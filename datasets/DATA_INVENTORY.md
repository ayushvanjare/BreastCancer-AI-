# Dataset inventory and next actions

Last reviewed: 2026-10-29

## Dataset tracks

| Track | Location | Current contents | Status and next action |
|---|---|---|---|
| CT | `CT/QIN-BREAST/` | Separate `raw`, `labels`, and `metadata` folders are ready | No CT data downloaded. QIN-BREAST is a candidate cohort. TCIA requires the user to review and accept its Data Usage Policies before retrieval; no acceptance was made on the user's behalf. |
| MRI | `MRI/QIN-BREAST/` | Separate `raw`, `labels`, and `metadata` folders are ready | No MRI data downloaded. The same QIN-BREAST collection includes MR imaging and treatment-response information. Confirm appropriate endpoints and cohort splits after access. |
| Germline BRCA | `BRCA/Germline/ClinVar/` | 6,319 source summaries in compressed JSONL; 3,021 filtered variant records in TSV; query/provenance file and reproducible downloader | Public **variant-level** germline interpretations downloaded; a research-only variant annotation classifier was trained with a locus-grouped holdout (see `../research_results/brca_variant_annotation/MODEL_CARD.md`). This is not a dataset of people tested for BRCA and cannot train or validate a patient-level hereditary-risk model. A separately authorized patient cohort with genotype and clinical outcome labels is still needed in `BRCA/Germline/Patient-Level/`. |
| Somatic BRCA | `BRCA/Somatic/TCGA-BRCA/` | 992 open-access TCGA-BRCA masked somatic MAF files (32,009,844 bytes), GDC manifest, downloader, and extracted BRCA1/BRCA2 table | Downloaded with GDC-provided MD5 and size verification. Extracted table has 25 BRCA1 and 27 BRCA2 mutation rows. No supervised somatic model was trained: these MAFs do not provide a suitable patient-level clinical outcome label for the requested risk prediction task. This is tumor-acquired mutation data from a cancer cohort; it is not inherited BRCA status or a model for predicting who will develop cancer. |
| Mammography | `Mammography/CBIS-DDSM/` | Small existing pilot, source label CSVs, TCIA manifest and metadata; 123,820,418 bytes in the organized folder | Mammography **model training is paused** by project direction. Keep its pilot and labels organized; it was not included in either BRCA track. |
| Histopathology | `../model_artifacts/` and `../research_results/` | Existing BreaKHis model checkpoints and BACH external evaluation outputs | These are retained model/results artifacts, not raw datasets. |

## Plain-language distinction: germline and somatic

- **Germline** means inherited. A patient-level model needs each person's genetic result and an appropriate hereditary-risk label. ClinVar here contains evidence about variants, not individual patients.
- **Somatic** means acquired in tumor tissue. The TCGA files describe mutations found in breast tumor samples. They cannot be used as a substitute for inherited-carrier labels.
- The two data types are stored in separate folders and must remain separate in analysis, model names, and evaluation reports.
- A clinically important use case is not the same thing as clinical validation. Neither this public dataset nor an internal score proves clinical validity or readiness for patient care.

## Dataset provenance

### Germline variant evidence

- Source: [NCBI ClinVar downloads](https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/) via NCBI E-utilities.
- Scope: BRCA1/BRCA2; Pathogenic, Likely pathogenic, Benign, and Likely benign; ClinVar review status `criteria provided, multiple submitters, no conflicts`; rows associated with breast/ovarian condition descriptions.
- Raw responses are in `BRCA/Germline/ClinVar/raw/clinvar_brca1_brca2_multisubmit_no_conflict.jsonl.gz`.
- Derived table and query counts are in `BRCA/Germline/ClinVar/derived/`.
- Re-run using `BRCA/Germline/ClinVar/download_clinvar_brca_subset.py`. ClinVar changes over time; record the download date in reports.

### Somatic mutation cohort

- Source: [NCI Genomic Data Commons API](https://gdc.cancer.gov/developers/gdc-application-programming-interface-api); project TCGA-BRCA, open-access MAF files, data type Masked Somatic Mutation, Aliquot Ensemble Somatic Variant Merging and Masking workflow.
- [GDC MAF documentation](https://docs.gdc.cancer.gov/Data/File_Formats/MAF_Format/) explains that open somatic MAFs are filtered to mask potential germline variants.
- Manifest with GDC IDs, filenames, sizes, MD5 values and associated metadata: `BRCA/Somatic/TCGA-BRCA/metadata/gdc_tcga_brca_somatic_maf_manifest.json`.
- Re-download with `BRCA/Somatic/TCGA-BRCA/metadata/download_tcga_brca_somatic.py`. Rebuild the gene table with `BRCA/Somatic/TCGA-BRCA/metadata/extract_tcga_brca1_brca2.ps1`.

### CT and MRI candidate

- Candidate collection: [QIN-BREAST on TCIA](https://www.cancerimagingarchive.net/collection/qin-breast/).
- Before any download, the user must accept the [TCIA Data Usage Policies](https://www.cancerimagingarchive.net/access-data/). The previously identified collection is about 11.41 GB; confirm available disk space and the correct series/labels before retrieval.

## Cleanup and retention

See [CLEANUP_LOG.md](CLEANUP_LOG.md) for removed items and why project outputs, environments, labels and source data were retained.

