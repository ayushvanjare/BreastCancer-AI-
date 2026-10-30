from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]
DATA_PATH = SCRIPT_DIR / "derived" / "clinvar_brca1_brca2_breast_ovarian_variant_labels.tsv"
MODEL_DIR = PROJECT_ROOT / "model_artifacts" / "brca_variant_annotation"
RESULT_DIR = PROJECT_ROOT / "research_results" / "brca_variant_annotation"
FEATURE_COLUMNS = ["gene", "variant", "molecular_consequences", "protein_change"]
LABELS = {"Pathogenic": 1, "Likely pathogenic": 1, "Benign": 0, "Likely benign": 0}


def dataset_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_group(row: pd.Series) -> str:
    # Keep all records from the same gene/locus together to reduce locus leakage.
    chromosome = str(row.get("GRCh38_chromosome", "")).strip()
    start = str(row.get("GRCh38_start", "")).strip()
    stop = str(row.get("GRCh38_stop", "")).strip()
    gene = str(row["gene"]).strip()
    if chromosome and start and stop:
        return f"{gene}|{chromosome}|{start}|{stop}"
    return f"{gene}|unmapped|{str(row['variant']).strip().lower()}"


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(DATA_PATH, sep="\t", dtype=str).fillna("")
    frame = frame.drop_duplicates(subset=["clinvar_accession"]).copy()
    frame["target_pathogenic"] = frame["germline_classification"].map(LABELS)
    frame = frame.dropna(subset=["target_pathogenic"]).copy()
    frame["target_pathogenic"] = frame["target_pathogenic"].astype(int)
    frame["split_group"] = frame.apply(make_group, axis=1)

    # Drop genomic loci that contain both binary labels in this filtered source;
    # they are ambiguous for a one-label-per-locus holdout experiment.
    label_counts_per_group = frame.groupby("split_group")["target_pathogenic"].nunique()
    conflicting_groups = set(label_counts_per_group[label_counts_per_group > 1].index)
    excluded_conflict_rows = int(frame["split_group"].isin(conflicting_groups).sum())
    frame = frame.loc[~frame["split_group"].isin(conflicting_groups)].reset_index(drop=True)
    if frame["target_pathogenic"].nunique() != 2:
        raise RuntimeError("Both benign/likely benign and pathogenic/likely pathogenic classes are required.")

    X = frame[FEATURE_COLUMNS].astype(str)
    y = frame["target_pathogenic"].to_numpy()
    groups = frame["split_group"].to_numpy()
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=20261029)
    train_indices, test_indices = next(splitter.split(X, y, groups))
    train_groups = set(groups[train_indices])
    test_groups = set(groups[test_indices])
    overlap_count = len(train_groups & test_groups)
    if overlap_count:
        raise RuntimeError("Group leakage detected between train and holdout partitions.")
    if len(np.unique(y[test_indices])) != 2:
        raise RuntimeError("Holdout partition does not contain both classes; no model was saved.")

    features = ColumnTransformer(
        transformers=[
            ("gene", OneHotEncoder(handle_unknown="ignore"), ["gene"]),
            ("hgvs_text", TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=2, max_features=50000), "variant"),
            ("consequence", TfidfVectorizer(token_pattern=r"(?u)\b\w+\b", ngram_range=(1, 2), min_df=1), "molecular_consequences"),
            ("protein_text", TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2, max_features=25000), "protein_change"),
        ],
        remainder="drop",
        sparse_threshold=1.0,
    )
    model = Pipeline(
        steps=[
            ("features", features),
            ("classifier", LogisticRegression(class_weight="balanced", C=1.0, max_iter=3000, solver="liblinear", random_state=20261029)),
        ]
    )
    model.fit(X.iloc[train_indices], y[train_indices])
    probabilities = model.predict_proba(X.iloc[test_indices])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    matrix = confusion_matrix(y[test_indices], predictions, labels=[0, 1])
    metrics = {
        "scope": "variant-level ClinVar annotation classification research pilot; not a patient-level carrier-risk model",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "target": "ClinVar germline classification collapsed as Pathogenic/Likely pathogenic vs Benign/Likely benign",
        "source": "NCBI ClinVar filtered BRCA1/BRCA2 breast/ovarian variant table",
        "data_file": str(DATA_PATH.relative_to(PROJECT_ROOT)),
        "data_sha256": dataset_sha256(DATA_PATH),
        "model": "scikit-learn logistic regression with character n-gram variant/protein text, consequence text, and gene features",
        "split": "single 80/20 GroupShuffleSplit; gene and GRCh38 locus are held together; fixed seed 20261029",
        "features": FEATURE_COLUMNS,
        "excluded_ambiguous_locus_rows": excluded_conflict_rows,
        "rows_after_filtering": len(frame),
        "train_rows": len(train_indices),
        "holdout_rows": len(test_indices),
        "train_groups": len(train_groups),
        "holdout_groups": len(test_groups),
        "train_holdout_group_overlap": overlap_count,
        "train_class_counts_benign_then_pathogenic": [int((y[train_indices] == 0).sum()), int((y[train_indices] == 1).sum())],
        "holdout_class_counts_benign_then_pathogenic": [int((y[test_indices] == 0).sum()), int((y[test_indices] == 1).sum())],
        "decision_threshold": 0.5,
        "metrics": {
            "accuracy": float(accuracy_score(y[test_indices], predictions)),
            "balanced_accuracy": float(balanced_accuracy_score(y[test_indices], predictions)),
            "pathogenic_precision": float(precision_score(y[test_indices], predictions, zero_division=0)),
            "pathogenic_recall": float(recall_score(y[test_indices], predictions, zero_division=0)),
            "roc_auc": float(roc_auc_score(y[test_indices], probabilities)),
            "average_precision": float(average_precision_score(y[test_indices], probabilities)),
            "confusion_matrix_actual_rows_benign_pathogenic_predicted_columns_benign_pathogenic": matrix.tolist(),
            "classification_report": classification_report(y[test_indices], predictions, target_names=["benign_or_likely_benign", "pathogenic_or_likely_pathogenic"], output_dict=True, zero_division=0),
        },
        "limitations": [
            "Labels and annotations come from the same public database; the holdout is not an independent clinical validation cohort.",
            "Variant classification is not patient-level germline carrier detection or cancer-risk prediction.",
            "Class balance and ClinVar curation patterns affect these internal metrics.",
            "No probability calibration or clinical threshold selection was performed.",
            "Research use only; do not use for screening, diagnosis, treatment, or patient care.",
        ],
    }
    model_path = MODEL_DIR / "clinvar_brca_variant_classifier.joblib"
    joblib.dump(model, model_path, compress=3)
    metrics_path = RESULT_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    report_path = RESULT_DIR / "MODEL_CARD.md"
    m = metrics["metrics"]
    report_path.write_text(
        "# ClinVar BRCA variant annotation classifier\n\n"
        "**Research-only.** This model classifies public BRCA1/BRCA2 variant annotations as pathogenic/likely pathogenic or benign/likely benign. It does not predict whether a person carries an inherited variant, develop cancer, or need care.\n\n"
        f"- Model: logistic regression, grouped holdout split (seed 20261029).\n"
        f"- Records after ambiguous-locus exclusion: {len(frame)}; training: {len(train_indices)}; holdout: {len(test_indices)}.\n"
        f"- Holdout accuracy: {m['accuracy']:.3f}; balanced accuracy: {m['balanced_accuracy']:.3f}; ROC AUC: {m['roc_auc']:.3f}; average precision: {m['average_precision']:.3f}.\n"
        f"- Pathogenic-class precision: {m['pathogenic_precision']:.3f}; recall: {m['pathogenic_recall']:.3f}.\n"
        f"- Locus groups shared across train and holdout: {overlap_count}.\n\n"
        "## Important limitations\n\n"
        "The source is ClinVar itself, so this internal holdout is not independent clinical validation. Curated variant labels are not individual patient outcomes. Metrics can reflect ClinVar curation patterns and class balance. The model is not connected to the patient-facing application. Do not use its output for screening, diagnosis, treatment, or patient-care decisions.\n",
        encoding="utf-8",
    )
    print(json.dumps({"model": str(model_path), "metrics": str(metrics_path), "model_card": str(report_path), "rows": len(frame), "train": len(train_indices), "holdout": len(test_indices), "group_overlap": overlap_count, "metrics_summary": {key: m[key] for key in ("accuracy", "balanced_accuracy", "roc_auc", "average_precision", "pathogenic_precision", "pathogenic_recall")}}, indent=2))


if __name__ == "__main__":
    main()
