import type { ResearchModule } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401 && localStorage.getItem("breastcare_access_token")) {
    localStorage.removeItem("breastcare_access_token");
    window.location.assign("/login?session_expired=1");
  }
  return response;
}
function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("breastcare_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getHealth() {
  const response = await apiFetch(`${API_BASE}/api/health`);
  if (!response.ok) throw new Error("Backend health check failed");
  return response.json() as Promise<{ status: string; app: string; phase: string | number }>;
}

export async function getModules() {
  const response = await apiFetch(`${API_BASE}/api/modules`);
  if (!response.ok) throw new Error("Could not load modules");
  const data = await response.json();
  return data.modules as ResearchModule[];
}

export async function analyzeCsv(file: File): Promise<CsvAnalysisResult> {
  const body = new FormData();
  body.append("file", file);
  const response = await apiFetch(`${API_BASE}/api/csv/analyze`, { method: "POST", headers: authHeaders(), body });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "CSV analysis failed.");
  return data as CsvAnalysisResult;
}

export async function extractReport(file: File): Promise<ReportExtractionResult> {
  const body = new FormData();
  body.append("file", file);
  const response = await apiFetch(`${API_BASE}/api/reports/extract`, { method: "POST", headers: authHeaders(), body });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Text extraction failed.");
  return data as ReportExtractionResult;
}

export async function predictHistopathology(file: File, includeGradCam: boolean, checkpointId: string): Promise<HistopathologyResult> {
  const body = new FormData();
  body.append("file", file);
  body.append("explain", String(includeGradCam));
  body.append("checkpoint_id", checkpointId);
  const response = await apiFetch(`${API_BASE}/api/research/histopathology/predict`, { method: "POST", headers: authHeaders(), body });
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message ?? "Research model could not process this image.");
  }
  return data as HistopathologyResult;
}

export interface HistopathologyResult {
  filename: string;
  size_bytes: number;
  analysis_type: "research_only_model_output";
  research_only: true;
  predicted_class: "benign" | "malignant";
  class_scores: { benign: number; malignant: number };
  score_note: string;
  model: string;
  training_fold: string;
  training_magnification: string;
  image_size: number;
  execution_device: string;
  clinical_use: false;
  history_id?: number;
  explanation?: string;
  grad_cam_overlay_png_base64?: string;
}

export async function inspectImaging(moduleId: "ct" | "mri" | "xray", file: File): Promise<ImagingInspectionResult> {
  const body = new FormData();
  body.append("module_id", moduleId);
  body.append("file", file);
  const response = await apiFetch(`${API_BASE}/api/imaging/inspect`, { method: "POST", headers: authHeaders(), body });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "The image could not be inspected.");
  return data as ImagingInspectionResult;
}

export async function inspectDicomSeries(moduleId: "ct" | "mri" | "xray", files: File[]): Promise<ImagingInspectionResult> {
  const body = new FormData();
  body.append("module_id", moduleId);
  files.forEach((file) => body.append("files", file));
  const response = await apiFetch(`${API_BASE}/api/imaging/series/inspect`, { method: "POST", headers: authHeaders(), body });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "The DICOM series could not be inspected.");
  return data as ImagingInspectionResult;
}

export async function preflightBrcaCohort(file: File): Promise<Record<string, unknown>> {
  const body = new FormData();
  body.append("file", file);
  const response = await apiFetch(`${API_BASE}/api/research/brca/preflight`, { method: "POST", headers: authHeaders(), body });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "BRCA cohort preflight failed.");
  return data as Record<string, unknown>;
}

export interface ImagingInspectionResult {
  history_id?: number;
  size_bytes: number;
  inspection_type: "raster_image_metadata" | "dicom_header_metadata" | "dicom_series_header_metadata" | "nifti_header_metadata";
  module_id: "ct" | "mri" | "xray";
  modality_check: "not_verifiable_from_raster_image" | "not_verifiable_from_nifti_header" | "matches_selected_module";
  metadata: {
    format?: string;
    width?: number;
    height?: number;
    mode?: string;
    modality?: string;
    rows?: number | null;
    columns?: number | null;
    frames?: number | null;
    samples_per_pixel?: number | null;
    pixel_spacing_mm?: number[] | null;
    slice_thickness_mm?: number[] | null;
    dimensions?: number[];
    voxel_spacing?: number[];
    data_type?: string;
    instances?: number;
    position_headers_available?: number;
    orientation_consistent?: boolean;
    duplicate_slice_positions?: boolean;
  };
  patient_identifiers_returned: false;
  model_inference_performed: false;
  note?: string;
}

export interface ReportExtractionResult {
  history_id?: number;
  filename: string;
  size_bytes: number;
  extraction_type: string;
  character_count: number;
  method: "ocr" | "embedded_text";
  pages: number;
  text: string;
}

export interface CsvAnalysisResult {
  history_id?: number;
  filename: string;
  size_bytes: number;
  analysis_type: string;
  shape: { rows: number; columns: number };
  columns: { name: string; dtype: string; missing: number; missing_percent: number }[];
  descriptive_statistics: Record<string, Record<string, number | null>>;
  chart_data: {
    numeric: { column: string; count: number; mean: number | null; std: number | null; min: number | null; q25: number | null; median: number | null; q75: number | null; max: number | null }[];
    categorical: { column: string; counts: { label: string; count: number }[] }[];
  };
}

export interface AnalysisHistoryItem {
  id: number;
  analysis_type: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string | null;
}

export async function getAnalysisHistory(): Promise<AnalysisHistoryItem[]> {
  const response = await apiFetch(`${API_BASE}/api/history`, { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Sign in to view saved analyses.");
  return data.items as AnalysisHistoryItem[];
}

export async function getAnalysisHistoryDetail(id: number): Promise<{ result: Record<string, unknown> }> {
  const response = await apiFetch(`${API_BASE}/api/history/${id}`, { headers: authHeaders() });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not load this saved analysis.");
  return data as { result: Record<string, unknown> };
}

export async function deleteAnalysisHistory(id: number): Promise<void> {
  const response = await apiFetch(`${API_BASE}/api/history/${id}`, { method: "DELETE", headers: authHeaders() });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(typeof data.detail === "string" ? data.detail : "Could not delete this saved analysis.");
  }
}

export async function downloadAnalysisFile(id: number): Promise<Blob> {
  const response = await apiFetch(`${API_BASE}/api/history/${id}/file`, { headers: authHeaders() });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(typeof data.detail === "string" ? data.detail : "Could not download this saved file.");
  }
  return response.blob();
}
