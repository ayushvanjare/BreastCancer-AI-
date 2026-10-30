# BreastCare AI — Research Prototype Project

## Abstract

BreastCare AI is a local-first research prototype for exploring breast-cancer-related datasets. It provides a React dashboard with six workflows and a FastAPI backend for descriptive CSV analysis, report text extraction, and limited imaging metadata review. A separate experiment evaluated ImageNet-pretrained ResNet-18 models on BreaKHis histopathology images at four magnifications; the saved checkpoints were evaluated on 400 BACH microscopy images. An optional local inference worker can use a compatible BreaKHis checkpoint, with a Grad-CAM visualization. The BACH results showed poor external transfer. The software does not diagnose cancer, and neither experiment is clinical validation.

## Project objectives

- Provide one local workspace for several breast-cancer research data workflows.
- Support descriptive CSV exploration and report-text extraction.
- Establish a reproducible, research-only histopathology image-classification baseline.
- Present model results with clear limits and avoid clinical inference.

## Implemented software

- React, TypeScript, and Vite dashboard with module navigation, model registry, history, settings, and an Experiment Results page.
- FastAPI backend exposing health, module, authentication, CSV-analysis, report-extraction, DICOM/raster metadata review, and optional research histopathology endpoints.
- CSV analysis: accepts files up to 10 MB, reports shape, columns, inferred data types, missing values, descriptive statistics, and chart-ready category counts. Authenticated uploads and results are encrypted in local account history.
- Doctor Reports: extracts embedded PDF text or uses local Tesseract OCR for scanned PDFs and images. Uploads are limited to 10 MB and PDFs to 20 pages. Extracted text is for human review and is not interpreted.
- Histopathology inference is optional and uses a separately configured local PyTorch environment. This local project copy contains 20 ResNet-18 and five scratch-CNN checkpoints; the application lets the user select among them. Generated-image CPU smoke checks passed for the ResNet-18 worker and all five scratch-CNN weights. The returned scores are not calibrated probabilities; Grad-CAM is available for ResNet-18 only and is a visualization. The configured BreaKHis models showed near-chance accuracy and poor non-carcinoma specificity on BACH. Checkpoint redistribution terms still require review before submission packaging.
- CT, MRI, and X-ray modules inspect raster, DICOM, and NIfTI headers and check technical consistency within one uploaded DICOM series. Pixel/voxel values are not interpreted and no modality-specific inference is implemented.
- Analysis uploads require a bearer token. Original uploads and result JSON are encrypted in the local database, scoped to the account, and can be viewed, downloaded, or deleted. This local prototype is not clinical-grade storage and must not contain identifiable patient files.

## BreaKHis experiment method

- Dataset: BreaKHis histopathology images with benign and malignant labels.
- Model: ImageNet-pretrained ResNet-18; early layers frozen while layer 4 and the classifier were fine-tuned.
- Each magnification (40X, 100X, 200X, 400X) was evaluated separately at 128 × 128 pixels.
- Five official fold splits were used per magnification. A group-separated validation subset was selected from each fold’s training split. The official test split was held out.
- Training used a maximum of 8 epochs with early stopping based on validation loss (patience 2).
- The RTX 3050 CUDA environment was used. Every run reported zero shared sample groups between fit, validation, and test partitions.
- Reported values below are arithmetic means of fold-level metrics. The fold test sets overlap, so they are not pooled as if they were distinct images.

## BACH external research evaluation

- The BACH Photos subset contained 400 images: 100 each in the original classes Benign, InSitu, Invasive, and Normal.
- The 20 saved BreaKHis ResNet-18 checkpoints (five folds at each of 40X, 100X, 200X, and 400X) were evaluated without retraining. Images were resized to 128 × 128 in memory, converted to RGB, and ImageNet-normalized; the source files were not overwritten.
- For this binary comparison, Benign and Normal were grouped as non-carcinoma, and InSitu and Invasive as carcinoma. This is a study-specific grouping; the prediction file retains the original four-class labels.
- The table reports the arithmetic mean across the five saved fold models for each training magnification. All five models were tested on the same 400 BACH images, so fold-model spread is descriptive variability, not a confidence interval or five independent BACH tests.

| BreaKHis training magnification | Mean BACH accuracy | Mean carcinoma recall | Mean non-carcinoma specificity | Mean balanced accuracy |
|---|---:|---:|---:|---:|
| 40X | 50.2% | 70.1% | 30.3% | 50.2% |
| 100X | 49.2% | 79.6% | 18.7% | 49.2% |
| 200X | 52.1% | 79.7% | 24.5% | 52.1% |
| 400X | 49.2% | 85.7% | 12.6% | 49.2% |

The external results are close to chance accuracy on this balanced binary grouping. Low non-carcinoma specificity means many Benign/Normal images were classified as carcinoma. In this evaluation setup, the BreaKHis models did not transfer reliably to BACH; these results are not clinical performance estimates.

## Results

| Magnification | Mean accuracy | Mean malignant recall | Mean benign specificity | Mean balanced accuracy |
|---|---:|---:|---:|---:|
| 40X | 77.0% | 82.9% | 65.4% | 74.1% |
| 100X | 77.2% | 83.7% | 64.4% | 74.1% |
| 200X | 81.4% | 82.9% | 78.1% | 80.5% |
| 400X | 81.3% | 83.0% | 78.2% | 80.6% |

In this experiment, 200X and 400X had similar averages and higher mean specificity than 40X and 100X. The results do not establish a reliable winning magnification; fold-level variation was material. The detailed fold ranges and additional notes are in `BREAKHIS_EXPERIMENT_SUMMARY.md`.

## Verification

The project owner confirmed that the frontend loads the Experiment Results page, the FastAPI `/docs` page opens, and the CSV Analysis and Doctor Reports workflows work locally. The BreaKHis training and BACH evaluation were run using the owner's CUDA-enabled RTX 3050 environment. These are software/research checks only; they do not validate medical performance.

## Limitations and responsible use

- These are exploratory experiments using checkpoints from one BreaKHis training setup. BACH results are a research-only external dataset evaluation, not clinical validation; no patient-level confidence intervals were calculated.
- Performance on BreaKHis does not establish performance at other hospitals, scanners, staining conditions, or patient populations.
- The BACH binary grouping loses distinctions between Normal and Benign and between InSitu and Invasive. Always report the original class counts and mapping with these results. The project owner reported receiving permission for the intended BACH use; retain the organizer correspondence and follow its conditions and attribution requirements.
- Do not use the model or these metrics for diagnosis, screening, triage, treatment, patient-image assessment, or other patient-care decisions. Optional inference is strictly a research demonstration and should use authorized research images only.

## How to run locally on Windows

Start the backend in one PowerShell terminal:

```powershell
Set-Location "$env:USERPROFILE\Downloads\BreastCare_AI_Phase2_2\backend"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```powershell
Set-Location "$env:USERPROFILE\Downloads\BreastCare_AI_Phase2_2\frontend"
npm run dev
```

Open `http://localhost:5173`. The Experiment Results page is at `http://localhost:5173/results`. Backend API documentation is at `http://127.0.0.1:8000/docs`.

Optional local BreaKHis inference can be enabled by setting `RESEARCH_MODEL_PYTHON` in `backend/.env` to an existing Python environment that already has compatible PyTorch, torchvision, and Pillow. CPU is supported; CUDA is optional. The app can select any of the 20 included ResNet-18 and five scratch-CNN checkpoints, so `HISTOPATHOLOGY_CHECKPOINT` is optional. The backend requirements do not install or pin PyTorch. The provided BreaKHis checkpoints showed poor transfer on BACH and must not be used for patient images.

## References

1. Spanhol, F. A., Oliveira, L. S., Petitjean, C., and Heutte, L. “A Dataset for Breast Cancer Histopathological Image Classification.” *IEEE Transactions on Biomedical Engineering*, 2016. DOI: 10.1109/TBME.2015.2496264.
2. BreaKHis dataset and download information: https://web.inf.ufpr.br/vri/databases/breast-cancer-histopathological-database-breakhis/
3. Aresta, G. et al. “BACH: Grand challenge on breast cancer histology images.” *Medical Image Analysis*, 56 (2019), 122–139. DOI: 10.1016/j.media.2019.05.010.
