from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset


class BreakHis40X(Dataset):
    """Binary research dataset: BreaKHis benign (0) vs malignant (1)."""

    def __init__(self, folder: Path, image_size: int):
        self.folder = folder
        self.image_size = image_size
        self.files = sorted(folder.glob("*.png"))
        if not self.files:
            raise ValueError(f"No PNG images found in {folder}")
        invalid = [p.name for p in self.files if not (p.name.startswith("SOB_B_") or p.name.startswith("SOB_M_"))]
        if invalid:
            raise ValueError(f"Unexpected image filename (expected SOB_B_ or SOB_M_): {invalid[0]}")
        self.labels = [1 if p.name.startswith("SOB_M_") else 0 for p in self.files]

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, index: int):
        path = self.files[index]
        with Image.open(path) as image:
            image = image.convert("RGB").resize((self.image_size, self.image_size), Image.Resampling.BILINEAR)
            tensor = torch.frombuffer(bytearray(image.tobytes()), dtype=torch.uint8)
            tensor = tensor.view(self.image_size, self.image_size, 3).permute(2, 0, 1).float().div_(255.0)
        # Scale RGB values to [0, 1]; no stain normalization or clinical interpretation is performed.
        return tensor, self.labels[index], path.name


def group_key(filename: str) -> str:
    parts = Path(filename).stem.split("-")
    if len(parts) < 5:
        raise ValueError(f"Unexpected BreaKHis filename: {filename}")
    return "-".join(parts[:-2])


class SmallCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            nn.Conv2d(64, 96, 3, padding=1), nn.BatchNorm2d(96), nn.ReLU(inplace=True), nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(96, 2))

    def forward(self, x):
        return self.classifier(self.features(x))


def main() -> int:
    parser = argparse.ArgumentParser(description="Research-only BreaKHis 40X benign/malignant baseline; not for diagnosis.")
    parser.add_argument("--fold-dir", type=Path, required=True, help="Fold directory containing train/40X and test/40X")
    parser.add_argument("--output-dir", type=Path, required=True, help="Where to save model checkpoint and metrics")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.image_size < 32:
        raise SystemExit("epochs and batch size must be positive; image size must be at least 32")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    train_ds = BreakHis40X(args.fold_dir / "train" / "40X", args.image_size)
    test_ds = BreakHis40X(args.fold_dir / "test" / "40X", args.image_size)
    train_groups = {group_key(p.name) for p in train_ds.files}
    test_groups = {group_key(p.name) for p in test_ds.files}
    overlap = train_groups & test_groups
    if overlap:
        raise SystemExit(f"Train/test leakage check failed: {len(overlap)} shared sample group(s), e.g. {sorted(overlap)[0]}")

    train_counts = [train_ds.labels.count(0), train_ds.labels.count(1)]
    test_counts = [test_ds.labels.count(0), test_ds.labels.count(1)]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("RESEARCH BASELINE ONLY — not a diagnostic tool or clinical validation.")
    print(f"Device: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else ""))
    print(f"40X images: train={len(train_ds)} (benign={train_counts[0]}, malignant={train_counts[1]}), "
          f"test={len(test_ds)} (benign={test_counts[0]}, malignant={test_counts[1]})")
    print(f"Shared train/test sample groups: {len(overlap)}")

    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0, generator=generator)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    model = SmallCNN().to(device)
    weights = torch.tensor([len(train_ds) / (2 * max(n, 1)) for n in train_counts], dtype=torch.float32, device=device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        correct = total = 0
        for images, labels, _names in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * labels.size(0)
            correct += (logits.argmax(1) == labels).sum().item()
            total += labels.size(0)
        print(f"Epoch {epoch}/{args.epochs}: loss={running_loss / max(total, 1):.4f}, train_accuracy={correct / max(total, 1):.4f}")

    model.eval()
    tn = fp = fn = tp = 0
    with torch.inference_mode():
        for images, labels, _names in test_loader:
            labels = labels.to(device)
            predictions = model(images.to(device)).argmax(1)
            for actual, predicted in zip(labels.tolist(), predictions.tolist()):
                if actual == 0 and predicted == 0:
                    tn += 1
                elif actual == 0 and predicted == 1:
                    fp += 1
                elif actual == 1 and predicted == 0:
                    fn += 1
                else:
                    tp += 1

    total = tn + fp + fn + tp
    metrics = {
        "scope": "research-only BreaKHis binary baseline; not for diagnosis or clinical use",
        "fold": args.fold_dir.name,
        "magnification": "40X",
        "image_size": args.image_size,
        "epochs": args.epochs,
        "device": str(device),
        "cuda_device": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "train_images": len(train_ds),
        "test_images": len(test_ds),
        "train_test_shared_sample_groups": 0,
        "confusion_matrix_actual_rows_predicted_columns": [[tn, fp], [fn, tp]],
        "accuracy": (tn + tp) / total if total else None,
        "malignant_sensitivity_recall": tp / (tp + fn) if tp + fn else None,
        "benign_specificity": tn / (tn + fp) if tn + fp else None,
        "malignant_precision": tp / (tp + fp) if tp + fp else None,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_name = f"breakhis_{args.fold_dir.name.lower()}_40x_baseline.pt"
    torch.save({"model_state_dict": model.cpu().state_dict(), "class_names": ["benign", "malignant"],
                "image_size": args.image_size, "fold": args.fold_dir.name, "magnification": "40X"},
               args.output_dir / checkpoint_name)
    with (args.output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    print("\nTest metrics (descriptive research results only):")
    print(json.dumps(metrics, indent=2))
    print(f"\nSaved files in: {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
