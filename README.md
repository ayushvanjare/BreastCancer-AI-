# BreastCare AI — Research Prototype

A local-first research prototype combining tabular exploration, report text extraction, imaging input review, and an optional BreaKHis histopathology research experiment.

## Included in this Phase 2.2 release
- React + TypeScript + Vite responsive dashboard (white, navy, teal)
- Seven dedicated module entry pages: histopathology, CT, MRI, X-ray/mammography, BRCA genomics readiness, doctor reports, CSV
- Python FastAPI backend with health, module metadata, registration, login, and demo analysis endpoints
- SQLite by default for easy local setup; database file is created on first startup
- Password hashing using Python's standard-library PBKDF2-HMAC and signed bearer tokens
- Account-protected uploads with encrypted local history for source files and analysis results
- Docker Compose option
- Windows, PowerShell, and Linux/macOS launch scripts
- Basic automated backend tests and a model manifest
- CSV upload (50 MB maximum) with shape, column types, missingness, numeric descriptive statistics and chart-ready category counts
- BRCA cohort preflight (50 MB maximum) for a de-identified CSV; checks schema and aggregate labels in memory without retaining rows or predicting mutation status
- Doctor report text extraction from digital/scanned PDFs and images (25 MB maximum; OCR for scans)
- Five-fold BreaKHis experiment results plus BACH external research evaluation
- 20 local BreaKHis ResNet-18 fold/magnification checkpoints and five scratch-CNN baseline checkpoints; the app can select all 25 checkpoints when a compatible existing PyTorch environment is configured
- Single-file CT/MRI/X-ray metadata review for raster images or DICOM headers; this is not image inference
- No internet connection required after dependencies have been installed

## Important medical AI limitations
This is a research software prototype, not a clinically validated diagnostic product. This local copy includes 20 BreaKHis ResNet-18 checkpoints and five historical scratch-CNN checkpoints. A generated-image API smoke test passed on the existing CPU-only Anaconda PyTorch environment; the separate CUDA Python environment remains blocked by Windows Application Control on `c10.dll`. No CT, MRI, mammography/X-ray, or patient-level BRCA risk models are included. A separate offline ClinVar variant-annotation research model is available; it is not integrated into the app. The ResNet-18 workflow had near-chance accuracy and poor specificity on the separate BACH evaluation; its output is not a diagnosis. Dataset-derived checkpoint redistribution is not cleared for the submission ZIP until the applicable terms have been reviewed. CT, MRI, and radiology workflows inspect basic file metadata only. CSV analysis returns descriptive statistics only. Doctor report processing extracts text only; OCR may misread content and does not summarize or interpret it. Do not use this software for clinical decisions.

The proposed data requirements and gated next steps for MRI, CT, and BRCA genomics are in [MODEL_DEVELOPMENT_ROADMAP.md](MODEL_DEVELOPMENT_ROADMAP.md). Mammography is paused at the user's direction; its local pilot has too few verified image pairs for training.

## Requirements
- Python 3.11, 3.12, or 3.13 recommended
- Node.js 20 LTS or newer (npm included)
- Optional: Docker Desktop / Docker Engine with Compose
- Optional: Git
- Tesseract OCR installed and available on `PATH` for scanned PDFs and image reports (digital PDFs can be read without Tesseract)

The dashboard, CSV, reports, and metadata review do not require a GPU. Optional histopathology inference uses a separate configured Python environment with PyTorch, torchvision, and Pillow; the project never installs or pins PyTorch.

## Run on Windows (recommended)
1. Extract the ZIP to a normal writable folder.
2. Open PowerShell in the extracted `BreastCare_AI_Phase2_2` folder.
3. Run the included launch script:
   ```powershell
   .\run_windows.ps1
   ```
   If PowerShell policy blocks scripts, use Command Prompt:
   ```bat
   run_windows.bat
   ```
   The first run creates the backend environment and installs Python and npm dependencies. Later runs reuse them. To refresh dependencies deliberately, run `.\run_windows.ps1 -InstallDependencies` in PowerShell or `run_windows.bat --install-dependencies` in Command Prompt.
4. Open the frontend at `http://localhost:5173`.
5. Backend API docs: `http://127.0.0.1:8000/docs`.

The launcher opens one window for the API and one for the frontend. Stop the app by pressing **Ctrl+C** in both windows or closing both windows. If the launcher reports that port 8000 or 5173 is busy, close any existing BreastCare AI server windows before starting it again.

The first setup requires internet access to install Python and npm dependencies. After installation, the dashboard and API run locally. The scripts do not install or pin PyTorch or download additional model weights. To preserve an existing CUDA-enabled PyTorch installation, use its existing environment and install only the backend requirements if necessary; these requirements do not list PyTorch. The included checkpoint files are documented in `model_artifacts/checkpoint_manifest.json`; the CPU inference worker passed a generated-image smoke test in this local setup, while CUDA remains unavailable in the selected runtime.

## Run manually
### Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```

## Environment configuration
Copy `backend/.env.example` to `backend/.env` if you want to customize settings. A random development secret is generated when `APP_SECRET_KEY` is not supplied; set a stable, strong secret for any shared deployment. Never expose this development server directly to the public internet.

### Saved upload privacy
Analysis uploads require a signed-in account. Original files and result data are encrypted in the local SQLite database and account-scoped. The History page renders saved summaries as readable tables/cards and previews saved images, PDFs, and CSV samples; use Download original to retrieve the complete source file. A local Fernet key is created at `backend/.history.key` on first save and excluded from Git and source ZIPs. Keep this key private and back it up separately if history must remain readable after moving the database; losing the key makes existing encrypted history unreadable. Delete records from the History page when no longer needed. This local prototype is not a secure clinical-record system: use authorized, de-identified research data only, never identifiable patient files, and do not expose the app publicly.

## API endpoints
- `GET /api/health` — status and configured database
- `GET /api/modules` — seven module descriptions and readiness
- `POST /api/auth/register` — `{ "email": "...", "username": "...", "password": "..." }`
- `POST /api/auth/login` — form-encoded `username` (email or username) and `password`
- `GET /api/auth/me` — current user (Bearer token)
- `POST /api/analysis` — authenticated readiness endpoint; it does not fabricate predictions
- `POST /api/csv/analyze` — multipart field `file`; requires a bearer token, accepts CSV files up to 50 MB, returns descriptive summaries, and saves the upload and result encrypted in account history.
- `POST /api/reports/extract` — multipart field `file`; requires a bearer token, accepts PDF/image reports up to 25 MB, returns extracted text, and saves the upload and result encrypted in account history. Scanned PDFs are limited to 20 pages.
- `POST /api/research/brca/preflight` — multipart field `file`; authenticated schema and aggregate-label check for a de-identified CSV with `sample_id`, `target_type`, and `label`; raw rows are not retained and prediction is not performed.
- `GET /api/history` — list the signed-in user's saved analysis records
- `GET /api/history/{id}` — view a saved result belonging to the signed-in user
- `GET /api/history/{id}/file` — download the original upload belonging to the signed-in user
- `DELETE /api/history/{id}` — delete the result and original upload belonging to the signed-in user
- `POST /api/imaging/inspect` — multipart fields `module_id` and `file`; inspects one raster or DICOM header up to 50 MB, or one NIfTI header up to 500 MB. No image inference or patient identifiers are returned.
- `POST /api/imaging/series/inspect` — multipart fields `module_id` and repeated `files`; checks one DICOM series (up to 500 instances, 250 MB total) for modality, image dimensions, and repeated slice positions. Pixel data is not read; encrypted originals are kept together as a ZIP history item.
- `POST /api/research/histopathology/predict` — multipart fields `file`, `checkpoint_id` (from `/api/modules`), and optional `explain`; local BreaKHis ResNet-18 or scratch-CNN scores, with Grad-CAM for ResNet-18, explicitly research-only. Requires the separate model configuration below.
- `GET /docs` — interactive API documentation

## Git repository
This folder includes `.gitignore` and an initial Git setup helper. To create a repository:
```bash
git init
git add .
git commit -m "Initial BreastCare AI Phase 1 foundation"
```
Then create an empty repository on your Git host and follow its instructions to add a remote and push. A remote GitHub/GitLab repository is not created automatically by this package.

For offline sharing, a companion `BreastCare_AI_Phase1.bundle` can be imported with:
```bash
git clone BreastCare_AI_Phase1.bundle BreastCare_AI
```
A Git bundle carries Git history and source code, but not ignored model weights, private datasets, or local environment files.

## Tests
```bash
cd backend
python -m pip install -r requirements-dev.txt
pytest -q
```

## Phase 2.1 CSV workflow
Select **CSV Analysis** in the dashboard, sign in, choose a `.csv` file, and click **Analyze CSV**. The endpoint checks the extension and compatible content type, reads at most 50 MB plus one byte, tries common text encodings, detects common delimiters, validates quoted row structure and field counts, and parses with pandas. It returns dimensions, inferred dtypes, missing-value counts/percentages, numeric summary statistics, and top category counts suitable for charts. Empty, malformed, unsupported, and oversized inputs return actionable HTTP errors. The original file and descriptive result are saved encrypted in local account history. These statistics are not diagnosis or prediction.

### Run manually on Windows PowerShell
Backend terminal (from the project root):
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Frontend terminal (from the project root):
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`. If `.venv` already contains CUDA-enabled PyTorch, activate that environment and install the listed backend requirements there; PyTorch is neither installed nor changed by this project.

## Phase 2.2 doctor report text extraction
Open **Doctor Reports**, sign in, select a PDF or image, and click **Extract text**. Digital PDFs are read from their embedded text. Scanned PDFs and images are processed with Tesseract OCR installed locally on the computer. The encrypted file and extracted text are saved to the account history. Uploads are limited to 25 MB; PDFs are limited to 20 pages. The interface returns extracted text for human review and does not summarize, interpret, or diagnose. OCR can omit or misread content, so compare the output with the source report. If OCR reports that Tesseract is unavailable, install Tesseract OCR, make sure its executable is on `PATH`, and restart the backend terminal.

## Research-only experiment results and optional inference
Open **Experiment results** to view the five-fold BreaKHis summary and the separate 400-image BACH external evaluation. The BACH models were near chance with low non-carcinoma specificity. The output is not clinical validation or patient-care evidence. Detailed methods and limitations are in `BREAKHIS_EXPERIMENT_SUMMARY.md` and `PROJECT_SUBMISSION_REPORT.md`.

Optional local inference can use one of the included ResNet-18 checkpoints after a compatible Python interpreter with PyTorch, torchvision, and Pillow is verified. The project does not install or pin PyTorch. Set these in `backend/.env` (replace the placeholders with full paths):
```dotenv
RESEARCH_MODEL_PYTHON=C:/path/to/your/existing/python.exe
# Optional fallback for a checkpoint outside the included model selector.
HISTOPATHOLOGY_CHECKPOINT=../model_artifacts/breakhis/resnet18/fold1_40x/resnet18_fold1_40x.pt
```
Restart the backend after changing `.env`. The example path is only a configuration example, not a recommended model. The checkpoint selector can use all 25 included ResNet-18 and scratch-CNN weights; the fallback setting is optional. Generated-image smoke checks passed for the ResNet-18 worker and all five scratch-CNN checkpoints using the existing CPU-only Anaconda environment. The separate CUDA Python environment could not load `c10.dll`, and no PyTorch files were changed. The BACH results were poor. Do not infer from patient images. Grad-CAM is a visualization of model activations, not an explanation of medical causation.

The CT, MRI, and X-ray pages inspect selected single-file headers, check DICOM series consistency, and read NIfTI headers. They do not process voxel values, perform segmentation, or provide prediction. Compatible modality-specific datasets, licensing, models, and evaluation evidence are not provided, so modality-specific prediction cannot responsibly be enabled from the files available here. Header checks are technical input review, not diagnostic safeguards or clinical validation.

### Optional BACH external research evaluation
After obtaining permission for the intended BACH use, `evaluate_bach_external.py` evaluates the saved BreaKHis ResNet-18 checkpoints on the four-class BACH `Photos` folder. It decodes and resizes images in memory and does not overwrite the dataset. The research-only binary mapping is `Benign` and `Normal` → non-carcinoma, and `InSitu` and `Invasive` → carcinoma; the original BACH labels remain in the per-image predictions. This mapping is study-specific, and results must be reported separately from BreaKHis results. The script evaluates all 20 saved fold/magnification checkpoints and writes JSON metrics, a summary CSV, and per-image predictions. Fold-model spread is not a patient-level confidence interval.

Run from the project root in Windows PowerShell, using the existing CUDA-enabled PyTorch environment (the command does not install or pin PyTorch):
```powershell
$python = "$env:USERPROFILE\Downloads\BreastCare_AI_Phase1\BreastCare_AI\.venv\Scripts\python.exe"
& $python .\evaluate_bach_external.py `
  --photos-dir "$env:USERPROFILE\Downloads\BACH_External\extracted\ICIAR2018_BACH_Challenge\Photos" `
  --checkpoints-dir "$env:USERPROFILE\Downloads\BreaKHis\resnet18_results" `
  --output-dir .\research_results\bach_external `
  --device cuda
```
The outputs are research-only, not for diagnosis or clinical use, and not clinical validation. Keep the dataset permission and required attribution with any report.

## Completed project milestones and remaining research inputs
- CT/MRI and BRCA model development still requires a defined research task, authorized labeled data, training, and independent evaluation. Mammography development is paused; see `MODEL_DEVELOPMENT_ROADMAP.md` for the track statuses.
- See `PROJECT_MILESTONES.md` for a delivery checklist and the exact boundary between implemented workflows and model-dependent milestones.
- Local dashboard and FastAPI API with seven workflows, including a BRCA research-planning page with no genomic upload or prediction.
- CSV data-quality summaries, descriptive statistics, and chart-ready data; report text extraction; single-image/DICOM-header metadata review.
- BreaKHis baseline training, fold-wise metrics, BACH external evaluation, result reporting, optional local research inference, and Grad-CAM visualization.
- Real CT/MRI/X-ray prediction, patient-level BRCA risk prediction, and clinical validation are not included. An offline ClinVar variant-annotation research artifact is available, but it does not predict carrier status for an individual. Encrypted local analysis history and technical DICOM-series/NIfTI header review are implemented. Predictive milestones require compatible, licensed labeled data and rigorous independent evaluation; clinical validation also requires qualified clinical partners and formal study governance.

