# BreastCare AI project milestones

This document describes what the current source package actually implements. It separates working software from research capabilities that still need suitable data, model weights, or validation evidence.

| Milestone | Status | Delivered |
|---|---|---|
| Local application foundation | Complete | React/TypeScript dashboard, FastAPI API, SQLite account endpoints, Windows launch scripts, module registry, local settings, and API documentation. |
| CSV exploration | Complete | Bounded in-memory upload, robust text decoding and pandas parsing, dimensions, column types, missing values, descriptive statistics, and chart-ready category counts. This is not clinical prediction. |
| Report text extraction | Complete | In-memory PDF/image extraction, embedded PDF text and optional local Tesseract OCR, with size/page limits and human-review warnings. No medical interpretation. |
| BreaKHis research experiment | Complete as a baseline | ResNet-18 training script, five official folds at four magnifications, group-separated validation, metrics/checkpoints generated outside the source archive, and a results summary. |
| BACH external evaluation | Complete as a research evaluation | 400-image external evaluation using the original four classes and a documented binary grouping. Mean accuracy was about 49–52% with poor non-carcinoma specificity, indicating weak transfer in this setup. |
| Optional histopathology demonstration | Implemented; requires a compatible runtime | Research-only inference can select any of the 20 included ResNet-18 or five scratch-CNN checkpoints in an isolated local worker; Grad-CAM is available for ResNet-18. It requires a compatible existing PyTorch/torchvision environment. Do not use on patient images. |
| CT/MRI/X-ray input review | Complete as metadata review only | Single raster/DICOM/NIfTI header review plus same-series DICOM consistency checks; pixel/voxel data are not analyzed and no prediction is produced. |
| BRCA cohort preflight | Implemented as an in-memory schema check | Accepts a de-identified cohort CSV and returns aggregate schema/label quality counts. Raw rows are not saved; no variant interpretation or prediction is performed. |
| BRCA variant annotation research pilot | Trained as a separate research artifact | ClinVar BRCA1/2 variant annotations were grouped by genomic locus into train/holdout partitions. This classifies curated variant labels only; it is not patient-level carrier-risk prediction, independent clinical validation, or connected to app inference. |
| BRCA genomics research planning | Implemented as readiness guidance only | The app distinguishes germline from somatic targets and lists study-design/data gates. Genomic upload, interpretation, and prediction are disabled. |
| Modality-specific medical prediction | Not complete | No compatible licensed CT/MRI/X-ray/mammography datasets or trained checkpoints were supplied. Creating only a screen or using the histopathology model for these modalities would be misleading. |
| Patient-level BRCA prediction | Not complete | Requires an authorized patient-level germline cohort with an explicitly defined clinical target, independent evaluation, and clinical oversight. The ClinVar variant annotation pilot and TCGA somatic MAF cohort do not satisfy this requirement. The cohort preflight does not perform prediction. |
| Prediction model data preparation | Dataset tracks separated; one BRCA variant annotation pilot trained | CT/MRI image prediction still requires an authorized imaging cohort; patient-level BRCA prediction still requires germline participant data and clinical labels. Somatic BRCA MAF data is downloaded for research, but no clinical outcome model was trained from it. Mammography model work is paused. See `MODEL_DEVELOPMENT_ROADMAP.md`. |
| Account-protected encrypted analysis history | Implemented for local research use | Upload endpoints require a bearer token. Original uploads and results are encrypted in the local database, scoped to the signed-in account, and can be viewed, downloaded, or deleted. The local key must be kept private; this is not clinical-grade storage. |
| Patient-care safeguards | Local-prototype safeguards implemented | Upload workflows require sign-in, modality review never infers from image pixels, and UI/API output explicitly says research-only or metadata-only. No emergency, diagnosis, or treatment advice is provided. This does not make the app safe for patient care. |
| Production deployment and clinical safeguards | Not complete | No public deployment, clinical-grade privacy/security controls, audit program, or clinical validation is provided. Do not use identifiable patient data or expose this prototype publicly. |

## Before demonstrating

1. Install Node.js 20 LTS or newer and Python 3.11, 3.12, or 3.13; reopen VS Code after installing Node.js so its terminal refreshes `PATH`.
2. Follow `README.md` to install the backend and frontend dependencies and start each service.
3. Confirm `http://127.0.0.1:8000/docs` and `http://localhost:5173` open.
4. In the dashboard, demonstrate CSV descriptive analysis and report text extraction with non-sensitive example files. Demonstrate imaging metadata review with a sample file only if available.
5. Show the BreaKHis/BACH results and explain that BACH transfer was poor and neither experiment is clinical validation.
6. Configure the optional histopathology worker with a compatible local PyTorch Python environment; CPU inference is supported and CUDA is optional. Keep the source ZIP free of datasets, checkpoints, `.env`, `.history.key`, and virtual environments. Keep the local encryption key private and separately backed up if you need saved history.

## Research and safety boundary

No displayed score is a diagnosis, risk estimate, screening result, or recommendation. Do not upload patient records or use the application to guide care. BACH use must follow the dataset permission and attribution terms reported by the project owner.

