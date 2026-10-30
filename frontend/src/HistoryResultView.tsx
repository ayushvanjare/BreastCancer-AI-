import type { ReactNode } from "react";

type Data = Record<string, unknown>;

function isData(value: unknown): value is Data {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function labelFor(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function readable(value: unknown): ReactNode {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 5 });
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map((item) => typeof item === "object" ? readable(item) : String(item)).join(" · ");
  if (isData(value)) return <dl className="history-nested-data">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{labelFor(key)}</dt><dd>{readable(item)}</dd></div>)}</dl>;
  return String(value);
}

function numberCell(value: unknown): ReactNode {
  if (typeof value !== "number") return "—";
  return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 5 });
}

export function HistoryResultView({ result }: { result: Data }) {
  const kind = typeof result.analysis_type === "string" ? result.analysis_type : "saved_analysis";
  const title = kind.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const columns = Array.isArray(result.columns) ? result.columns.filter(isData) : [];
  const stats = isData(result.descriptive_statistics) ? result.descriptive_statistics : {};
  const chartData = isData(result.chart_data) ? result.chart_data : {};
  const numericCharts = Array.isArray(chartData.numeric) ? chartData.numeric.filter(isData) : [];
  const categoryCharts = Array.isArray(chartData.categorical) ? chartData.categorical.filter(isData) : [];
  const hiddenKeys = new Set(["analysis_type", "history_id", "text", "columns", "descriptive_statistics", "chart_data", "metadata"]);
  const summary = Object.entries(result).filter(([key, value]) => !hiddenKeys.has(key) && (typeof value !== "object" || value === null));

  return <section className="history-result-view" aria-label="Saved analysis result">
    <div className="history-result-title"><div><div className="eyebrow">SAVED RESULT</div><h4>{title}</h4></div><span className="badge badge-neutral">Readable summary</span></div>
    {summary.length > 0 && <dl className="history-summary-grid">{summary.map(([key, value]) => <div key={key}><dt>{labelFor(key)}</dt><dd>{key === "size_bytes" && typeof value === "number" ? `${(value / 1024 / 1024).toFixed(2)} MB` : readable(value)}</dd></div>)}</dl>}
    {columns.length > 0 && <div className="history-result-section"><h5>Columns in this file</h5><div className="table-scroll"><table><thead><tr><th>Column</th><th>Type</th><th>Missing values</th><th>Missing</th></tr></thead><tbody>{columns.map((column, index) => <tr key={`${String(column.name)}-${index}`}><td><strong>{readable(column.name)}</strong></td><td>{readable(column.dtype)}</td><td>{readable(column.missing)}</td><td>{typeof column.missing_percent === "number" ? `${column.missing_percent}%` : "—"}</td></tr>)}</tbody></table></div></div>}
    {Object.keys(stats).length > 0 && <div className="history-result-section"><h5>Numeric summaries</h5><div className="table-scroll"><table><thead><tr><th>Column</th><th>Count</th><th>Mean</th><th>Std. dev.</th><th>Minimum</th><th>Median</th><th>Maximum</th></tr></thead><tbody>{Object.entries(stats).map(([column, raw]) => { const row = isData(raw) ? raw : {}; return <tr key={column}><td><strong>{column}</strong></td><td>{numberCell(row.count)}</td><td>{numberCell(row.mean)}</td><td>{numberCell(row.std)}</td><td>{numberCell(row.min)}</td><td>{numberCell(row.median)}</td><td>{numberCell(row.max)}</td></tr>; })}</tbody></table></div></div>}
    {numericCharts.length > 0 && Object.keys(stats).length === 0 && <div className="history-result-section"><h5>Numeric summaries</h5><div className="table-scroll"><table><thead><tr><th>Column</th><th>Count</th><th>Mean</th><th>Minimum</th><th>Median</th><th>Maximum</th></tr></thead><tbody>{numericCharts.map((row, index) => <tr key={`${String(row.column)}-${index}`}><td><strong>{readable(row.column)}</strong></td><td>{numberCell(row.count)}</td><td>{numberCell(row.mean)}</td><td>{numberCell(row.min)}</td><td>{numberCell(row.median)}</td><td>{numberCell(row.max)}</td></tr>)}</tbody></table></div></div>}
    {categoryCharts.length > 0 && <div className="history-result-section"><h5>Category counts</h5><div className="history-category-grid">{categoryCharts.map((group, index) => <div className="history-category-card" key={`${String(group.column)}-${index}`}><strong>{readable(group.column)}</strong>{Array.isArray(group.counts) ? group.counts.filter(isData).map((entry, countIndex) => <div key={`${String(entry.label)}-${countIndex}`}><span>{readable(entry.label)}</span><b>{readable(entry.count)}</b></div>) : <p className="muted">No category counts were saved.</p>}</div>)}</div></div>}
    {isData(result.class_scores) && <div className="history-result-section"><h5>Model scores</h5><dl className="history-summary-grid">{Object.entries(result.class_scores).map(([key, value]) => <div key={key}><dt>{labelFor(key)}</dt><dd>{readable(value)}</dd></div>)}</dl></div>}
    {isData(result.shape) && <div className="history-result-section"><h5>File shape</h5>{readable(result.shape)}</div>}
    {isData(result.metadata) && <div className="history-result-section"><h5>Input metadata</h5>{readable(result.metadata)}</div>}
    {typeof result.text === "string" && <div className="history-result-section"><h5>Extracted text</h5><pre className="history-readable-text">{result.text || "No text was detected in this file."}</pre></div>}
    {categoryCharts.length === 0 && numericCharts.length === 0 && Object.keys(stats).length === 0 && !isData(result.metadata) && summary.length === 0 && <p className="muted">This saved record has no additional summary fields.</p>}
    <p className="history-result-note">Research output for review only. This display does not provide a diagnosis or clinical recommendation.</p>
  </section>;
}
