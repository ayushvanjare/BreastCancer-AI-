# Dataset selection for the next research model

## Recommended first: mammography lesion classification

Use **CBIS-DDSM** for a bounded mammography research experiment. TCIA lists 6,671 subjects, 10,239 mammography images, and mass/calcification training and test description tables with classification labels. The image download is large (about 163.51 GB), so start by downloading the description tables and the smallest supported image subset rather than the entire collection. Keep patient IDs grouped: all images from one patient must remain in only one split. Cite the dataset DOI and follow the TCIA data usage terms. [Official TCIA collection page](https://www.cancerimagingarchive.net/collection/cbis-ddsm/)

Suggested first endpoint: **mass lesion benign-versus-malignant classification**, using only labels provided by the official mass tables. Report patient-level split method, class counts, sensitivity, specificity, precision, and confidence intervals. Do not call the output a screening test or diagnosis. Keep calcification as a separate task because it has a different cohort/table.

## MRI option

**Duke-Breast-Cancer-MRI** contains 922 biopsy-confirmed invasive breast cancer cases, DCE-MRI, lesion annotations, and clinical/pathology data. It is a large download (about 368 GB), retrospective, and from one institution; it is therefore better suited to a later annotation/segmentation or defined pathology-feature task than an immediate general diagnostic model. Its listed license is CC BY-NC 4.0. [Official TCIA collection page](https://www.cancerimagingarchive.net/collection/duke-breast-cancer-mri/)

## CT option

Do not start a CT cancer predictor from the currently identified set. **CMB-BRCA** contains several imaging modalities including CT, MR, and mammography, but its current public summary has a small radiology cohort relative to the image size and most clinical/genomic data are hosted separately. First inspect the downloadable manifest and labels, then define a cohort and endpoint. It is not a defensible stand-alone CT classification dataset just because CT files exist. [Official TCIA collection page](https://www.cancerimagingarchive.net/collection/cmb-brca/)

## BRCA genetics option

**METABRIC** in cBioPortal includes targeted sequencing of 2,509 primary breast tumors and mutation data for many samples. That is somatic tumor-genomics data, not necessarily a clinically curated germline BRCA carrier label. It can support a carefully defined exploratory tumor-genomics task after confirming the data dictionary, permissions, label source, and leakage risks; it should not be described as hereditary-risk prediction. [cBioPortal study page](https://www.cbioportal.org/study?id=brca_metabric)

## Before training

1. Download only data you are authorized to use and retain the dataset citation/license with your report.
2. Keep the source dataset unchanged; create a separate derived-work folder.
3. Audit labels, class counts, missingness, image formats, patient identifiers, and duplicates.
4. Split by patient, not by image, to prevent nearly identical images from the same person leaking across train/test.
5. Choose one modality and one endpoint first. Do not combine BreaKHis pathology images with radiology images or genetic data as if they were interchangeable.
6. Freeze the test split before model selection. Report limitations and do not make clinical claims.

**Current recommendation:** begin with CBIS-DDSM mammography mass classification, provided the user can obtain the official data and the intended use complies with its license. The model remains research-only. Independent clinical validation cannot be supplied by this software project alone.
