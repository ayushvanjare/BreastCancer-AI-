# Model artifacts

This local project copy includes 25 existing BreaKHis research checkpoints:

- 20 ResNet-18 checkpoints: five cross-validation folds at 40X, 100X, 200X, and 400X. All loaded strictly into the inference worker's expected model architecture; a generated-image smoke test passed using the existing CPU-only Anaconda environment.
- Five 40X scratch-CNN baseline checkpoints. They are selectable in the research-only Histopathology workflow; Grad-CAM is available for ResNet-18 only.

`checkpoint_manifest.json` records paths relative to `model_artifacts/breakhis`, sizes, and SHA-256 hashes. `model_manifest.json` records task and availability limits. The source copies remain in the user's BreaKHis results folder. The API advertises each selectable file through `GET /api/modules`; submit its `id` as `checkpoint_id` to the histopathology endpoint.

The current local `backend/.env` uses the existing Anaconda CPU-only environment and one included checkpoint as a fallback. A generated-image smoke test through the API worker passed on CPU, and all 20 ResNet-18 state dictionaries loaded strictly into the expected architecture. The Histopathology page can select all 20 ResNet-18 and five scratch-CNN checkpoints. The existing CUDA Python environment still cannot load `c10.dll` because Windows Application Control blocks it; no PyTorch installation was changed. For another machine, set `RESEARCH_MODEL_PYTHON` to an already-working Python environment with compatible PyTorch, torchvision, and Pillow. `HISTOPATHOLOGY_CHECKPOINT` is optional when using the included checkpoint selector.

These files are not clinically validated; BACH external results showed weak transfer and low non-carcinoma specificity. Do not use the outputs for patient care. Do not choose a checkpoint based on official test-set results.

The BreaKHis source page identifies the dataset under CC BY 4.0: https://web.inf.ufpr.br/vri/databases/breast-cancer-histopathological-database-breakhis/. TorchVision warns that model weights may have terms derived from their training data and places permission checks on the user: https://github.com/pytorch/vision. Therefore this local copy is not cleared for redistribution in a submission ZIP until the applicable BreaKHis and ImageNet-derived weight terms are reviewed. No CT, MRI, mammography/X-ray, or patient-level BRCA prediction checkpoints are present.

## BRCA variant annotation research artifact

A separate scikit-learn model is saved at `brca_variant_annotation/clinvar_brca_variant_classifier.joblib`. It classifies ClinVar BRCA1/BRCA2 variant annotations as pathogenic/likely pathogenic or benign/likely benign. The grouped holdout report is in `../research_results/brca_variant_annotation/MODEL_CARD.md`. It is not registered as a patient-level BRCA predictor and is not exposed by the app. The ClinVar-only holdout is not clinical validation.

