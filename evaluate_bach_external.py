from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms


EXPECTED_CLASSES = ("Benign", "InSitu", "Invasive", "Normal")
IMAGE_EXTENSIONS = {".tif", ".tiff", ".jpg", ".jpeg", ".png"}
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
CLASS_TO_BINARY = {"Benign": 0, "Normal": 0, "InSitu": 1, "Invasive": 1}


class BachPhotos(Dataset):
    def __init__(self, photos_dir: Path, image_size: int):
        self.photos_dir = photos_dir
        self.transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ])
        self.samples: list[tuple[Path, str, int]] = []
        for class_name in EXPECTED_CLASSES:
            class_dir = photos_dir / class_name
            if not class_dir.is_dir():
                raise SystemExit(f"Missing expected BACH class folder: {class_dir}")
            files = sorted(
                path for path in class_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            )
            if not files:
                raise SystemExit(f"No supported image files found in {class_dir}")
            self.samples.extend((path, class_name, CLASS_TO_BINARY[class_name]) for path in files)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        path, class_name, binary_label = self.samples[index]
        try:
            with Image.open(path) as image:
                tensor = self.transform(image.convert("RGB"))
        except Exception as exc:
            raise RuntimeError(f"Could not read BACH image {path}: {exc}") from exc
        return tensor, binary_label, class_name, path.relative_to(self.photos_dir).as_posix()


def build_model(checkpoint_path: Path, device: torch.device):
    try:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    except TypeError:  # Compatibility with older PyTorch releases.
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
    if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
        raise ValueError(f"Unsupported checkpoint format: {checkpoint_path}")
    class_names = checkpoint.get("class_names")
    if class_names != ["benign", "malignant"]:
        raise ValueError(f"Unexpected checkpoint class order in {checkpoint_path}: {class_names}")
    if checkpoint.get("architecture") != "resnet18":
        raise ValueError(f"Expected a ResNet-18 checkpoint: {checkpoint_path}")
    image_size = int(checkpoint.get("image_size", 128))
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.to(device).eval()
    return model, image_size, checkpoint


def calculate_metrics(actual: list[int], predicted: list[int]) -> dict:
    tn = sum(a == 0 and p == 0 for a, p in zip(actual, predicted))
    fp = sum(a == 0 and p == 1 for a, p in zip(actual, predicted))
    fn = sum(a == 1 and p == 0 for a, p in zip(actual, predicted))
    tp = sum(a == 1 and p == 1 for a, p in zip(actual, predicted))
    total = tn + fp + fn + tp
    sensitivity = tp / (tp + fn) if tp + fn else None
    specificity = tn / (tn + fp) if tn + fp else None
    return {
        "confusion_matrix_actual_rows_predicted_columns": [[tn, fp], [fn, tp]],
        "accuracy": (tn + tp) / total if total else None,
        "carcinoma_sensitivity_recall": sensitivity,
        "non_carcinoma_specificity": specificity,
        "carcinoma_precision": tp / (tp + fp) if tp + fp else None,
        "balanced_accuracy": (sensitivity + specificity) / 2 if sensitivity is not None and specificity is not None else None,
    }


def evaluate_one(checkpoint_path: Path, dataset: BachPhotos, batch_size: int, device: torch.device):
    model, checkpoint_size, checkpoint = build_model(checkpoint_path, device)
    if checkpoint_size != dataset.transform.transforms[0].size[0]:
        raise ValueError(
            f"Evaluator size and checkpoint size differ for {checkpoint_path}: "
            f"{dataset.transform.transforms[0].size[0]} vs {checkpoint_size}"
        )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    actual: list[int] = []
    predicted: list[int] = []
    prediction_rows: list[dict] = []
    with torch.inference_mode():
        for images, labels, original_classes, relative_paths in loader:
            probabilities = torch.softmax(model(images.to(device)), dim=1)[:, 1].cpu().tolist()
            batch_predictions = [int(probability >= 0.5) for probability in probabilities]
            batch_actual = labels.tolist()
            actual.extend(batch_actual)
            predicted.extend(batch_predictions)
            for path, class_name, label, prediction, probability in zip(
                relative_paths, original_classes, batch_actual, batch_predictions, probabilities
            ):
                prediction_rows.append({
                    "checkpoint": str(checkpoint_path),
                    "training_fold": str(checkpoint.get("fold", "unknown")),
                    "training_magnification": str(checkpoint.get("magnification", "unknown")),
                    "relative_image_path": path,
                    "actual_bach_class": class_name,
                    "actual_binary_label": "carcinoma" if label else "non_carcinoma",
                    "predicted_binary_label": "carcinoma" if prediction else "non_carcinoma",
                    "probability_carcinoma": probability,
                })
    fold = str(checkpoint.get("fold", checkpoint_path.parent.name))
    magnification = str(checkpoint.get("magnification", "unknown"))
    return {
        "checkpoint": str(checkpoint_path),
        "fold": fold,
        "training_magnification": magnification,
        "image_size": checkpoint_size,
        "n_images": len(dataset),
        "original_class_counts": {
            name: sum(sample[1] == name for sample in dataset.samples)
            for name in EXPECTED_CLASSES
        },
        **calculate_metrics(actual, predicted),
    }, prediction_rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Research-only external evaluation of saved BreaKHis ResNet-18 checkpoints on BACH Photos."
    )
    parser.add_argument("--photos-dir", type=Path, required=True, help="BACH Photos folder containing Benign/InSitu/Invasive/Normal")
    parser.add_argument("--checkpoints-dir", type=Path, required=True, help="resnet18_results directory containing fold*_MAG folders")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("batch size must be positive")
    if not args.photos_dir.is_dir() or not args.checkpoints_dir.is_dir():
        raise SystemExit("Photos folder or checkpoints folder does not exist")

    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else "cpu")
    if args.device == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("CUDA was requested, but this Python environment cannot access CUDA")
        device = torch.device("cuda")
    elif args.device == "cpu":
        device = torch.device("cpu")
    dataset = BachPhotos(args.photos_dir, 128)
    class_counts = {name: sum(sample[1] == name for sample in dataset.samples) for name in EXPECTED_CLASSES}
    if len(dataset) != 400 or any(class_counts[name] != 100 for name in EXPECTED_CLASSES):
        raise SystemExit(f"Expected 100 images in each of the four BACH Photos classes; found {class_counts}")

    checkpoints = sorted(args.checkpoints_dir.glob("fold*_*x/resnet18_fold*_*x.pt"))
    if len(checkpoints) != 20:
        raise SystemExit(f"Expected 20 fold/magnification checkpoints; found {len(checkpoints)} under {args.checkpoints_dir}")

    print("RESEARCH-ONLY external evaluation — not a diagnostic tool or clinical validation.")
    print(f"BACH images: {len(dataset)}; class counts: {class_counts}")
    print("Binary mapping: Benign + Normal -> non-carcinoma; InSitu + Invasive -> carcinoma.")
    print(f"Device: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else ""))
    print("Images are decoded and resized in memory; source image files are not written or changed.")

    results: list[dict] = []
    all_rows: list[dict] = []
    for checkpoint_path in checkpoints:
        result, rows = evaluate_one(checkpoint_path, dataset, args.batch_size, device)
        results.append(result)
        all_rows.extend(rows)
        print(
            f"{result['fold']} {result['training_magnification']}: "
            f"accuracy={result['accuracy']:.4f}, "
            f"carcinoma_recall={result['carcinoma_sensitivity_recall']:.4f}, "
            f"non_carcinoma_specificity={result['non_carcinoma_specificity']:.4f}"
        )

    metric_names = (
        "accuracy", "carcinoma_sensitivity_recall", "non_carcinoma_specificity",
        "carcinoma_precision", "balanced_accuracy",
    )
    by_magnification: dict[str, dict] = {}
    for magnification in ("40X", "100X", "200X", "400X"):
        group = [row for row in results if row["training_magnification"].upper() == magnification]
        if len(group) != 5:
            raise SystemExit(f"Expected five checkpoints for {magnification}; found {len(group)}")
        by_magnification[magnification] = {
            "fold_model_count": len(group),
            "metrics_mean_across_fold_models": {
                name: statistics.mean(row[name] for row in group) for name in metric_names
            },
            "metrics_std_across_fold_models_population": {
                name: statistics.pstdev(row[name] for row in group) for name in metric_names
            },
            "note": "Fold-model spread is descriptive variability across saved models, not a patient-level confidence interval.",
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": "research-only external dataset evaluation; not for diagnosis, clinical use, or clinical validation",
        "dataset": "BACH / ICIAR 2018 Photos subset",
        "n_images": len(dataset),
        "original_class_counts": class_counts,
        "binary_mapping": {
            "non_carcinoma_label_0": ["Benign", "Normal"],
            "carcinoma_label_1": ["InSitu", "Invasive"],
            "note": "This is a study-specific grouping; original four-class labels are retained in predictions.csv.",
        },
        "model": "Saved BreaKHis ResNet-18 checkpoints, evaluated without retraining",
        "preprocessing": "Resize to checkpoint image size; RGB; ImageNet normalization; source files left unchanged",
        "device": str(device),
        "cuda_device": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "checkpoint_results": results,
        "magnification_summary": by_magnification,
    }
    with (args.output_dir / "bach_external_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    fieldnames = list(all_rows[0].keys())
    with (args.output_dir / "bach_external_predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    with (args.output_dir / "bach_external_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["training_magnification", "fold", "n_images", *metric_names]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            writer.writerow({name: result.get(name) for name in fields})
        for magnification, summary in by_magnification.items():
            writer.writerow({
                "training_magnification": magnification,
                "fold": "mean_across_fold_models",
                "n_images": len(dataset),
                **summary["metrics_mean_across_fold_models"],
            })
            writer.writerow({
                "training_magnification": magnification,
                "fold": "std_across_fold_models_population",
                "n_images": len(dataset),
                **summary["metrics_std_across_fold_models_population"],
            })
    print(f"\nSaved report and per-image predictions to: {args.output_dir.resolve()}")
    print("These measurements are descriptive external research results, not clinical performance estimates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
