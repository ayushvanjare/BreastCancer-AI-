import csv, gzip, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
RAW = BASE / "raw"
DERIVED = BASE / "derived"
RAW.mkdir(parents=True, exist_ok=True)
DERIVED.mkdir(parents=True, exist_ok=True)
API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
GENES = ("BRCA1", "BRCA2")
LABELS = ("Pathogenic", "Likely pathogenic", "Benign", "Likely benign")
REVIEW = "criteria provided, multiple submitters, no conflicts"


def get_json(endpoint, params):
    request = Request(API + endpoint + "?" + urlencode(params), headers={"User-Agent": "BreastCareAI academic research dataset fetcher"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def clean(value):
    return " ".join(str(value or "").replace("\t", " ").replace("\n", " ").split())

ids = set()
query_counts = {}
for gene in GENES:
    for label in LABELS:
        query = f'{gene}[gene] AND "{label}"[clinsig] AND "{REVIEW}"[Review Status]'
        result = get_json("esearch.fcgi", {"db": "clinvar", "term": query, "retmax": 100000, "retmode": "json"})["esearchresult"]
        query_counts[f"{gene}:{label}"] = int(result["count"])
        ids.update(result.get("idlist", []))
        time.sleep(0.36)

records = {}
all_ids = sorted(ids)
for offset in range(0, len(all_ids), 200):
    batch = all_ids[offset:offset + 200]
    result = get_json("esummary.fcgi", {"db": "clinvar", "id": ",".join(batch), "retmode": "json"})["result"]
    for uid in result.get("uids", []):
        records[uid] = result[uid]
    print(f"Fetched {min(offset + len(batch), len(all_ids))}/{len(all_ids)} ClinVar summaries", flush=True)
    time.sleep(0.36)

# Preserve the returned NCBI summaries for traceability, compressed.
raw_path = RAW / "clinvar_brca1_brca2_multisubmit_no_conflict.jsonl.gz"
with gzip.open(raw_path, "wt", encoding="utf-8") as stream:
    for uid in sorted(records, key=lambda x: int(x)):
        stream.write(json.dumps(records[uid], ensure_ascii=False, separators=(",", ":")) + "\n")

rows = []
for uid, record in records.items():
    genes = {item.get("symbol", "") for item in record.get("genes", [])}
    gene = record.get("gene_sort", "")
    classification = record.get("germline_classification", {}) or {}
    label = classification.get("description", "")
    review = classification.get("review_status", "")
    if gene not in GENES and not (genes & set(GENES)):
        continue
    if label not in LABELS or REVIEW.lower() not in review.lower():
        continue
    traits = [item.get("trait_name", "") for item in classification.get("trait_set", [])]
    breast_traits = [x for x in traits if re.search(r"breast|ovarian", x, re.I)]
    if not breast_traits:
        continue
    gene = gene if gene in GENES else sorted(genes & set(GENES))[0]
    locations = [loc for variation in record.get("variation_set", []) for loc in variation.get("variation_loc", []) if loc.get("assembly_name") == "GRCh38" and loc.get("status") == "current"]
    loc = locations[0] if locations else {}
    rows.append({
        "clinvar_accession": record.get("accession_version") or record.get("accession", ""),
        "gene": gene,
        "variant": record.get("title", ""),
        "germline_classification": label,
        "review_status": review,
        "last_evaluated": classification.get("last_evaluated", ""),
        "breast_or_ovarian_conditions": " | ".join(sorted(set(breast_traits))),
        "GRCh38_chromosome": loc.get("chr", ""),
        "GRCh38_start": loc.get("start", ""),
        "GRCh38_stop": loc.get("stop", ""),
        "molecular_consequences": " | ".join(record.get("molecular_consequence_list", [])),
        "protein_change": record.get("protein_change", ""),
        "source_url": "https://www.ncbi.nlm.nih.gov/clinvar/variation/" + str(record.get("uid", uid)),
    })

rows.sort(key=lambda row: (row["gene"], row["germline_classification"], row["clinvar_accession"]))
fields = list(rows[0]) if rows else ["clinvar_accession", "gene", "variant", "germline_classification", "review_status", "last_evaluated", "breast_or_ovarian_conditions", "GRCh38_chromosome", "GRCh38_start", "GRCh38_stop", "molecular_consequences", "protein_change", "source_url"]
with (DERIVED / "clinvar_brca1_brca2_breast_ovarian_variant_labels.tsv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)

metadata = {
    "downloaded_utc": datetime.now(timezone.utc).isoformat(),
    "source": "NCBI ClinVar via E-utilities esearch/esummary",
    "query_genes": list(GENES),
    "requested_classifications": list(LABELS),
    "review_status_filter": REVIEW,
    "counts_by_query": query_counts,
    "unique_records_retrieved": len(records),
    "records_exported_after_gene_classification_review_status_and_breast_ovarian_condition_filters": len(rows),
    "data_level": "variant-level aggregate interpretations; no patient-level genotype or carrier labels",
    "intended_use": "research and dataset exploration only; not a clinical prediction model or clinical validation",
    "source_docs": ["https://www.ncbi.nlm.nih.gov/clinvar/docs/downloads/", "https://www.ncbi.nlm.nih.gov/clinvar/docs/ftp_primer/"],
}
(DERIVED / "clinvar_brca_subset_provenance.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"raw_file": str(raw_path), "records_retrieved": len(records), "records_exported": len(rows), "counts": query_counts}, indent=2))

