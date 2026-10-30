import hashlib, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "raw"
META = BASE / "metadata"
RAW.mkdir(parents=True, exist_ok=True)
META.mkdir(parents=True, exist_ok=True)
API = "https://api.gdc.cancer.gov"
FILTERS = {"op": "and", "content": [
    {"op": "in", "content": {"field": "cases.project.project_id", "value": ["TCGA-BRCA"]}},
    {"op": "=", "content": {"field": "data_format", "value": "MAF"}},
    {"op": "=", "content": {"field": "access", "value": "open"}},
]}
FIELDS = "file_id,file_name,file_size,md5sum,data_type,data_category,access,analysis.workflow_type,cases.case_id,cases.submitter_id"
HEADERS = {"User-Agent": "BreastCareAI academic research dataset fetcher"}

request = Request(API + "/files", data=json.dumps({"filters": FILTERS, "fields": FIELDS, "format": "JSON", "size": 10000}).encode(), headers={**HEADERS, "Content-Type": "application/json"}, method="POST")
with urlopen(request, timeout=60) as response:
    catalog = json.load(response)
hits = catalog["data"]["hits"]
total = catalog["data"]["pagination"]["total"]
if total != len(hits) or not hits:
    raise RuntimeError(f"Incomplete GDC catalog response: total={total}, returned={len(hits)}")
for item in hits:
    if item.get("access") != "open" or item.get("data_type") != "Masked Somatic Mutation" or not item.get("file_name", "").lower().endswith(".maf.gz"):
        raise RuntimeError("Unexpected file in GDC result; refusing bulk download")

manifest = {
    "retrieved_utc": datetime.now(timezone.utc).isoformat(),
    "source": "NCI Genomic Data Commons API",
    "project": "TCGA-BRCA",
    "filter": FILTERS,
    "fields": FIELDS,
    "total_files": total,
    "total_bytes": sum(int(item.get("file_size", 0)) for item in hits),
    "access": "open",
    "data_type": "Masked Somatic Mutation",
    "workflow": "Aliquot Ensemble Somatic Variant Merging and Masking",
    "files": hits,
}
manifest_path = META / "gdc_tcga_brca_somatic_maf_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def download(item):
    target = RAW / item["file_name"]
    if target.exists():
        digest = hashlib.md5()
        with target.open("rb") as existing:
            for chunk in iter(lambda: existing.read(1024 * 1024), b""):
                digest.update(chunk)
        if target.stat().st_size == int(item["file_size"]) and digest.hexdigest().lower() == item["md5sum"].lower():
            return target.name, target.stat().st_size
        target.unlink()
    tmp = target.with_suffix(target.suffix + ".part")
    for attempt in range(3):
        try:
            request = Request(API + "/data/" + item["file_id"], headers=HEADERS)
            digest = hashlib.md5()
            size = 0
            with urlopen(request, timeout=120) as response, tmp.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            if size != int(item["file_size"]):
                raise RuntimeError(f"size mismatch for {item['file_name']}: {size} != {item['file_size']}")
            if digest.hexdigest().lower() != item["md5sum"].lower():
                raise RuntimeError(f"MD5 mismatch for {item['file_name']}")
            os.replace(tmp, target)
            return target.name, size
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            if attempt == 2:
                raise RuntimeError(f"Failed {item['file_name']}: {exc}") from exc
            time.sleep(2 ** attempt)

failures = []
completed = 0
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = {executor.submit(download, item): item for item in hits}
    for future in as_completed(futures):
        try:
            future.result()
            completed += 1
            if completed % 100 == 0 or completed == total:
                print(f"Downloaded and verified {completed}/{total} GDC files", flush=True)
        except Exception as exc:
            failures.append(str(exc))
            print(str(exc), file=sys.stderr, flush=True)

if failures:
    raise RuntimeError(f"{len(failures)} GDC downloads failed; see messages above")
print(json.dumps({"files_verified": completed, "bytes": manifest["total_bytes"], "manifest": str(manifest_path), "data_folder": str(RAW)}, indent=2))



