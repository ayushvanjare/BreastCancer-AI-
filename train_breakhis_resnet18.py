from __future__ import annotations

import argparse
import copy
import json
import random
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def label_for(path: Path) -> int:
    if path.name.startswith("SOB_B_"):
        return 0
    if path.name.startswith("SOB_M_"):
        return 1
    raise ValueError(f"Unexpected BreaKHis filename: {path.name}")


def sample_group(filename: str) -> str:
    parts = Path(filename).stem.split("-")
    if len(parts) < 5:
        raise ValueError(f"Unexpected BreaKHis filename: {filename}")
    return "-".join(parts[:-2])


class ImageList(Dataset):
    def __init__(self, files: list[Path], transform):
        self.files = files
        self.transform = transform
        self.labels = [label_for(p) for p in files]

    def __len__(self):
        return len(self.files)

    def __getitem__(self, index):
        path = self.files[index]
        with Image.open(path) as image:
            image = image.convert("RGB")
            tensor = self.transform(image)
        return tensor, self.labels[index]


def split_validation_by_group(files: list[Path], seed: int, fraction: float):
    # Stratify by class, but keep every image from a sample group in one partition.
    by_class: dict[int, dict[str, list[Path]]] = {0: {}, 1: {}}
    for path in files:
        label = label_for(path)
        by_class[label].setdefault(sample_group(path.name), []).append(path)
    train_files: list[Path] = []
    val_files: list[Path] = []
    rng = random.Random(seed)
    for label in (0, 1):
        groups = list(by_class[label].items())
        rng.shuffle(groups)
        if len(groups) < 2:
            raise SystemExit(f"Need at least two distinct sample groups for class {label} to create validation split.")
        n_val = max(1, min(len(groups) - 1, round(len(groups) * fraction)))
        for index, (_group, paths) in enumerate(groups):
            (val_files if index < n_val else train_files).extend(paths)
    train_groups = {sample_group(p.name) for p in train_files}
    val_groups = {sample_group(p.name) for p in val_files}
    overlap = train_groups & val_groups
    if overlap:
        raise SystemExit(f"Validation leakage check failed: {len(overlap)} shared sample group(s).")
    return sorted(train_files), sorted(val_files)


def counts(labels: list[int]) -> list[int]:
    return [labels.count(0), labels.count(1)]


def evaluate(model, loader, device):
    model.eval()
    tn = fp = fn = tp = 0
    with torch.inference_mode():
        for images, labels in loader:
            logits = model(images.to(device))
            predictions = logits.argmax(1).cpu().tolist()
            for actual, predicted in zip(labels.tolist(), predictions):
                if actual == 0 and predicted == 0:
                    tn += 1
                elif actual == 0 and predicted == 1:
                    fp += 1
                elif actual == 1 and predicted == 0:
                    fn += 1
                else:
                    tp += 1
    total = tn + fp + fn + tp
    return {
        "confusion_matrix_actual_rows_predicted_columns": [[tn, fp], [fn, tp]],
        "accuracy": (tn + tp) / total if total else None,
        "malignant_sensitivity_recall": tp / (tp + fn) if tp + fn else None,
        "benign_specificity": tn / (tn + fp) if tn + fp else None,
        "malignant_precision": tp / (tp + fp) if tp + fp else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Research-only BreaKHis ResNet-18 transfer-learning experiment; not for diagnosis.")
    parser.add_argument("--fold-dir", type=Path, required=True, help="Fold directory containing train/ and test/ magnification folders")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--magnification", choices=("40X", "100X", "200X", "400X"), default="40X")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.image_size < 64:
        raise SystemExit("epochs and batch size must be positive; image size must be at least 64")
    if not 0.05 <= args.validation_fraction <= 0.4:
        raise SystemExit("validation fraction must be between 0.05 and 0.4")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    train_dir = args.fold_dir / "train" / args.magnification
    test_dir = args.fold_dir / "test" / args.magnification
    train_files = sorted(train_dir.glob("*.png"))
    test_files = sorted(test_dir.glob("*.png"))
    if not train_files or not test_files:
        raise SystemExit(f"Missing PNG images in {train_dir} or {test_dir}")

    all_train_groups = {sample_group(p.name) for p in train_files}
    test_groups = {sample_group(p.name) for p in test_files}
    test_overlap = all_train_groups & test_groups
    if test_overlap:
        raise SystemExit(f"Official train/test leakage check failed: {len(test_overlap)} shared sample group(s).")
    fit_files, val_files = split_validation_by_group(train_files, args.seed, args.validation_fraction)
    fit_groups = {sample_group(p.name) for p in fit_files}
    val_groups = {sample_group(p.name) for p in val_files}
    if (fit_groups & val_groups) or (fit_groups & test_groups) or (val_groups & test_groups):
        raise SystemExit("A sample group is shared between fit, validation, or test partitions.")

    size = args.image_size
    fit_transform = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(15),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    eval_transform = transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    fit_ds = ImageList(fit_files, fit_transform)
    val_ds = ImageList(val_files, eval_transform)
    test_ds = ImageList(test_files, eval_transform)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("RESEARCH EXPERIMENT ONLY — not a diagnostic tool or clinical validation.")
    print(f"Device: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else ""))
    print(f"{args.magnification} images: fit={len(fit_ds)} {counts(fit_ds.labels)}, validation={len(val_ds)} {counts(val_ds.labels)}, test={len(test_ds)} {counts(test_ds.labels)}")
    print(f"Sample groups: fit={len(fit_groups)}, validation={len(val_groups)}, test={len(test_groups)}; overlaps=0")

    generator = torch.Generator().manual_seed(args.seed)
    fit_loader = DataLoader(fit_ds, batch_size=args.batch_size, shuffle=True, num_workers=0, generator=generator)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    # The first run may download standard ImageNet weights from torchvision if not cached.
    weights = models.ResNet18_Weights.DEFAULT
    model = models.resnet18(weights=weights)
    for parameter in model.parameters():
        parameter.requires_grad = False
    for parameter in model.layer4.parameters():
        parameter.requires_grad = True
    model.fc = nn.Linear(model.fc.in_features, 2)
    for parameter in model.fc.parameters():
        parameter.requires_grad = True
    model = model.to(device)

    fit_counts = counts(fit_ds.labels)
    class_weights = torch.tensor([len(fit_ds) / (2 * max(n, 1)) for n in fit_counts], dtype=torch.float32, device=device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=1e-4, weight_decay=1e-4)
    best_state = None
    best_val_loss = float("inf")
    patience, stale = 2, 0

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        total = correct = 0
        for images, labels in fit_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * labels.size(0)
            correct += (logits.argmax(1) == labels).sum().item()
            total += labels.size(0)

        model.eval()
        val_loss = 0.0
        val_total = 0
        with torch.inference_mode():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                loss = criterion(model(images), labels)
                val_loss += loss.item() * labels.size(0)
                val_total += labels.size(0)
        mean_val_loss = val_loss / max(val_total, 1)
        print(f"Epoch {epoch}/{args.epochs}: fit_loss={total_loss / max(total, 1):.4f}, "
              f"fit_accuracy={correct / max(total, 1):.4f}, validation_loss={mean_val_loss:.4f}")
        if mean_val_loss < best_val_loss:
            best_val_loss = mean_val_loss
            best_state = copy.deepcopy({key: value.detach().cpu() for key, value in model.state_dict().items()})
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                print("Early stopping based on validation loss.")
                break

    if best_state is None:
        raise SystemExit("Training did not produce a valid checkpoint.")
    model.load_state_dict(best_state)
    model.to(device)
    # Evaluate the official test partition once, after model selection using validation only.
    test_metrics = evaluate(model, test_loader, device)
    fold_name = args.fold_dir.name.lower()
    metrics = {
        "scope": "research-only BreaKHis binary transfer-learning experiment; not for diagnosis or clinical use",
        "model": "ResNet-18 ImageNet pretrained; layer4 and classifier fine-tuned",
        "fold": args.fold_dir.name,
        "magnification": args.magnification,
        "image_size": args.image_size,
        "epochs_requested": args.epochs,
        "best_validation_loss": best_val_loss,
        "device": str(device),
        "cuda_device": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "fit_images": len(fit_ds),
        "validation_images": len(val_ds),
        "test_images": len(test_ds),
        "fit_validation_test_shared_sample_groups": 0,
        **test_metrics,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": model.cpu().state_dict(), "class_names": ["benign", "malignant"],
                "image_size": args.image_size, "fold": args.fold_dir.name, "magnification": args.magnification,
                "architecture": "resnet18", "pretrained": "ImageNet"},
               args.output_dir / f"resnet18_{fold_name}_{args.magnification.lower()}.pt")
    with (args.output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    print("\nTest metrics (research-only; not clinical performance):")
    print(json.dumps(metrics, indent=2))
    print(f"\nSaved files in: {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
