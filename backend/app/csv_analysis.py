import csv
import io
import math

import pandas as pd


def analyze_csv(content: bytes) -> dict:
    """Parse a bounded CSV payload and return JSON-safe descriptive summaries."""
    frame = None
    errors = []
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = content.decode(encoding)
            delimiter = _detect_delimiter(text)
            _validate_row_widths(text, delimiter)
            frame = pd.read_csv(io.StringIO(text), sep=delimiter,
                                engine="python", on_bad_lines="error")
            break
        except UnicodeDecodeError as exc:
            errors.append(exc)
        except csv.Error as exc:
            raise ValueError(f"Could not parse CSV quoting or row structure: {exc}") from exc
        except pd.errors.EmptyDataError:
            raise ValueError("The CSV file is empty or has no header row.")
        except pd.errors.ParserError as exc:
            raise ValueError(f"Could not parse CSV structure: {exc}") from exc
    if frame is None:
        raise ValueError("Could not decode this CSV file using common text encodings.") from errors[-1]
    if frame.empty and len(frame.columns) == 0:
        raise ValueError("The CSV file has no columns.")
    if len(frame.columns) == 0:
        raise ValueError("The CSV file has no columns.")

    columns = [str(c) for c in frame.columns]
    missing = frame.isna().sum()
    numeric = frame.select_dtypes(include="number")
    stats = {}
    for column in numeric.columns:
        values = numeric[column].dropna()
        stats[str(column)] = {
            "count": int(values.count()),
            "mean": _number(values.mean()), "std": _number(values.std()),
            "min": _number(values.min()), "q25": _number(values.quantile(.25)),
            "median": _number(values.median()), "q75": _number(values.quantile(.75)),
            "max": _number(values.max()),
        }
    chart_data = {
        "numeric": [{"column": col, **values} for col, values in stats.items()],
        "categorical": [],
    }
    for column in frame.columns:
        if column in numeric.columns:
            continue
        counts = frame[column].fillna("(missing)").astype(str).value_counts().head(20)
        chart_data["categorical"].append({
            "column": str(column),
            "counts": [{"label": str(label), "count": int(count)} for label, count in counts.items()],
        })
    return {
        "shape": {"rows": int(frame.shape[0]), "columns": int(frame.shape[1])},
        "columns": [{"name": str(col), "dtype": str(frame[col].dtype),
                     "missing": int(missing[col]),
                     "missing_percent": round(float(missing[col] / max(len(frame), 1) * 100), 2)}
                    for col in frame.columns],
        "descriptive_statistics": stats,
        "chart_data": chart_data,
    }


def _detect_delimiter(text: str) -> str:
    sample = text[:65536]
    candidates = []
    for delimiter in ",;\t|":
        try:
            reader = csv.reader(io.StringIO(sample, newline=""), delimiter=delimiter, strict=True)
            header = next((row for row in reader if row and not (len(row) == 1 and not row[0].strip())), None)
        except csv.Error:
            continue
        if header is not None:
            candidates.append((len(header), delimiter))
    if not candidates:
        return ","
    widest_header = max(width for width, _delimiter in candidates)
    widest_candidates = [delimiter for width, delimiter in candidates if width == widest_header]
    if len(widest_candidates) == 1:
        return widest_candidates[0]

    # Resolve genuinely ambiguous headers using Sniffer, constrained to candidates
    # that actually split the header into its maximum number of fields.
    try:
        guessed = csv.Sniffer().sniff(sample, delimiters="".join(widest_candidates)).delimiter
        if guessed in widest_candidates:
            return guessed
    except csv.Error:
        pass
    # A single-column file has no evidence for a delimiter; comma is conventional.
    return "," if widest_header == 1 else widest_candidates[0]


def _validate_row_widths(text: str, delimiter: str) -> None:
    """Reject rows wider than the header instead of silently shifting columns."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    expected_width = None
    for row in reader:
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        if expected_width is None:
            expected_width = len(row)
            if expected_width == 0:
                raise ValueError("The CSV file has no header columns.")
            continue
        if len(row) > expected_width:
            raise ValueError(
                f"Malformed CSV row near line {reader.line_num}: found {len(row)} fields, "
                f"but the header has {expected_width}. Check for an extra delimiter."
            )


def _number(value):
    if pd.isna(value) or not math.isfinite(float(value)):
        return None
    return float(value)
