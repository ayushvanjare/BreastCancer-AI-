# TCGA-BRCA somatic mutation data

This folder contains the open-access TCGA-BRCA masked somatic MAF cohort. It describes tumor-acquired mutations and must not be described as inherited BRCA status or as a predictor of cancer incidence.

- Original, checksum-verified files: `raw/`
- GDC manifest and reproducible scripts: `metadata/`
- BRCA1/BRCA2-only extracted variant rows: `derived/`

The extracted table is exploratory. Define the target and patient-level split before model training; this download alone does not establish clinical validity.
