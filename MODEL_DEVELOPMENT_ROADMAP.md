# Predictive model development roadmap

This roadmap starts the four requested research-model tracks without presenting missing data or untrained code as working prediction. Every model remains research-only. No output may guide screening, diagnosis, treatment, or patient care.

## Current track status

| Track | Current evidence in this project | Proposed first research task | Current status |
|---|---|---|---|
| BRCA genomics — priority 1 | Local ClinVar BRCA1/2 variant-level records and a trained research-only variant annotation classifier are now available. Germline carrier status and tumor somatic alteration remain distinct targets. | A variant-level pathogenic/benign annotation pilot has been trained on ClinVar. The mandatory patient-level inherited-risk task still requires an authorized cohort with participant-level genetic results and clinical labels. Somatic data remains a separate tumor mutation analysis. | Variant annotation prototype trained; no patient-level carrier-risk model, clinical validation, or app inference. |
| MRI | No images/checkpoint are local. TCIA's QIN-BREAST collection provides longitudinal MR and treatment-response labels for 67 subjects, with an 11.41 GB multimodality collection. | Pilot an exploratory baseline MRI treatment-response classifier using only pre-treatment sequences and patient-level splits. | Candidate cohort and endpoint identified; download awaits TCIA Data Usage Policy acceptance. Small cohort; research-only. |
| CT | No images/checkpoint are local. QIN-BREAST provides longitudinal PET/CT and treatment-response data for 67 subjects within its 11.41 GB multimodality collection. | Pilot an exploratory baseline CT treatment-response classifier using only pre-treatment CT series and patient-level splits. | Candidate cohort and endpoint identified; download awaits TCIA Data Usage Policy acceptance. Small cohort; research-only. |
| Mammography | A local CBIS-DDSM Mass metadata pilot: 20 selected patients; only 2 image/mask pairs are verified. | Classify a cropped mass image as benign or malignant, after the data gate passes. | Paused at the user's direction; no training or model claim. |

## Mammography track (paused)

This was the project's initial proposed track, but mammography model work is now paused at the user's direction. The project already has CBIS-DDSM mass labels and a pilot audit. TCIA lists CBIS-DDSM as a mammography collection with 1,566 subjects, 10,239 images, and a 163.6 GB full-collection size; its data citation and CC BY 3.0 license must be followed. The local pilot is not a trainable cohort: its 20-case workflow sample has only 2 verified image/mask pairs. Do not start a download or training run unless the user resumes this track.

### Current acquisition checkpoint

- The official TCIA Mass-Training ROI-and-cropped-images manifest has been prepared and lists 1,410 series.
- The official portable TCIA Data Retriever release `1.21.2-20261026` has been downloaded locally and its SHA-256 matches the published GitHub release digest.
- The download destination is prepared separately from the 20-case pilot. The image transfer has not started: TCIA requires a user to review and accept its Data Usage Policy in the retriever. No one has accepted that policy on the user's behalf.
- A full-root metadata audit found 8 DICOM file paths and 2 verified image/mask pairs in the pilot. Do not train from the pilot.

If resumed later, the proposed mammography model is **cropped mass benign-versus-malignant research classification**. It must use the training CSV only for fitting and validation, keep patients isolated across splits, and reserve the official test cases for one final evaluation. No model should be trained on the 20-case pilot or report results from it.

## Data and model gates

1. Audit CSV labels against DICOM `PatientID`, `SeriesInstanceUID`, `SeriesDescription`, and pixel-data readability; remove duplicate downloads and resolve all label/path mismatches.
2. Confirm dataset access terms, citation requirements, and whether local weights may be shared. Keep source datasets and weights out of a submission archive until redistribution terms are settled.
3. Define patient-level training/validation/test partitions before reading image pixels for training. Never let images from one patient cross partitions.
4. Train a simple baseline first, record exact preprocessing and random seeds, and save cohort counts and split IDs alongside metrics.
5. Evaluate only after the dataset gate passes. Report class-specific sensitivity and specificity, AUROC/AUPRC, calibration where appropriate, confidence intervals by patient, and limitations. Do not label the result clinically validated.
6. Register an inference checkpoint only after architecture, preprocessing, labels, input format, and reproducible evaluation artifacts are recorded.

## Mandatory BRCA track

The BRCA target must be fixed before training. For inherited-risk relevance, the preferred question is whether a patient is a confirmed germline BRCA1/2 pathogenic/likely pathogenic carrier, using a clinical genetic-test result as the reference label. This requires authorized germline-labeled data; TCGA's open somatic MAF is not a substitute, and germline/low-level genomic files may require controlled access. If only open somatic data are used, the project must describe that as a separate tumor-somatic research task, not hereditary-risk prediction. Any future clinical use would need independent clinical validation and the applicable ethics/regulatory review.

## Current germline variant annotation pilot

A separate ClinVar-based BRCA1/BRCA2 variant annotation classifier is saved under `model_artifacts/brca_variant_annotation/`; its grouped holdout metrics and model card are in `research_results/brca_variant_annotation/`. It classifies ClinVar variant-label categories only. The internal holdout comes from the same source database and is not independent clinical validation. The model is not integrated into the app and does not predict an individual's carrier status or cancer risk.

## Authoritative dataset starting points

- [QIN-BREAST on TCIA](https://www.cancerimagingarchive.net/collection/qin-breast/) — 67-subject longitudinal PET/CT and quantitative MR cohort with treatment-response labels; collection download is listed as 11.41 GB and CC BY 3.0. TCIA requires the downloader to agree to its Data Usage Policies and Restrictions. This cohort can support only an exploratory pilot, not clinical claims.
- [TCGA-BRCA on the NCI Genomic Data Commons](https://portal.gdc.cancer.gov/projects/TCGA-BRCA) — 1,098 cases. Open-access somatic MAFs may support a somatic BRCA1/2 target; germline/low-level genomic files are controlled access, so this plan does not assume permission for those files.
- [GDC MAF format and access](https://docs.gdc.cancer.gov/Data/File_Formats/MAF_Format/) — explains open somatic MAF processing and its filtering limitations.
- [CBIS-DDSM on TCIA](https://www.cancerimagingarchive.net/collection/cbis-ddsm/) — mammography images, pathology labels, and ROI material; data citation and license apply.
- [Duke Breast Cancer MRI on TCIA](https://www.cancerimagingarchive.net/collection/duke-breast-cancer-mri/) — DCE-MRI with clinical, imaging, and genomic supporting data; large download and non-commercial terms apply.
- [TCGA-BRCA in the NCI Genomic Data Commons](https://portal.gdc.cancer.gov/projects/TCGA-BRCA) — mixed open and controlled-access data; the precise intended mutation target and access tier must be established.
- [CMB-BRCA on TCIA](https://www.cancerimagingarchive.net/collection/cmb-brca/) — a multi-modality breast cancer collection including CT, MRI, mammography, and other imaging; small/ongoing for a standalone CT model.

## Safety boundary

The application must continue to describe these tracks as unavailable until compatible checkpoints and evaluation evidence are registered. A functioning upload screen, an available dataset, generated-image smoke checks, or a model trained on a tiny pilot are not evidence of prediction accuracy or clinical value.

## Planning interfaces

The app includes a BRCA genomics page with a de-identified cohort CSV preflight. It does not accept raw sequence/variant files or provide inference. CT, MRI, and mammography metadata-review pages show modality-specific research gates; they do not analyze image pixels. The mammography page reflects the current audit (2 verified image/mask pairs among the 20-case pilot), and this count must be refreshed from the audit before being treated as current.
