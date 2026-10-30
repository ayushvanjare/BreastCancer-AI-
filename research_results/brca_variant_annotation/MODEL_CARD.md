# ClinVar BRCA variant annotation classifier

**Research-only.** This model classifies public BRCA1/BRCA2 variant annotations as pathogenic/likely pathogenic or benign/likely benign. It does not predict whether a person carries an inherited variant, develop cancer, or need care.

- Model: logistic regression, grouped holdout split (seed 20261029).
- Records after ambiguous-locus exclusion: 2938; training: 2357; holdout: 581.
- Holdout accuracy: 0.983; balanced accuracy: 0.980; ROC AUC: 0.995; average precision: 0.989.
- Pathogenic-class precision: 0.973; recall: 0.973.
- Locus groups shared across train and holdout: 0.

## Important limitations

The source is ClinVar itself, so this internal holdout is not independent clinical validation. Curated variant labels are not individual patient outcomes. Metrics can reflect ClinVar curation patterns and class balance. The model is not connected to the patient-facing application. Do not use its output for screening, diagnosis, treatment, or patient-care decisions.
