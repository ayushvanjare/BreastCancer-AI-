"""Audit CBIS-DDSM pilot labels, split isolation, and downloaded DICOM metadata.

This script only reads CSV and DICOM headers. It does not read pixel data,
train a model, or treat the pilot as evidence of model performance.
Run it with the project's backend Python environment and pydicom installed.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _column(row: dict[str, str], *candidates: str) -> str:
    normalized = {key.strip().lower(): value for key, value in row.items() if key}
    for name in candidates:
        if name.lower() in normalized:
            return (normalized[name.lower()] or "").strip()
    return ""


def _path_series_uid(value: str) -> str:
    parts = PurePosixPath(value.replace("\\", "/")).parts
    # TCIA CSV paths end with .../<study UID>/<series UID>/<instance>.dcm.
    return parts[-2] if len(parts) >= 2 else ""


def audit(root: Path) -> dict[str, Any]:
    try:
        import pydicom
    except ImportError as exc:
        raise RuntimeError("pydicom is missing; run this using backend/.venv/Scripts/python.exe") from exc

    train_path = root / "labels" / "mass_case_description_train_set.csv"
    test_path = root / "labels" / "mass_case_description_test_set.csv"
    pilot_path = root / "pilot_cases.csv"
    for path in (train_path, test_path, pilot_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required CBIS-DDSM file was not found: {path}")

    train = _rows(train_path)
    test = _rows(test_path)
    pilot = _rows(pilot_path)
    required_pilot = {"PatientID", "Label", "CroppedImagePath", "RoiMaskPath"}
    missing = required_pilot - {key for key in (pilot[0].keys() if pilot else [])}
    if missing:
        raise ValueError(f"pilot_cases.csv is missing columns: {', '.join(sorted(missing))}")
    if not pilot:
        raise ValueError("pilot_cases.csv has no data rows")

    def patients(records: list[dict[str, str]], patient_columns: tuple[str, ...]) -> set[str]:
        return {_column(row, *patient_columns).upper() for row in records if _column(row, *patient_columns)}

    train_ids = patients(train, ("patient_id", "PatientID"))
    test_ids = patients(test, ("patient_id", "PatientID"))
    pilot_ids = patients(pilot, ("PatientID", "patient_id"))
    train_test_overlap = sorted(train_ids & test_ids)
    pilot_test_overlap = sorted(pilot_ids & test_ids)
    training_by_patient: dict[str, set[str]] = defaultdict(set)
    for row in train:
        patient = _column(row, "patient_id", "PatientID").upper()
        label = _column(row, "pathology", "label").upper()
        if patient and label:
            training_by_patient[patient].add(label)

    dicom_index: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    # Search the entire dataset root: the Data Retriever may place one series
    # under cbis_ddsm/ while other pilot series live under pilot_downloads/.
    dicom_files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".dcm")
    for path in dicom_files:
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True, force=False)
        except Exception:
            continue
        patient_id = str(getattr(ds, "PatientID", "")).strip()
        series_uid = str(getattr(ds, "SeriesInstanceUID", "")).strip()
        if patient_id and series_uid:
            dicom_index[(patient_id, series_uid)].append({
                "path": str(path),
                "description": str(getattr(ds, "SeriesDescription", "")).strip(),
                "patient_id": patient_id,
                "series_uid": series_uid,
            })

    cases = []
    label_counts: Counter[str] = Counter()
    for row in pilot:
        patient = _column(row, "PatientID", "patient_id").upper()
        label = _column(row, "Label", "pathology").upper()
        label_counts[label] += 1
        crop_path = _column(row, "CroppedImagePath", "cropped image file path")
        mask_path = _column(row, "RoiMaskPath", "ROI mask file path")
        expected_patient_id = "Mass-Training_" + _patient_suffix(crop_path)
        path_patient_matches_csv_patient = expected_patient_id.startswith(f"Mass-Training_{patient}_")
        expected = []
        for name, csv_path, description_fragment in (
            ("cropped_image", crop_path, "cropped"),
            ("roi_mask", mask_path, "roi mask"),
        ):
            series_uid = _path_series_uid(csv_path)
            matching = [item for item in dicom_index.get((expected_patient_id, series_uid), [])
                        if description_fragment in item["description"].lower()]
            expected.append({
                "type": name,
                "series_uid_from_label_csv": series_uid,
                "series_description_match_count": len(matching),
                "matched_dicom_paths": [item["path"] for item in matching],
            })
        label_match = label in training_by_patient.get(patient, set())
        cases.append({
            "patient_id": patient,
            "label": label,
            "training_label_match": label_match,
            "matches_training_label_unambiguously": training_by_patient.get(patient, set()) == {label},
            "path_patient_matches_csv_patient": path_patient_matches_csv_patient,
            "expected_dicom_patient_id": expected_patient_id,
            "series": expected,
        })

    all_metadata_matches = all(
        case["matches_training_label_unambiguously"]
        and case["path_patient_matches_csv_patient"]
        and all(series["series_description_match_count"] == 1 for series in case["series"])
        for case in cases
    ) and not train_test_overlap and not pilot_test_overlap
    verified_cases = [case["patient_id"] for case in cases if
                      case["matches_training_label_unambiguously"]
                      and case["path_patient_matches_csv_patient"]
                      and all(series["series_description_match_count"] == 1 for series in case["series"])]
    return {
        "dataset": "CBIS-DDSM mass pilot metadata audit",
        "root": str(root.resolve()),
        "training_rows": len(train),
        "training_unique_patients": len(train_ids),
        "official_test_rows": len(test),
        "official_test_unique_patients": len(test_ids),
        "pilot_cases": len(pilot),
        "pilot_unique_patients": len(pilot_ids),
        "pilot_verified_image_pairs": len(verified_cases),
        "pilot_verified_patient_ids": verified_cases,
        "pilot_missing_or_unverified_patient_ids": sorted(pilot_ids - set(verified_cases)),
        "pilot_label_counts": dict(sorted(label_counts.items())),
        "dicom_files_scanned_dataset_root": len(dicom_files),
        "readable_dicom_headers_indexed": sum(len(items) for items in dicom_index.values()),
        "training_official_test_patient_overlap_count": len(train_test_overlap),
        "training_official_test_patient_overlap_examples": train_test_overlap[:10],
        "pilot_official_test_patient_overlap_count": len(pilot_test_overlap),
        "pilot_official_test_patient_overlap_examples": pilot_test_overlap[:10],
        "all_pilot_labels_and_dicom_series_match": all_metadata_matches,
        "model_training_recommendation": "Do not train or report performance from this 20-case workflow pilot.",
        "cases": cases,
        "pixel_data_read": False,
        "clinical_inference_performed": False,
    }


def _patient_suffix(csv_path: str) -> str:
    """Return side/view/lesion suffix from a CSV path's first directory."""
    first = PurePosixPath(csv_path.replace("\\", "/")).parts[0]
    prefix = "Mass-Training_"
    return first[len(prefix):] if first.startswith(prefix) else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True,
                        help="CBIS-DDSM folder containing labels/ and pilot_downloads/.")
    parser.add_argument("--full-json", action="store_true",
                        help="Print every pilot case and matched DICOM path as JSON.")
    args = parser.parse_args()
    try:
        report = audit(args.root)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Audit could not be completed: {exc}", file=sys.stderr)
        return 2
    if args.full_json:
        print(json.dumps(report, indent=2))
    else:
        print("CBIS-DDSM pilot audit (headers only; no pixels read)")
        print(f"Training: {report['training_rows']} rows / {report['training_unique_patients']} patients")
        print(f"Official test: {report['official_test_rows']} rows / {report['official_test_unique_patients']} patients")
        print(f"Pilot labels: {report['pilot_cases']} unique patients / {report['pilot_label_counts']}")
        print(f"Train/test patient overlap: {report['training_official_test_patient_overlap_count']}")
        print(f"Pilot/test patient overlap: {report['pilot_official_test_patient_overlap_count']}")
        print(f"DICOM files found across dataset root: {report['dicom_files_scanned_dataset_root']}")
        print(f"Verified pilot image/mask pairs: {report['pilot_verified_image_pairs']}/{report['pilot_cases']}")
        print("Verified patients: " + (", ".join(report["pilot_verified_patient_ids"]) or "none"))
        print("Missing/unverified patients: " + (", ".join(report["pilot_missing_or_unverified_patient_ids"]) or "none"))
        if report["all_pilot_labels_and_dicom_series_match"]:
            print("Result: all pilot cases match labels and DICOM metadata.")
        else:
            print("Result: incomplete. Do not train or report performance from this pilot.")
    return 0 if report["all_pilot_labels_and_dicom_series_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
