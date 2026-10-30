from __future__ import annotations

import gzip
from io import BytesIO

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_PIXELS = 100_000_000
EXPECTED_MODALITIES = {
    "ct": {"CT"},
    "mri": {"MR"},
    "xray": {"CR", "DX", "MG"},
}
RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
DICOM_EXTENSIONS = {".dcm", ".dicom"}
NIFTI_EXTENSIONS = {".nii", ".nii.gz"}


class ImagingReviewError(ValueError):
    pass


class ImagingReviewUnavailableError(RuntimeError):
    pass


def inspect_imaging_input(module_id: str, filename: str, content: bytes) -> dict:
    """Inspect one image/header without saving it or returning patient identifiers."""
    if module_id not in EXPECTED_MODALITIES:
        raise ImagingReviewError("Choose CT, MRI, or X-ray & Mammography for input review.")
    if not content:
        raise ImagingReviewError("The selected file is empty.")
    lower_name = filename.lower()
    extension = ".nii.gz" if lower_name.endswith(".nii.gz") else ("." + filename.rsplit(".", 1)[-1].lower() if "." in filename else "")
    if extension in RASTER_EXTENSIONS:
        try:
            with Image.open(BytesIO(content)) as image:
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ImagingReviewError("The image dimensions exceed the supported limit.")
                image_format = image.format
                width, height, mode = image.width, image.height, image.mode
                image.verify()
                return {
                    "inspection_type": "raster_image_metadata",
                    "module_id": module_id,
                    "modality_check": "not_verifiable_from_raster_image",
                    "metadata": {
                        "format": image_format,
                        "width": int(width),
                        "height": int(height),
                        "mode": mode,
                    },
                    "patient_identifiers_returned": False,
                    "model_inference_performed": False,
                }
        except ImagingReviewError:
            raise
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
            raise ImagingReviewError("The selected file is not a readable PNG, JPG, or TIFF image.") from exc
    if extension in NIFTI_EXTENSIONS:
        try:
            import nibabel as nib
        except ImportError as exc:
            raise ImagingReviewUnavailableError("NIfTI header reading is unavailable. Install the project's backend requirements.") from exc
        try:
            nifti_bytes = content
            if extension == ".nii.gz":
                with gzip.GzipFile(fileobj=BytesIO(content)) as compressed:
                    nifti_bytes = compressed.read(512 * 1024 * 1024 + 1)
                if len(nifti_bytes) > 512 * 1024 * 1024:
                    raise ImagingReviewError("The expanded NIfTI image exceeds the 512 MB safety limit.")
            image = nib.Nifti1Image.from_bytes(nifti_bytes)
            header = image.header
            shape = [int(value) for value in image.shape]
            if not shape or any(value <= 0 for value in shape) or len(shape) > 7:
                raise ImagingReviewError("The NIfTI header has invalid dimensions.")
            zooms = [float(value) for value in header.get_zooms()]
            if any(not __import__("math").isfinite(value) or value <= 0 for value in zooms):
                raise ImagingReviewError("The NIfTI header has invalid voxel spacing.")
            return {
                "inspection_type": "nifti_header_metadata",
                "module_id": module_id,
                "modality_check": "not_verifiable_from_nifti_header",
                "metadata": {"format": "NIfTI", "dimensions": shape, "voxel_spacing": zooms,
                             "data_type": str(header.get_data_dtype())},
                "patient_identifiers_returned": False,
                "model_inference_performed": False,
                "note": "Header metadata only. Voxel data and identifying extensions are not returned.",
            }
        except ImagingReviewError:
            raise
        except Exception as exc:
            raise ImagingReviewError("The selected file is not a readable NIfTI-1 image.") from exc
    if extension not in DICOM_EXTENSIONS:
        raise ImagingReviewError("Upload one DICOM (.dcm/.dicom), NIfTI (.nii/.nii.gz), PNG, JPG, JPEG, or TIFF image.")
    try:
        import pydicom

        dataset = pydicom.dcmread(BytesIO(content), stop_before_pixels=True, force=False)
    except ImportError as exc:
        raise ImagingReviewUnavailableError("DICOM header reading is unavailable. Install the project's backend requirements.") from exc
    except Exception as exc:
        raise ImagingReviewError("The DICOM file could not be read. Check that it is a valid single-instance DICOM file.") from exc

    modality = str(getattr(dataset, "Modality", "")).upper()
    if modality not in EXPECTED_MODALITIES[module_id]:
        expected = ", ".join(sorted(EXPECTED_MODALITIES[module_id]))
        found = modality or "unspecified"
        raise ImagingReviewError(f"This module expects DICOM modality {expected}; the uploaded file reports {found}.")

    def safe_int(name: str):
        value = getattr(dataset, name, None)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def safe_numbers(name: str):
        value = getattr(dataset, name, None)
        if value is None:
            return None
        try:
            if isinstance(value, (str, bytes)):
                return [float(value)]
            try:
                return [float(item) for item in value]
            except TypeError:
                return [float(value)]
        except (TypeError, ValueError):
            return None

    metadata = {
        "modality": modality,
        "rows": safe_int("Rows"),
        "columns": safe_int("Columns"),
        "frames": safe_int("NumberOfFrames") or 1,
        "samples_per_pixel": safe_int("SamplesPerPixel"),
        "pixel_spacing_mm": safe_numbers("PixelSpacing"),
        "slice_thickness_mm": safe_numbers("SliceThickness"),
    }
    return {
        "inspection_type": "dicom_header_metadata",
        "module_id": module_id,
        "modality_check": "matches_selected_module",
        "metadata": metadata,
        "patient_identifiers_returned": False,
        "model_inference_performed": False,
        "note": "Single-instance header inspection only. Pixel data and patient-identifying DICOM fields are not returned.",
    }


def inspect_dicom_series(module_id: str, files: list[tuple[str, bytes]]) -> dict:
    """Check a same-series DICOM set using header metadata only."""
    if module_id not in EXPECTED_MODALITIES:
        raise ImagingReviewError("Choose CT, MRI, or X-ray & Mammography for input review.")
    if not files:
        raise ImagingReviewError("Select at least one DICOM instance.")
    try:
        import pydicom
    except ImportError as exc:
        raise ImagingReviewUnavailableError("DICOM header reading is unavailable. Install the project's backend requirements.") from exc

    datasets = []
    series_ids = set()
    study_ids = set()
    modalities = set()
    positions = []
    orientations = set()
    shapes = set()
    for name, content in files:
        extension = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if extension not in DICOM_EXTENSIONS or not content:
            raise ImagingReviewError("A DICOM series may contain only non-empty .dcm or .dicom files.")
        try:
            dataset = pydicom.dcmread(BytesIO(content), stop_before_pixels=True, force=False)
        except Exception as exc:
            raise ImagingReviewError("One of the selected files is not a readable DICOM instance.") from exc
        modality = str(getattr(dataset, "Modality", "")).upper()
        if modality not in EXPECTED_MODALITIES[module_id]:
            expected = ", ".join(sorted(EXPECTED_MODALITIES[module_id]))
            raise ImagingReviewError(f"This module expects DICOM modality {expected}; a selected instance reports {modality or 'unspecified'}.")
        series_id = str(getattr(dataset, "SeriesInstanceUID", ""))
        study_id = str(getattr(dataset, "StudyInstanceUID", ""))
        if not series_id:
            raise ImagingReviewError("Every DICOM instance must include a Series Instance UID.")
        if not study_id:
            raise ImagingReviewError("Every DICOM instance must include a Study Instance UID.")
        series_ids.add(series_id)
        study_ids.add(study_id)
        modalities.add(modality)
        rows, columns = getattr(dataset, "Rows", None), getattr(dataset, "Columns", None)
        if rows is None or columns is None:
            raise ImagingReviewError("Every DICOM instance must include image dimensions.")
        shapes.add((int(rows), int(columns)))
        position = getattr(dataset, "ImagePositionPatient", None)
        orientation = getattr(dataset, "ImageOrientationPatient", None)
        if position is not None and orientation is not None:
            try:
                positions.append(tuple(float(item) for item in position))
                orientations.add(tuple(round(float(item), 5) for item in orientation))
            except (TypeError, ValueError):
                pass
        datasets.append(dataset)
    if len(series_ids) != 1:
        raise ImagingReviewError("Selected instances belong to multiple DICOM series. Select one series at a time.")
    if len(study_ids) != 1:
        raise ImagingReviewError("Selected instances belong to multiple DICOM studies. Select one study series at a time.")
    if len(shapes) != 1:
        raise ImagingReviewError("DICOM instances have inconsistent image dimensions.")
    if len(orientations) > 1:
        raise ImagingReviewError("DICOM instances have inconsistent image orientations.")
    duplicate_positions = len(positions) != len(set(positions))
    rows, columns = next(iter(shapes))
    return {
        "inspection_type": "dicom_series_header_metadata",
        "module_id": module_id,
        "modality_check": "matches_selected_module",
        "metadata": {"instances": len(datasets), "modality": next(iter(modalities)),
                     "rows": rows, "columns": columns,
                     "position_headers_available": len(positions),
                     "orientation_consistent": len(orientations) == 1,
                     "duplicate_slice_positions": duplicate_positions},
        "patient_identifiers_returned": False,
        "pixel_data_read": False,
        "model_inference_performed": False,
        "note": "Series consistency check only. Pixel data and patient-identifying DICOM fields are not returned.",
    }
