"""In-memory, non-predictive BRCA cohort-file checks."""

from __future__ import annotations

import csv
import io
from collections import Counter

_LABELS = {
    "positive": "positive", "pathogenic": "positive", "likely_pathogenic": "positive", "1": "positive",
    "negative": "negative", "benign": "negative", "likely_benign": "negative", "0": "negative",
}


def preflight_brca_csv(content: bytes) -> dict:
    """Validate schema and report aggregate counts without retaining identifiers or rows."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Save the de-identified cohort CSV as UTF-8 and try again.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("The CSV must have a header row.")
    headers = {header.strip().lower() for header in reader.fieldnames if header}
    required = {"sample_id", "target_type", "label"}
    missing = sorted(required - headers)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing) + ".")

    source = {header.strip().lower(): header for header in reader.fieldnames if header}
    rows = missing_values = duplicate_ids = invalid_targets = invalid_labels = 0
    missing_targets = missing_labels = 0
    target_types: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    seen_ids: set[str] = set()
    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        rows += 1
        sample_id = (row.get(source["sample_id"]) or "").strip()
        target = (row.get(source["target_type"]) or "").strip().lower()
        label = (row.get(source["label"]) or "").strip().lower().replace(" ", "_")
        if not sample_id or not target or not label:
            missing_values += 1
        if not target:
            missing_targets += 1
        if not label:
            missing_labels += 1
        if sample_id:
            if sample_id in seen_ids:
                duplicate_ids += 1
            seen_ids.add(sample_id)
        if target in {"germline", "somatic"}:
            target_types[target] += 1
        elif target:
            invalid_targets += 1
        normalized = _LABELS.get(label)
        if normalized:
            labels[normalized] += 1
        elif label:
            invalid_labels += 1
    if rows == 0:
        raise ValueError("The cohort CSV has no data rows.")

    return {
        "inspection_type": "brca_cohort_schema_preflight",
        "prediction_performed": False,
        "raw_data_saved": False,
        "row_count": rows,
        "target_type_counts": dict(target_types),
        "target_type_consistent": len(target_types) == 1 and invalid_targets == 0 and missing_targets == 0,
        "label_counts": dict(labels),
        "binary_labels_recognized": len(labels) == 2 and invalid_labels == 0 and missing_labels == 0,
        "rows_with_missing_required_values": missing_values,
        "duplicate_sample_ids": duplicate_ids,
        "invalid_target_rows": invalid_targets,
        "unrecognized_label_rows": invalid_labels,
        "ready_for_model_training": False,
        "note": "Schema and aggregate counts only. No genotype interpretation or mutation prediction was performed; independent review and an approved study protocol remain required.",
    }
