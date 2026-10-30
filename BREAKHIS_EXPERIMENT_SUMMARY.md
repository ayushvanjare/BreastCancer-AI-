# BreaKHis ResNet-18 Baseline Experiment

## Scope

This is a research-only experiment on the public BreaKHis image dataset. It is not a diagnostic tool, clinical validation, or suitable for patient-care decisions.

## Setup

- Binary labels: benign and malignant.
- Model: ImageNet-pretrained ResNet-18; early layers frozen, layer 4 and classifier fine-tuned.
- Magnifications: 40X, 100X, 200X, and 400X, evaluated separately.
- Image size: 128 x 128.
- Maximum epochs: 8; early stopping based on validation loss with patience 2.
- For each official fold, the official test partition was held out. A group-separated validation set was created from the official training partition. Each run reported zero shared sample groups between fit, validation, and test.
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU using the existing CUDA-enabled PyTorch environment.
- Metrics below are simple arithmetic means of the five fold-level metrics, not pooled counts.

## Mean results across five fold runs

| Magnification | Accuracy | Malignant recall | Benign specificity | Balanced accuracy |
|---|---:|---:|---:|---:|
| 40X | 77.0% | 82.9% | 65.4% | 74.1% |
| 100X | 77.2% | 83.7% | 64.4% | 74.1% |
| 200X | 81.4% | 82.9% | 78.1% | 80.5% |
| 400X | 81.3% | 83.0% | 78.2% | 80.6% |

## Fold-level ranges

| Magnification | Accuracy range | Malignant recall range | Benign specificity range |
|---|---:|---:|---:|
| 40X | 72.1–80.7% | 76.7–89.5% | 43.3–76.6% |
| 100X | 73.6–80.8% | 72.5–92.1% | 46.9–75.5% |
| 200X | 75.8–84.5% | 70.2–88.8% | 64.9–86.1% |
| 400X | 76.9–84.7% | 79.2–86.8% | 71.6–86.6% |

## Interpretation

The 200X and 400X runs had higher mean accuracy and specificity than the 40X and 100X runs in this experiment. Their averages are nearly identical; the results do not establish a reliable winning magnification. Fold-level variation remains material. Several runs showed fit accuracy increasing while validation loss worsened, which is consistent with overfitting risk.

The five official test splits are not disjoint: the 40X test counts sum to 3,509, while each fold contains 1,995 40X images. Therefore, report the mean of fold-level metrics rather than treating all fold test predictions as 3,509 unique images or pooling them as one independent test set.

The earlier scratch CNN baseline at 40X had five-fold means of 65.8% accuracy, 68.4% malignant recall, 60.5% benign specificity, and 64.5% balanced accuracy. This is only an exploratory comparison: the scratch CNN used all official training images, while ResNet-18 reserved groups for validation.

## External dataset status

BACH Photos external research evaluation was run after the project owner reported obtaining permission for the intended use. The 400 images contained 100 each in the original classes Benign, InSitu, Invasive, and Normal. The 20 saved BreaKHis checkpoints were evaluated without retraining. Images were resized to 128 x 128 in memory, converted to RGB, and ImageNet-normalized; original image files were not overwritten.

For a binary comparison only, Benign and Normal were grouped as non-carcinoma, and InSitu and Invasive as carcinoma. This study-specific mapping loses the original four-class distinctions, which are retained in the per-image predictions. The table reports simple arithmetic means across the five saved fold models for each BreaKHis training magnification. Each fold model was evaluated on the same 400 BACH images. Fold-model spread is not a confidence interval or five independent BACH tests.

| BreaKHis training magnification | Mean BACH accuracy | Mean carcinoma recall | Mean non-carcinoma specificity | Mean balanced accuracy |
|---|---:|---:|---:|---:|
| 40X | 50.2% | 70.1% | 30.3% | 50.2% |
| 100X | 49.2% | 79.6% | 18.7% | 49.2% |
| 200X | 52.1% | 79.7% | 24.5% | 52.1% |
| 400X | 49.2% | 85.7% | 12.6% | 49.2% |

Accuracy was near 50% for every magnification. The low non-carcinoma specificity indicates that many Benign/Normal images were classified as carcinoma, so the saved BreaKHis models did not transfer reliably to this BACH evaluation setup. The generated `research_results/bach_external/bach_external_metrics.json` and `bach_external_summary.csv` contain the results; `bach_external_predictions.csv` retains original classes and individual predictions. These are research-only external dataset results, not clinical validation.

## Limitations and next work

- This is a small exploratory baseline with one random seed and no patient-level confidence intervals. BACH fold-model variability is descriptive only because all saved models were evaluated on the same 400 images.
- It uses one dataset and one image magnification at a time; results do not establish performance on other hospitals, scanners, staining conditions, or patient populations.
- Do not tune thresholds or model settings using these test results. Further model selection should use training/validation data, followed by an independent external test set whose license permits the intended processing.
- Do not integrate this model into a patient-facing diagnostic workflow. Any future demo should be explicitly labeled research-only and prevent clinical interpretation.

## BreaKHis citation

Spanhol, F. A., Oliveira, L. S., Petitjean, C., and Heutte, L. “A Dataset for Breast Cancer Histopathological Image Classification.” IEEE Transactions on Biomedical Engineering, 2016. DOI: 10.1109/TBME.2015.2496264.

Aresta, G. et al. “BACH: Grand challenge on breast cancer histology images.” Medical Image Analysis, 56 (2019), 122–139. DOI: 10.1016/j.media.2019.05.010.
