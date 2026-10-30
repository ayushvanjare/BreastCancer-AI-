# Dataset cleanup log

Last reviewed: 2026-10-29

## Removed

- One extra DICOM copy in the CBIS-DDSM pilot after SHA-256 confirmed it was identical to the copy kept in the pilot folder.
- An empty CBIS staging folder.
- Generated root Python bytecode cache and backend pytest cache; these are automatically recreated and are not source data.
- During TCGA organization, 549 exact duplicate MAF files were removed only after MD5 comparison with their retained copies. The final raw folder contains one verified copy of each of 992 source files.
- Empty nested staging folders left by the download were removed after their contents were consolidated.

## Reviewed and retained

- CBIS-DDSM images, labels, manifest and pilot metadata: source material for the paused mammography track.
- ClinVar and GDC source data, labels, query manifests and scripts: required to trace or reproduce the two BRCA tracks.
- Model checkpoints and BACH evaluation outputs: existing project results.
- Application database and encryption key, configuration files, and installed Python/Node dependencies: needed for the app or its runtime. Removing them could break local operation or stored application data.
- Submission archives: distinct historical deliverables; no identical archive was found by checksum.
- TCIA retrieval utilities outside the dataset folder: software tools, not dataset contents, retained for a future user-authorized download.

## Current limitations

The CT and MRI folders are intentionally empty pending TCIA policy acceptance. Germline ClinVar data is variant-level, not patient-level. TCGA data is somatic tumor data. No new clinical validation evidence or patient-level hereditary-risk cohort was downloaded.
