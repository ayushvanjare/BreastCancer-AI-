import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Activity, ArrowDownRight, ArrowRight, BrainCircuit, CheckCircle2,
  CircleHelp, ClipboardList, CloudDownload, Database, FileText, FlaskConical,
  Download, HeartPulse, Image as ImageIcon, LayoutDashboard, LockKeyhole, Menu,
  Microscope, Scan, Search, Settings, ShieldCheck, Table2, Upload, UserRound, X, Zap,
  Trash2, LogOut,
} from "lucide-react";
import { API_BASE, analyzeCsv, deleteAnalysisHistory, downloadAnalysisFile, extractReport, getAnalysisHistory, getAnalysisHistoryDetail, getHealth, getModules, inspectDicomSeries, inspectImaging, predictHistopathology, preflightBrcaCohort, type AnalysisHistoryItem, type CsvAnalysisResult, type HistopathologyResult, type ImagingInspectionResult, type ReportExtractionResult } from "./api";
import { HistoryResultView } from "./HistoryResultView";
import type { ResearchModule } from "./types";

const iconMap: Record<string, typeof Microscope> = {
  Microscope, Scan, Activity, Image: ImageIcon, FileText, Table2,
};

function useModules() {
  const [modules, setModules] = useState<ResearchModule[]>([]);
  useEffect(() => {
    getModules().then(setModules).catch(() => setModules([
      { id: "histopathology", title: "Histopathology", subtitle: "Tissue image analysis", description: "Optional BreaKHis ResNet-18 research model; not for diagnosis or clinical use.", icon: "Microscope", input_types: ["PNG", "JPG", "TIFF"], status: "interface_ready_model_missing", accent: "teal" },
      { id: "ct", title: "CT Scan", subtitle: "Computed tomography", description: "Single-image and DICOM-header review only. No CT prediction model is installed.", icon: "Scan", input_types: ["DICOM", "PNG", "TIFF"], status: "metadata_review_available_model_missing", accent: "blue" },
      { id: "mri", title: "MRI Analysis", subtitle: "Magnetic resonance imaging", description: "Single-image and DICOM-header review only. No MRI prediction model is installed.", icon: "Activity", input_types: ["DICOM", "PNG", "TIFF"], status: "metadata_review_available_model_missing", accent: "purple" },
      { id: "xray", title: "X-ray & Mammography", subtitle: "Radiology image analysis", description: "Single-image and DICOM-header review only. No radiology prediction model is installed.", icon: "Image", input_types: ["DICOM", "PNG", "JPG", "TIFF"], status: "metadata_review_available_model_missing", accent: "orange" },
      { id: "brca", title: "BRCA Genomics", subtitle: "Research cohort checks", description: "Preflight a de-identified BRCA cohort CSV. No variant interpretation or prediction is performed.", icon: "Activity", input_types: ["CSV (de-identified labels)"], status: "input_preflight_available_model_missing", accent: "purple" },
      { id: "reports", title: "Doctor Reports", subtitle: "Prescription and report extraction", description: "Extract text from reports for human review. No medical interpretation is performed.", icon: "FileText", input_types: ["PDF", "PNG", "JPG"], status: "interface_ready_text_extraction", accent: "green" },
      { id: "csv", title: "CSV Analysis", subtitle: "Tabular data exploration", description: "Explore structure, missing values, and descriptive statistics without medical prediction.", icon: "Table2", input_types: ["CSV"], status: "interface_ready_descriptive_analysis", accent: "teal" },
    ]));
  }, []);
  return modules;
}

function Brand({ compact = false }: { compact?: boolean }) {
  return <Link to="/" className={`brand ${compact ? "brand-compact" : ""}`}>
    <span className="brand-mark"><HeartPulse size={22} strokeWidth={2.4} /></span>
    {!compact && <span className="brand-name">BreastCare <b>AI</b><small>RESEARCH SUITE</small></span>}
  </Link>;
}

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mobileNavigation, setMobileNavigation] = useState(() => window.matchMedia("(max-width: 900px)").matches);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [health, setHealth] = useState<"checking" | "online" | "offline">("checking");
  const sidebarRef = useRef<HTMLElement>(null);
  const modules = useModules();
  const location = useLocation();

  useEffect(() => {
    const media = window.matchMedia("(max-width: 900px)");
    const updateNavigationMode = () => setMobileNavigation(media.matches);
    media.addEventListener("change", updateNavigationMode);
    return () => media.removeEventListener("change", updateNavigationMode);
  }, []);

  useEffect(() => {
    if (sidebarRef.current) sidebarRef.current.inert = mobileNavigation && !sidebarOpen;
  }, [mobileNavigation, sidebarOpen]);

  useEffect(() => {
    getHealth().then(() => setHealth("online")).catch(() => setHealth("offline"));
  }, [location.pathname]);

  const filteredModules = modules.filter((m) => `${m.title} ${m.subtitle}`.toLowerCase().includes(query.toLowerCase()));

  return <div className="app-shell">
    {sidebarOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
    <aside ref={sidebarRef} id="primary-navigation" aria-label="Primary navigation" aria-hidden={mobileNavigation && !sidebarOpen} className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
      <div className="sidebar-brand"><Brand /><button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close menu"><X size={18} /></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav className="nav-list">
        <NavLink to="/" end onClick={() => setSidebarOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}><LayoutDashboard size={18} /> Dashboard</NavLink>
        <div className="nav-section-title">ANALYSIS MODULES</div>
        {modules.map((m) => {
          const Icon = iconMap[m.icon] ?? FlaskConical;
          return <NavLink key={m.id} to={`/modules/${m.id}`} onClick={() => setSidebarOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            <Icon size={18} /><span>{m.title}</span><span className="nav-dot" />
          </NavLink>;
        })}
        <div className="nav-section-title">RESEARCH</div>
        <NavLink to="/models" onClick={() => setSidebarOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}><BrainCircuit size={18} /> Model registry</NavLink>
        <NavLink to="/results" onClick={() => setSidebarOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}><FlaskConical size={18} /> Experiment results</NavLink>
        <NavLink to="/history" onClick={() => setSidebarOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}><ClipboardList size={18} /> Analysis history</NavLink>
      </nav>
      <div className="sidebar-spacer" />
      <div className="offline-card">
        <div className="offline-card-icon"><ShieldCheck size={17} /></div>
        <div><strong>Local research workspace</strong><p>Use only authorized, de-identified research data.</p><span className={`connection-state ${health}`}><i />{health === "online" ? "API connected" : health === "offline" ? "API disconnected" : "Checking API…"}</span></div>
      </div>
      <div className="sidebar-footer"><NavLink to="/settings" className="nav-link"><Settings size={18} /> Settings</NavLink><span>Research prototype · local workflows</span></div>
    </aside>

    <main className="main-shell">
      <header className="topbar">
<div className="topbar-left">
  <button
    className="icon-button menu-toggle"
    aria-label="Open navigation"
    aria-controls="primary-navigation"
    aria-expanded={sidebarOpen}
    onClick={() => setSidebarOpen(true)}
  >
    <Menu size={21} />
  </button>

  <div className="breadcrumb">
    <span>Workspace</span>
    <span className="crumb-sep">/</span>
    <b>
      {location.pathname === "/"
        ? "Dashboard"
        : location.pathname
            .split("/")
            .filter(Boolean)
            .pop()
            ?.replace(/-/g, " ")}
    </b>
  </div>
</div>        <div className="topbar-actions">
          {searchOpen && <input autoFocus className="top-search" aria-label="Search modules" placeholder="Search modules…" value={query} onChange={(e) => setQuery(e.target.value)} />}
          <button className="icon-button" aria-label={searchOpen ? "Close module search" : "Search modules"} aria-expanded={searchOpen} onClick={() => setSearchOpen(!searchOpen)}><Search size={19} /></button>
          <span className="topbar-divider" />
          <div className="local-pill"><span className={`status-dot ${health}`} /> Local environment</div>
          {localStorage.getItem("breastcare_access_token") && <button className="button button-secondary button-small" onClick={() => { localStorage.removeItem("breastcare_access_token"); window.location.href = "/login"; }}><LogOut size={15} /> Sign out</button>}
          <Link className="account-link" to="/login" aria-label="Open sign in or registration" title="Account: sign in or register"><UserRound size={16} /><span>Account</span></Link>
        </div>
      </header>
      <div className="page-wrap">
        <Routes>
          <Route path="/" element={<Dashboard modules={filteredModules} health={health} />} />
          <Route path="/modules/:moduleId" element={<ModulePage modules={modules} />} />
          <Route path="/models" element={<ModelsPage modules={modules} />} />
          <Route path="/results" element={<ExperimentResultsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/login" element={<AuthPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </div>
      <footer className="app-footer"><span>BreastCare AI <b>·</b> Research-only prototype</span><span><LockKeyhole size={13} /> Local-first by design</span></footer>
    </main>
  </div>;
}

function PageIntro({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-intro"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}


function Dashboard({ modules, health }: { modules: ResearchModule[]; health: string }) {
  const [activeTab, setActiveTab] = useState("All modules");
  const [quickSearch, setQuickSearch] = useState("");
  const shown = modules.filter((m) => (activeTab === "All modules" || (activeTab === "Imaging" ? ["histopathology", "ct", "mri", "xray"].includes(m.id) : ["reports", "csv", "brca"].includes(m.id))) && `${m.title} ${m.subtitle}`.toLowerCase().includes(quickSearch.toLowerCase()));
  const histopathModule = modules.find((module) => module.id === "histopathology");
  const histopathConfigured = histopathModule?.status === "research_model_paths_set_unverified";
  const histopathCheckpointCount = (histopathModule?.available_checkpoints ?? 0) + (histopathModule?.available_baselines ?? 0);
  return <div className="page-content">
    <PageIntro eyebrow="RESEARCH WORKSPACE" title="Good to see you." description="Your multimodal breast cancer research workspace is ready to configure." action={<button className="button button-secondary" onClick={() => window.location.href = "/models"}><BrainCircuit size={16} /> Model registry <ArrowRight size={15} /></button>} />
    <section className="hero-panel">
    <div className="hero-copy"><div className="hero-kicker"><span className="hero-kicker-dot" /> MULTIMODAL RESEARCH WORKSPACE</div><h2>Bring research data<br /><em>into one workspace.</em></h2><p>Explore seven workflows for descriptive data analysis, document text extraction, research image experiments, imaging input review, and BRCA research planning.</p><div className="hero-actions"><Link to="/modules/histopathology" className="button button-white"><Upload size={16} /> Open image analysis <ArrowRight size={15} /></Link><Link to="/modules/csv" className="hero-text-link">Explore data analysis <ArrowDownRight size={15} /></Link></div><div className="hero-proof"><span><CheckCircle2 size={14} /> Optional local PyTorch runtime</span><span><LockKeyhole size={14} /> Uploads are encrypted and account-scoped</span></div></div>
      <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" /><div className="hero-core"><HeartPulse size={42} /></div><div className="floating-chip chip-one"><Microscope size={17} /><span>Pathology</span></div><div className="floating-chip chip-two"><Database size={17} /><span>Research data</span></div><div className="floating-chip chip-three"><BrainCircuit size={17} /><span>AI models</span></div><div className="hero-art-caption">One platform. Modular workflows.</div></div>
    </section>
    <div className="stat-grid">
      <StatCard icon={<FlaskConical size={19} />} label="Analysis modules" value={String(modules.length).padStart(2, "0")} note="Separate research workflows" tone="teal" />
      <StatCard icon={<BrainCircuit size={19} />} label="Local checkpoints" value={String(histopathCheckpointCount)} note={histopathConfigured ? "Path set · runtime unverified" : histopathCheckpointCount ? "Included · not configured" : "None included"} tone="purple" />
      <StatCard icon={<Database size={19} />} label="Datasets connected" value="0" note="Configure authorized data" tone="blue" />
      <StatCard icon={<Zap size={19} />} label="Inference runtime" value={histopathConfigured ? "Unverified" : "Not set"} note={histopathConfigured ? "Runtime check happens only when run" : "No model worker configured"} tone="orange" />
    </div>
    <div className="section-heading"><div><div className="eyebrow">YOUR WORKSPACE</div><h2>Analysis modules</h2><p>Choose a workflow to see its supported inputs and setup status.</p></div><div className="section-tools"><div className="inline-search"><Search size={16} /><input aria-label="Find a module" value={quickSearch} onChange={(e) => setQuickSearch(e.target.value)} placeholder="Find a module" /></div></div></div>
    <div className="tabs" role="group" aria-label="Filter modules">{["All modules", "Imaging", "Documents & data"].map((tab) => <button key={tab} type="button" aria-pressed={activeTab === tab} className={`tab ${activeTab === tab ? "tab-active" : ""}`} onClick={() => setActiveTab(tab)}>{tab}</button>)}</div>
    <div className="module-grid">{shown.map((m) => <ModuleCard key={m.id} module={m} />)}</div>
    <div className="bottom-grid"><section className="surface-card readiness-card"><div className="card-title-row"><div><div className="eyebrow">ENVIRONMENT</div><h3>Local setup status</h3></div><span className={`badge ${health === "online" ? "badge-success" : "badge-neutral"}`}><span className="status-dot" />{health === "online" ? "Connected" : health === "offline" ? "API offline" : "Checking"}</span></div><div className="readiness-list"><ReadinessRow icon={<CheckCircle2 size={17} />} title="Frontend interface" detail="React application is running" done /><ReadinessRow icon={<CheckCircle2 size={17} />} title="Module navigation" detail={`${modules.length} workflows registered`} done /><ReadinessRow icon={<Database size={17} />} title="Database" detail="SQLite is created by the backend" done={health === "online"} /><ReadinessRow icon={<BrainCircuit size={17} />} title="Model runtime configuration" detail={histopathConfigured ? "Paths exist; runtime compatibility is unverified" : histopathCheckpointCount ? `${histopathCheckpointCount} checkpoints included; runtime paths are not set` : "No model checkpoints or runtime paths are set"} done={false} /></div></section><section className="surface-card research-note"><div className="note-icon"><ShieldCheck size={20} /></div><div className="eyebrow">RESPONSIBLE AI</div><h3>Research first. Clinical claims only after validation.</h3><p>The local BreaKHis model is a research baseline with weak transfer to BACH. Its output is not a diagnosis and must not guide patient care.</p><Link to="/models" className="text-link">Review model readiness <ArrowRight size={15} /></Link></section></div>
  </div>;
}


type ReadinessRowProps = {
  icon: React.ReactNode;
  title: string;
  detail: string;
  done?: boolean;
};

function ReadinessRow({
  icon,
  title,
  detail,
  done = false,
}: ReadinessRowProps) {
  return (
    <div className="readiness-row">
      <div className="readiness-icon">{icon}</div>

      <div className="readiness-content">
        <strong>{title}</strong>
        <span>{detail}</span>
      </div>

      <span className={`badge ${done ? "badge-success" : "badge-neutral"}`}>
        {done ? "Ready" : "Pending"}
      </span>
    </div>
  );
}


function StatCard({ icon, label, value, note, tone }: { icon: ReactNode; label: string; value: string; note: string; tone: string }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}>{icon}</div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></div>;
}
function ModuleCard({ module }: { module: ResearchModule }) {
  const Icon = iconMap[module.icon] ?? FlaskConical;
  const modelMissing = module.status === "interface_ready_model_missing";
  const researchCheckpointsPresent = module.status === "research_checkpoints_present_unverified";
  const researchModelPathsSet = module.status === "research_model_paths_set_unverified";
  const metadataReviewReady = module.status === "metadata_review_available_model_missing";
  const planningOnly = module.status === "readiness_plan_only";
  const preflightAvailable = module.status === "input_preflight_available_model_missing";
  const featureReady = module.status === "interface_ready_text_extraction" || module.status === "interface_ready_descriptive_analysis";
  const badge = preflightAvailable ? "Input checks · no model" : planningOnly ? "Planning only · no upload" : researchModelPathsSet ? "Checkpoint paths set · unverified" : researchCheckpointsPresent ? `${module.available_checkpoints ?? 0} checkpoints · unverified` : metadataReviewReady ? "Metadata review · no model" : module.status === "interface_ready_text_extraction" ? "Text extraction" : module.status === "interface_ready_descriptive_analysis" ? "Descriptive analysis" : modelMissing ? "Model needed" : "Pipeline planned";
  return <Link to={`/modules/${module.id}`} className="module-card"><div className="module-card-top"><div className={`module-icon ${module.accent}`}><Icon size={21} /></div><span className={`badge ${preflightAvailable ? "badge-success" : modelMissing || metadataReviewReady || researchModelPathsSet || researchCheckpointsPresent ? "badge-warning" : featureReady ? "badge-success" : "badge-neutral"}`}>{badge}</span></div><h3>{module.title}</h3><div className="module-subtitle">{module.subtitle}</div><p>{module.description}</p><div className="module-card-bottom"><span className="input-hint"><FileText size={14} /> {module.input_types.slice(0, 3).join(" · ")}</span><span className="card-arrow"><ArrowRight size={17} /></span></div></Link>;
}

function ModulePage({ modules }: { modules: ResearchModule[] }) {
  const { moduleId } = useParams();
  const module = modules.find((m) => m.id === moduleId);
  const Icon = iconMap[module?.icon ?? ""] ?? FlaskConical;
  const [file, setFile] = useState<File | null>(null);
  const [notice, setNotice] = useState("");
  const [csvResult, setCsvResult] = useState<CsvAnalysisResult | null>(null);
  const [csvBusy, setCsvBusy] = useState(false);
  const [reportResult, setReportResult] = useState<ReportExtractionResult | null>(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [histopathResult, setHistopathResult] = useState<HistopathologyResult | null>(null);
  const [histopathBusy, setHistopathBusy] = useState(false);
  const [includeGradCam, setIncludeGradCam] = useState(false);
  const [checkpointId, setCheckpointId] = useState("resnet18/fold1_40x");
  const [imagingResult, setImagingResult] = useState<ImagingInspectionResult | null>(null);
  const [imagingBusy, setImagingBusy] = useState(false);
  const [dicomFiles, setDicomFiles] = useState<File[]>([]);
  if (!module) return <NotFound />;
  const activeModule = module;
  function handleFile(selected: File | undefined) {
    setNotice("");
    if (!selected) return;
    setFile(selected);
    setCsvResult(null);
    setReportResult(null);
    setHistopathResult(null);
    setImagingResult(null);
    setDicomFiles([]);
    setNotice(activeModule.id === "csv" ? "CSV selected. Choose Analyze CSV to upload it for descriptive statistics." : activeModule.id === "reports" ? "Report selected. Choose Extract text to upload it for local text extraction." : activeModule.id === "histopathology" ? "Image selected. It remains local until you explicitly run the research model." : ["ct", "mri", "xray"].includes(activeModule.id) ? "Image selected. Choose Inspect input to send a single image/header for local metadata review only." : "File selected for preview only.");
  }
  async function runCsvAnalysis() {
    if (!file) { setNotice("Select a CSV file first."); return; }
    if (!localStorage.getItem("breastcare_access_token")) { setNotice("Sign in before submitting a file. Uploads and results are saved encrypted to your local account history."); return; }
    setCsvBusy(true); setNotice(""); setCsvResult(null);
    try { setCsvResult(await analyzeCsv(file)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "CSV analysis failed. Check the file and backend, then try again."); }
    finally { setCsvBusy(false); }
  }
  async function runReportExtraction() {
    if (!file) { setNotice("Select a report file first."); return; }
    if (!localStorage.getItem("breastcare_access_token")) { setNotice("Sign in before submitting a file. Uploads and results are saved encrypted to your local account history."); return; }
    setReportBusy(true); setNotice(""); setReportResult(null);
    try { setReportResult(await extractReport(file)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Text extraction failed. Check the file and backend, then try again."); }
    finally { setReportBusy(false); }
  }
  async function runHistopathology() {
    if (!file) { setNotice("Select an image first."); return; }
    if (!localStorage.getItem("breastcare_access_token")) { setNotice("Sign in before submitting a file. Uploads and results are saved encrypted to your local account history."); return; }
    setHistopathBusy(true); setNotice(""); setHistopathResult(null);
    try { setHistopathResult(await predictHistopathology(file, includeGradCam, checkpointId)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Research model failed. Check its local configuration and try again."); }
    finally { setHistopathBusy(false); }
  }
  async function runImagingReview() {
    if ((!file && !dicomFiles.length) || !["ct", "mri", "xray"].includes(activeModule.id)) { setNotice("Select an imaging file or DICOM series first."); return; }
    if (!localStorage.getItem("breastcare_access_token")) { setNotice("Sign in before submitting a file. Uploads and results are saved encrypted to your local account history."); return; }
    setImagingBusy(true); setNotice(""); setImagingResult(null);
    try { setImagingResult(dicomFiles.length ? await inspectDicomSeries(activeModule.id as "ct" | "mri" | "xray", dicomFiles) : await inspectImaging(activeModule.id as "ct" | "mri" | "xray", file!)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Image metadata review failed. Check the file and backend."); }
    finally { setImagingBusy(false); }
  }
  if (module.id === "csv") return <CsvWorkflow file={file} notice={notice} handleFile={handleFile} clearFile={() => { setFile(null); setCsvResult(null); setNotice(""); }} busy={csvBusy} result={csvResult} onAnalyze={runCsvAnalysis} />;
  if (module.id === "reports") return <ReportWorkflow module={module} file={file} notice={notice} handleFile={handleFile} clearFile={() => { setFile(null); setReportResult(null); setNotice(""); }} busy={reportBusy} result={reportResult} onExtract={runReportExtraction} />;
  if (module.id === "histopathology") return <HistopathologyWorkflow module={module} file={file} notice={notice} handleFile={handleFile} clearFile={() => { setFile(null); setHistopathResult(null); setNotice(""); }} busy={histopathBusy} result={histopathResult} includeGradCam={includeGradCam} setIncludeGradCam={setIncludeGradCam} checkpointId={checkpointId} setCheckpointId={setCheckpointId} onAnalyze={runHistopathology} />;
  if (module.id === "brca") return <BrcaReadinessWorkflow module={module} />;
  if (["ct", "mri", "xray"].includes(module.id)) return <ImagingReviewWorkflow module={module} file={file} dicomFiles={dicomFiles} setDicomFiles={(files) => { setDicomFiles(files); setFile(null); setImagingResult(null); setNotice(`${files.length} DICOM files selected for a one-series metadata check.`); }} notice={notice} handleFile={(selected) => { setDicomFiles([]); handleFile(selected); }} clearFile={() => { setFile(null); setDicomFiles([]); setImagingResult(null); setNotice(""); }} busy={imagingBusy} result={imagingResult} onInspect={runImagingReview} />;
  return <div className="page-content">
    <div className="back-link"><Link to="/">← Back to dashboard</Link></div>
    <PageIntro eyebrow="ANALYSIS MODULE" title={module.title} description={module.description} action={<span className="badge badge-warning">No compatible AI model</span>} />
    <div className="module-detail-grid">
      <section className="surface-card upload-panel"><div className="card-title-row"><div><div className="eyebrow">INPUT WORKSPACE</div><h3>Input review is available</h3></div><div className={`module-icon ${module.accent}`}><Icon size={21} /></div></div><p className="muted">This module does not yet have a supported processing or prediction workflow. For CT, MRI, or X-ray files, use the metadata review workflow to inspect one file.</p><div className="inline-notice"><CircleHelp size={16} />AI inference stays disabled until a compatible, licensed model and evaluation evidence are registered.</div><Link className="button button-secondary full-width" to="/models">Review model registry <ArrowRight size={15} /></Link></section>
      <aside className="module-side-column"><section className="surface-card"><div className="eyebrow">MODULE READINESS</div><h3>Input checks only</h3><p className="muted">A limited file inspection may be available. No CT-, MRI-, or radiology-specific model is installed.</p><div className="status-row"><span>AI inference</span><span className="status-value pending">Unavailable</span></div><div className="status-row"><span>Clinical validation</span><span className="status-value pending">None</span></div></section></aside>
    </div>
    <div className="medical-disclaimer"><ShieldCheck size={17} /><div><strong>Research software notice</strong><p>This software does not diagnose cancer and must not be used to make clinical decisions.</p></div></div>
  </div>;
}

function HistopathologyWorkflow({ module, file, notice, handleFile, clearFile, busy, result, includeGradCam, setIncludeGradCam, checkpointId, setCheckpointId, onAnalyze }: {
  module: ResearchModule; file: File | null; notice: string;
  handleFile: (file: File | undefined) => void; clearFile: () => void; busy: boolean;
  result: HistopathologyResult | null; includeGradCam: boolean; setIncludeGradCam: (value: boolean) => void;
  checkpointId: string; setCheckpointId: (value: string) => void;
  onAnalyze: () => void;
}) {
  const configured = module.status === "research_model_paths_set_unverified";
  const checkpointFilesPresent = (module.available_checkpoints ?? 0) > 0;
  const selectedCheckpoint = module.checkpoints?.find((checkpoint) => checkpoint.id === checkpointId);
  const checkpointStatus = configured ? "Checkpoint paths set · unverified" : checkpointFilesPresent ? `${module.available_checkpoints} checkpoints included · not configured` : "No checkpoints included";
  return <div className="page-content">
    <div className="back-link"><Link to="/">← Back to dashboard</Link></div>
    <PageIntro eyebrow="RESEARCH-ONLY IMAGE WORKFLOW" title="Histopathology" description="Choose from the included BreaKHis ResNet-18 fold and magnification checkpoints. A compatible existing Python environment is required. This is not for diagnosis or clinical use." action={<span className={`badge ${configured || checkpointFilesPresent ? "badge-warning" : "badge-neutral"}`}>{checkpointStatus}</span>} />
    <section className="medical-disclaimer"><ShieldCheck size={18} /><div><strong>Research model output only — not for diagnosis or patient care</strong><p>The saved model achieved near-chance accuracy in the BACH external evaluation and did not transfer reliably to that dataset. Do not use this workflow on patient images or to guide care.</p></div></section>
    <div className="module-detail-grid">
      <section className="surface-card upload-panel"><div className="card-title-row"><div><div className="eyebrow">LOCAL IMAGE INPUT</div><h3>Choose a histopathology image</h3></div><div className={`module-icon ${module.accent}`}><Microscope size={21} /></div></div>
        <p className="muted">PNG, JPG, or TIFF up to 50 MB. The file stays in your browser until you run the local research model, then its encrypted copy and result are saved to your local account history.</p>
        <div className="form-field"><label htmlFor="research-checkpoint">Included model checkpoint</label><select id="research-checkpoint" value={checkpointId} onChange={(event) => setCheckpointId(event.target.value)} disabled={!module.checkpoints?.length}>{(module.checkpoints ?? []).map((checkpoint) => <option key={checkpoint.id} value={checkpoint.id}>{checkpoint.architecture} · {checkpoint.fold} · {checkpoint.magnification}</option>)}</select></div>
        <label className="drop-zone"><input type="file" aria-label="Choose a tissue image" accept=".png,.jpg,.jpeg,.tif,.tiff,image/png,image/jpeg,image/tiff" onChange={(event) => handleFile(event.target.files?.[0])} /><span className="upload-circle"><Upload size={21} /></span><strong>{file ? file.name : "Choose a tissue image"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · selected locally` : "PNG · JPG · TIFF · 50 MB maximum"}</span><span className="button button-secondary button-small">Browse files</span></label>
        {file && <div className="selected-file"><FileText size={18} /><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></div><button className="icon-button" onClick={clearFile} aria-label="Remove selected image"><X size={16} /></button></div>}
        <label className="research-toggle"><input type="checkbox" checked={includeGradCam && selectedCheckpoint?.architecture === "ResNet-18"} disabled={selectedCheckpoint?.architecture !== "ResNet-18"} onChange={(event) => setIncludeGradCam(event.target.checked)} /><span>Generate Grad-CAM visualization{selectedCheckpoint?.architecture === "Scratch CNN baseline" ? " (ResNet-18 only)" : ""}</span></label>
        {notice && <div className="inline-notice" role="alert"><CircleHelp size={16} />{notice}{notice.startsWith("Sign in") && <> <Link to="/login" className="text-link">Sign in</Link></>}</div>}
        {configured && <div className="inline-notice"><CircleHelp size={16} /><span>Both configured paths exist, but package compatibility, checkpoint format, and successful inference are not verified until this model is run.</span></div>}
        {!configured && <div className="inline-notice"><CircleHelp size={16} /><span>{checkpointFilesPresent ? "Checkpoint files are included. Inference needs a compatible existing PyTorch environment configured in backend/.env." : "Set RESEARCH_MODEL_PYTHON in backend/.env and add compatible checkpoint files before running the research model."} Do not install or replace PyTorch as part of this project setup.</span></div>}
        <button className="button button-primary full-width" disabled={!configured || !file || busy} onClick={onAnalyze}><Microscope size={16} /> {busy ? "Running local research model…" : "Run research model"} <ArrowRight size={15} /></button>
        <p className="privacy-hint"><LockKeyhole size={13} /> No result is produced unless a compatible checkpoint and PyTorch environment are configured.</p>
      </section>
      <aside className="module-side-column"><section className="surface-card"><div className="eyebrow">MODEL PROVENANCE</div><h3>BreaKHis ResNet-18</h3><div className="status-row"><span>Task</span><span className="status-value pending">Benign / malignant research labels</span></div><div className="status-row"><span>Input size</span><span className="status-value success">128 × 128</span></div><div className="status-row"><span>Clinical validation</span><span className="status-value pending">None</span></div><div className="status-row"><span>External BACH accuracy</span><span className="status-value pending">49–52% mean</span></div></section><section className="surface-card"><div className="eyebrow">INTERPRETATION LIMITS</div><h3>Scores and heatmaps</h3><p className="muted">Softmax scores are not calibrated probabilities. Grad-CAM highlights image regions associated with a model output; it does not explain cause or establish tissue diagnosis.</p></section></aside>
    </div>
    {result && <section className="surface-card report-results" aria-live="polite"><div className="table-intro"><div><div className="eyebrow">RESEARCH-ONLY MODEL OUTPUT</div><h3>{result.filename}</h3><p>{result.model} · {result.training_fold} · {result.training_magnification} · {result.execution_device}</p></div><span className="badge badge-warning">Not a diagnosis</span></div><div className="research-output-grid"><div className="research-output-card"><span>Predicted class</span><strong>{result.predicted_class}</strong><small>Model output only</small></div><div className="research-output-card"><span>Benign softmax score</span><strong>{(result.class_scores.benign * 100).toFixed(1)}%</strong><small>Not calibrated</small></div><div className="research-output-card"><span>Malignant softmax score</span><strong>{(result.class_scores.malignant * 100).toFixed(1)}%</strong><small>Not calibrated</small></div></div><p className="muted">{result.score_note}</p>{result.grad_cam_overlay_png_base64 && <figure className="research-heatmap"><img src={`data:image/png;base64,${result.grad_cam_overlay_png_base64}`} alt="Grad-CAM visualization overlay for the research model output" /><figcaption>{result.explanation}</figcaption></figure>}<div className="medical-disclaimer"><ShieldCheck size={17} /><div><strong>Do not use for clinical decisions</strong><p>This model has poor transfer performance on BACH and is not clinically validated.</p></div></div></section>}
  </div>;
}

function ImagingReviewWorkflow({ module, file, dicomFiles, setDicomFiles, notice, handleFile, clearFile, busy, result, onInspect }: {
  module: ResearchModule; file: File | null; dicomFiles: File[]; setDicomFiles: (files: File[]) => void; notice: string;
  handleFile: (file: File | undefined) => void; clearFile: () => void; busy: boolean;
  result: ImagingInspectionResult | null; onInspect: () => void;
}) {
  const planning = module.id === "ct" ? ["Choose the intended question first: for example, staging or a defined imaging finding.", "Identify an authorized breast-cancer CT cohort with patient-level outcomes.", "Specify patient-separated splits and an independent evaluation before training."] : module.id === "mri" ? ["Choose one target, such as lesion classification or a defined treatment-response endpoint.", "Identify a compatible breast MRI cohort and its patient-level labels.", "Document sequence, preprocessing, patient-separated splits, and an independent evaluation."] : ["The proposed first task is cropped mammography mass benign-versus-malignant research classification.", "The local pilot audit verified only 2 of 20 image/mask pairs; it is not trainable.", "Training remains paused until image/label mapping and patient-separated splits are verified."];
  return <div className="page-content">
    <div className="back-link"><Link to="/">← Back to dashboard</Link></div>
    <PageIntro eyebrow="INPUT REVIEW ONLY" title={module.title} description="Inspect image or volume headers and check one DICOM series for technical consistency. No model prediction is available for this modality." action={<span className="badge badge-warning">No AI model installed</span>} />
    <section className="medical-disclaimer"><ShieldCheck size={18} /><div><strong>Metadata inspection only — no image interpretation</strong><p>This tool does not detect or classify cancer. Uploaded files and returned metadata are encrypted in your local account history. Use only authorized, de-identified research data; this local prototype is not a secure clinical record system.</p></div></section>
    <div className="module-detail-grid">
      <section className="surface-card upload-panel"><div className="card-title-row"><div><div className="eyebrow">LOCAL INPUT</div><h3>Inspect an image, volume, or DICOM series</h3></div><div className={`module-icon ${module.accent}`}><Scan size={21} /></div></div>
        <p className="muted">DICOM (.dcm/.dicom), NIfTI (.nii/.nii.gz), PNG, JPG, JPEG, or TIFF. DICOM and raster files up to 50 MB each; NIfTI up to 500 MB. A DICOM series may contain up to 500 instances / 250 MB total.</p>
        <label className="drop-zone"><input type="file" aria-label="Choose one image or volume" accept=".dcm,.dicom,.nii,.nii.gz,.png,.jpg,.jpeg,.tif,.tiff,application/dicom,image/png,image/jpeg,image/tiff" onChange={(event) => handleFile(event.target.files?.[0])} /><span className="upload-circle"><Upload size={21} /></span><strong>{file ? file.name : "Choose one image or volume"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · selected locally` : "Single file metadata review"}</span><span className="button button-secondary button-small">Browse files</span></label>
        <label className="form-field" style={{ marginTop: 16 }}><span>Select a DICOM series (multiple files)</span><input type="file" multiple accept=".dcm,.dicom,application/dicom" onChange={(event) => setDicomFiles(Array.from(event.target.files ?? []))} /></label>
        {dicomFiles.length > 0 && <p className="muted">{dicomFiles.length} DICOM instances selected · encrypted series saved to local history</p>}
        {file && <div className="selected-file"><FileText size={18} /><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></div><button className="icon-button" onClick={clearFile} aria-label="Remove selected image"><X size={16} /></button></div>}
        {notice && <div className="inline-notice" role="alert"><CircleHelp size={16} />{notice}{notice.startsWith("Sign in") && <> <Link to="/login" className="text-link">Sign in</Link></>}</div>}
        <button className="button button-primary full-width" disabled={(!file && !dicomFiles.length) || busy} onClick={onInspect}><Scan size={16} /> {busy ? "Inspecting metadata…" : dicomFiles.length ? "Inspect DICOM series" : "Inspect input"} <ArrowRight size={15} /></button>
        <p className="privacy-hint"><LockKeyhole size={13} /> Technical metadata only. No pixel-level AI inference or diagnosis.</p>
      </section>
      <aside className="module-side-column"><section className="surface-card"><div className="eyebrow">CURRENT SUPPORT</div><h3>Technical input checks</h3><div className="status-row"><span>Raster dimensions</span><span className="status-value success">Available</span></div><div className="status-row"><span>DICOM modality match</span><span className="status-value success">Available</span></div><div className="status-row"><span>DICOM series / NIfTI header</span><span className="status-value success">Available</span></div><div className="status-row"><span>Modality model</span><span className="status-value pending">Not installed</span></div></section><section className="surface-card"><div className="eyebrow">RESEARCH READINESS</div><h3>What must happen next</h3><ol className="readiness-steps">{planning.map((item) => <li key={item}>{item}</li>)}</ol></section><section className="surface-card"><div className="eyebrow">DATA HANDLING</div><h3>No identifying fields returned</h3><p className="muted">For DICOM, the endpoint reads headers before pixel data and returns only technical metadata. For NIfTI, it reads the header only. The encrypted local archive retains original uploads until deleted in History.</p></section></aside>
    </div>
    {result && <section className="surface-card report-results" aria-live="polite"><div className="table-intro"><div><div className="eyebrow">INPUT METADATA</div><h3>{file?.name ?? (dicomFiles.length ? `${dicomFiles.length} DICOM instances` : "Input metadata")}</h3><p>{result.inspection_type === "dicom_series_header_metadata" ? "DICOM series consistency check; pixel data not read" : result.inspection_type === "dicom_header_metadata" ? "DICOM header, pixel data not read" : result.inspection_type === "nifti_header_metadata" ? "NIfTI header only; voxel data not read" : "Raster image metadata"}</p></div><span className="badge badge-warning">No AI inference</span></div><div className="results-detail-list imaging-metadata-list"><div><span>Module selected</span><strong>{module.title}</strong></div><div><span>Modality</span><strong>{result.modality_check === "matches_selected_module" ? result.metadata.modality : "Not verified from this header"}</strong></div>{result.metadata.instances !== undefined && <div><span>Series instances</span><strong>{result.metadata.instances}</strong></div>}{result.metadata.dimensions && <div><span>Volume dimensions</span><strong>{result.metadata.dimensions.join(" × ")}</strong></div>}{result.metadata.voxel_spacing && <div><span>Voxel spacing</span><strong>{result.metadata.voxel_spacing.join(" × ")}</strong></div>}{result.metadata.data_type && <div><span>Data type</span><strong>{result.metadata.data_type}</strong></div>}{result.metadata.orientation_consistent !== undefined && <div><span>Orientation consistent</span><strong>{result.metadata.orientation_consistent ? "Yes" : "Not verifiable"}</strong></div>}{result.metadata.format && <div><span>File format</span><strong>{result.metadata.format} · {result.metadata.mode}</strong></div>}{result.metadata.rows && <div><span>Image dimensions</span><strong>{result.metadata.rows} × {result.metadata.columns} pixels</strong></div>}{result.metadata.width && <div><span>Image dimensions</span><strong>{result.metadata.width} × {result.metadata.height} pixels</strong></div>}{result.metadata.frames && <div><span>Frames</span><strong>{result.metadata.frames}</strong></div>}{result.metadata.pixel_spacing_mm && <div><span>Pixel spacing</span><strong>{result.metadata.pixel_spacing_mm.join(" × ")} mm</strong></div>}{result.metadata.slice_thickness_mm && <div><span>Slice thickness</span><strong>{result.metadata.slice_thickness_mm.join(" × ")} mm</strong></div>}{result.metadata.duplicate_slice_positions !== undefined && <div><span>Repeated positions</span><strong>{result.metadata.duplicate_slice_positions ? "Detected" : "Not detected"}</strong></div>}</div>{result.note && <p className="muted imaging-result-note">{result.note}</p>}</section>}
  </div>;
}

function BrcaReadinessWorkflow({ module }: { module: ResearchModule }) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  async function preflight() {
    if (!file) { setNotice("Choose a de-identified cohort CSV first."); return; }
    if (!localStorage.getItem("breastcare_access_token")) { setNotice("Sign in before submitting a file. The cohort is processed in memory and is not saved."); return; }
    setBusy(true); setNotice(""); setResult(null);
    try { setResult(await preflightBrcaCohort(file)); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Cohort preflight failed."); }
    finally { setBusy(false); }
  }
  return <div className="page-content"><div className="back-link"><Link to="/">← Back to dashboard</Link></div>
    <PageIntro eyebrow="GENOMICS RESEARCH PLANNING" title={module.title} description="Define a responsible, testable BRCA1/2 research question and check a de-identified cohort table before modeling." action={<span className="badge badge-warning">Cohort preflight · no model</span>} />
    <section className="medical-disclaimer"><ShieldCheck size={18} /><div><strong>Cohort preflight only — no variant interpretation or prediction</strong><p>Only submit a de-identified, authorized research cohort summary CSV. Do not upload raw sequence files, direct identifiers, or clinical records. This page does not estimate inherited risk or provide genetic counseling.</p></div></section>
    <div className="module-detail-grid"><section className="surface-card upload-panel"><div className="eyebrow">IN-MEMORY COHORT CHECK</div><h3>Check cohort labels and schema</h3><p className="muted">CSV must contain <code>sample_id</code>, <code>target_type</code> (germline or somatic), and <code>label</code>. The check returns aggregate counts, processes up to 50 MB, and does not retain CSV rows.</p><label className="drop-zone"><input type="file" accept=".csv,text/csv" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setResult(null); setNotice(""); }} /><span className="upload-circle"><Upload size={21} /></span><strong>{file?.name ?? "Choose a de-identified cohort CSV"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · selected locally` : "CSV only · maximum 50 MB"}</span><span className="button button-secondary button-small">Browse files</span></label>{file && <div className="selected-file"><FileText size={18} /><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></div><button className="icon-button" onClick={() => { setFile(null); setResult(null); setNotice(""); }} aria-label="Remove selected cohort file"><X size={16} /></button></div>}{notice && <div className="inline-notice" role="alert"><CircleHelp size={16} />{notice}{notice.startsWith("Sign in") && <> <Link to="/login" className="text-link">Sign in</Link></>}</div>}<button className="button button-primary full-width" disabled={busy || !file} onClick={preflight}>{busy ? "Checking cohort…" : "Preflight cohort CSV"} <ArrowRight size={15} /></button><p className="privacy-hint"><LockKeyhole size={13} /> Authenticated local check. Raw rows are processed in memory and discarded; no mutation prediction is produced.</p></section>
      <section className="surface-card"><div className="eyebrow">DECISIONS REQUIRED</div><h3>Make the target precise</h3><ol className="readiness-steps"><li>Specify whether the target is a germline BRCA1/2 pathogenic variant or a tumor somatic alteration; these are different research tasks.</li><li>Select the population, outcome definition, prediction time point, and intended research use.</li><li>Identify a permitted, labeled cohort and document its access tier, consent basis, and data-use terms.</li><li>Plan patient-level splits, leakage checks, external evaluation, calibration, and subgroup reporting before fitting a model.</li></ol></section>
      <aside className="module-side-column"><section className="surface-card"><div className="eyebrow">CURRENT STATUS</div><h3>Not ready for prediction</h3><div className="status-row"><span>Target defined</span><span className="status-value pending">No</span></div><div className="status-row"><span>Authorized labeled cohort</span><span className="status-value pending">Not configured</span></div><div className="status-row"><span>BRCA model weights</span><span className="status-value pending">Not installed</span></div><div className="status-row"><span>Raw genomic upload / inference</span><span className="status-value pending">Disabled</span></div></section><section className="surface-card"><div className="eyebrow">SAFE NEXT STEP</div><h3>Write the study specification</h3><p className="muted">Record the population, exact mutation label, data source and access route, split strategy, and evaluation plan in the research roadmap before collecting data.</p><Link className="text-link" to="/models">Review the model registry <ArrowRight size={15} /></Link></section></aside></div>
      {result && <section className="surface-card report-results research-check-results"><div className="table-intro"><div><div className="eyebrow">AGGREGATE CHECK RESULT</div><h3>BRCA cohort preflight</h3></div><span className="badge badge-warning">No prediction</span></div><pre>{JSON.stringify(result, null, 2)}</pre></section>}
  </div>;
}

function CsvWorkflow({ file, notice, handleFile, clearFile, busy, result, onAnalyze }: {
  file: File | null; notice: string;
  handleFile: (file: File | undefined) => void; clearFile: () => void; busy: boolean;
  result: CsvAnalysisResult | null; onAnalyze: () => void;
}) {
  return <div className="page-content">
    <div className="back-link"><Link to="/">← Back to dashboard</Link></div>
    <PageIntro eyebrow="ANALYSIS MODULE" title="CSV Analysis" description="Upload a CSV to inspect its structure, missing values, descriptive statistics and chart-ready summaries." action={<span className="badge badge-success">Descriptive analysis available</span>} />
    <div className="module-detail-grid">
      <section className="surface-card upload-panel"><div className="card-title-row"><div><div className="eyebrow">INPUT WORKSPACE</div><h3>Analyze a dataset</h3></div><div className="module-icon teal"><Table2 size={21} /></div></div>
        <p className="muted">CSV files up to 50 MB are processed locally and saved encrypted with their result in your signed-in account history. Delete entries from the History page when no longer needed.</p>
        <label className="drop-zone"><input type="file" aria-label="Choose a CSV file" accept=".csv,text/csv" onChange={(e) => handleFile(e.target.files?.[0])} /><span className="upload-circle"><Upload size={21} /></span><strong>{file ? file.name : "Choose a CSV file"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · ready to upload` : "UTF-8 and common text encodings supported · 50 MB maximum"}</span><span className="button button-secondary button-small">Browse files</span></label>
        {file && <div className="selected-file"><FileText size={18} /><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></div><button className="icon-button" onClick={clearFile} aria-label="Remove selected file"><X size={16} /></button></div>}
        {notice && <div className="inline-notice" role="alert"><CircleHelp size={16} />{notice}{notice.startsWith("Sign in") && <> <Link to="/login" className="text-link">Sign in</Link></>}</div>}
        <button className="button button-primary full-width" disabled={busy || !file} onClick={onAnalyze}><Table2 size={16} /> {busy ? "Analyzing CSV…" : "Analyze CSV"} <ArrowRight size={15} /></button>
        <p className="privacy-hint"><LockKeyhole size={13} /> Descriptive summaries only. No diagnosis, risk score or medical prediction is produced. Use authorized, de-identified research files only.</p>
      </section>
      <aside className="module-side-column"><section className="surface-card"><div className="eyebrow">ANALYSIS SCOPE</div><h3>Dataset exploration</h3><p className="muted">Reports dimensions, inferred column types, missingness, numeric summaries and frequent categories for charts.</p><div className="status-row"><span>Upload limit</span><span className="status-value success">50 MB</span></div><div className="status-row"><span>Medical prediction</span><span className="status-value pending">Not performed</span></div><div className="status-row"><span>File persistence</span><span className="status-value success">Encrypted locally</span></div></section><section className="medical-disclaimer"><ShieldCheck size={17} /><div><strong>Descriptive statistics are not diagnosis</strong><p>These summaries describe the uploaded data and must not be used to make clinical decisions. Do not upload identifiable patient data.</p></div></section></aside>
    </div>
    {result && <section className="csv-results surface-card" aria-live="polite">
      <div className="table-intro"><div><div className="eyebrow">DESCRIPTIVE RESULTS</div><h3>{result.filename}</h3><p>{result.shape.rows.toLocaleString()} rows · {result.shape.columns} columns · summary only</p></div><span className="badge badge-success">No diagnosis</span></div>
      <h4>Columns and missing values</h4><div className="table-scroll"><table><thead><tr><th>Column</th><th>Type</th><th>Missing</th><th>Missing %</th></tr></thead><tbody>{result.columns.map((col) => <tr key={col.name}><td><strong>{col.name}</strong></td><td>{col.dtype}</td><td>{col.missing.toLocaleString()}</td><td>{col.missing_percent}%</td></tr>)}</tbody></table></div>
      <h4>Numeric descriptive statistics</h4>{result.chart_data.numeric.length ? <div className="table-scroll"><table><thead><tr><th>Column</th><th>Count</th><th>Mean</th><th>Std</th><th>Min</th><th>Median</th><th>Max</th></tr></thead><tbody>{result.chart_data.numeric.map((item) => <tr key={item.column}><td><strong>{item.column}</strong></td><td>{item.count}</td><td>{formatStat(item.mean)}</td><td>{formatStat(item.std)}</td><td>{formatStat(item.min)}</td><td>{formatStat(item.median)}</td><td>{formatStat(item.max)}</td></tr>)}</tbody></table></div> : <p className="muted csv-empty">No numeric columns were detected.</p>}
      {result.chart_data.categorical.length > 0 && <><h4>Chart-ready category counts <small>(top 20 per column)</small></h4><div className="csv-category-grid">{result.chart_data.categorical.map((group) => <div className="csv-category-card" key={group.column}><strong>{group.column}</strong>{group.counts.map((entry) => <div key={entry.label}><span>{entry.label}</span><b>{entry.count}</b></div>)}</div>)}</div></>}
    </section>}
  </div>;
}
function formatStat(value: number | null) { return value === null ? "—" : Number(value.toPrecision(5)).toLocaleString(); }

function ReportWorkflow({ module, file, notice, handleFile, clearFile, busy, result, onExtract }: {
  module: ResearchModule; file: File | null; notice: string; handleFile: (file: File | undefined) => void;
  clearFile: () => void; busy: boolean; result: ReportExtractionResult | null; onExtract: () => void;
}) {
  return <div className="page-content">
    <div className="back-link"><Link to="/">← Back to dashboard</Link></div>
    <PageIntro eyebrow="DOCUMENT WORKFLOW" title={module.title} description="Extract text from a report PDF or image, then review the extracted text yourself." action={<span className="badge badge-success">Text extraction available</span>} />
    <div className="module-detail-grid">
      <section className="surface-card upload-panel"><div className="card-title-row"><div><div className="eyebrow">INPUT WORKSPACE</div><h3>Extract report text</h3></div><div className="module-icon green"><FileText size={21} /></div></div>
        <p className="muted">PDF and image files up to 25 MB are processed locally and saved encrypted with extracted text in your account history. Only authorized, de-identified research files should be used.</p>
        <label className="drop-zone"><input type="file" aria-label="Choose a report PDF or image" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.bmp,application/pdf,image/*" onChange={(e) => handleFile(e.target.files?.[0])} /><span className="upload-circle"><Upload size={21} /></span><strong>{file ? file.name : "Choose a report PDF or image"}</strong><span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · ready to upload` : "PDF (up to 20 pages), PNG, JPG, TIFF or BMP · 25 MB maximum"}</span><span className="button button-secondary button-small">Browse files</span></label>
        {file && <div className="selected-file"><FileText size={18} /><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></div><button className="icon-button" onClick={clearFile} aria-label="Remove selected file"><X size={16} /></button></div>}
        {notice && <div className="inline-notice" role="alert"><CircleHelp size={16} />{notice}{notice.startsWith("Sign in") && <> <Link to="/login" className="text-link">Sign in</Link></>}</div>}
        <button className="button button-primary full-width" disabled={busy || !file} onClick={onExtract}><FileText size={16} /> {busy ? "Extracting text…" : "Extract text"} <ArrowRight size={15} /></button>
        <p className="privacy-hint"><LockKeyhole size={13} /> Text extraction only. No diagnosis, summary, or clinical interpretation is produced.</p>
      </section>
      <aside className="module-side-column"><section className="surface-card"><div className="eyebrow">WHAT THIS DOES</div><h3>Text for your review</h3><p className="muted">Digital PDFs use their embedded text. Scanned PDFs and images use the local Tesseract OCR engine.</p><div className="status-row"><span>Maximum file size</span><span className="status-value success">25 MB</span></div><div className="status-row"><span>Scanned PDF length</span><span className="status-value success">20 pages</span></div><div className="status-row"><span>Medical interpretation</span><span className="status-value pending">Not performed</span></div></section><section className="medical-disclaimer"><ShieldCheck size={17} /><div><strong>Review OCR output carefully</strong><p>OCR can miss or misread text. Confirm extracted content against the original document; do not use it alone for clinical decisions.</p></div></section></aside>
    </div>
    {result && <section className="report-results surface-card" aria-live="polite"><div className="table-intro"><div><div className="eyebrow">EXTRACTED TEXT</div><h3>{result.filename}</h3><p>{result.pages} {result.pages === 1 ? "page" : "pages"} · {result.character_count.toLocaleString()} characters · {result.method === "ocr" ? "OCR" : "embedded PDF text"}</p></div><span className="badge badge-neutral">Review required</span></div><pre className="extracted-report-text">{result.text || "No text was detected in this file."}</pre><div className="table-footnote"><ShieldCheck size={15} /> Text extraction only; the application does not interpret medical meaning or provide diagnosis.</div></section>}
  </div>;
}

function ModelsPage({ modules }: { modules: ResearchModule[] }) {
  const histopathModule = modules.find((module) => module.id === "histopathology");
  const histopathConfigured = histopathModule?.status === "research_model_paths_set_unverified";
  const checkpointCount = histopathModule?.available_checkpoints ?? 0;
  const rows = [
    ["BreaKHis research checkpoints", "PNG / JPG / TIFF histopathology", `${checkpointCount} ResNet-18 + ${histopathModule?.available_baselines ?? 0} scratch-CNN baselines included · runtime unverified`],
    ["BreaKHis scratch-CNN baselines", "40X histopathology research images", "5 included · not supported by app worker"],
    ["BRCA1 / BRCA2 predictor", "Matched pathology + mutation labels", "Not installed"],
    ["CT-specific model", "Compatible CT series", "Not installed"],
    ["MRI-specific model", "Supported MRI sequences", "Not installed"],
    ["Radiology / mammography model", "Validated intended modality", "Not installed"],
    ["Document text extraction", "PDF / image reports", "Available (Tesseract required for OCR)"],
    ["CSV descriptive analysis", "Tabular datasets", "Available"],
  ];
  return <div className="page-content"><PageIntro eyebrow="RESEARCH TOOLS" title="Model registry" description="Track model readiness and requirements before enabling research workflows." /><section className="surface-card table-card"><div className="table-intro"><div><h3>Registered model slots</h3><p>{checkpointCount} ResNet-18 checkpoints and five historical scratch-CNN baselines are included locally. Runtime compatibility remains unverified; checkpoint presence is not evidence of clinical validity.</p></div><span className={`badge ${histopathConfigured ? "badge-warning" : "badge-neutral"}`}>{histopathConfigured ? "Configured paths · unverified" : `${checkpointCount} ResNet-18 files included · not configured`}</span></div><div className="table-scroll"><table><thead><tr><th>Model / processor</th><th>Expected input</th><th>Status</th></tr></thead><tbody>{rows.map((r) => <tr key={r[0]}><td><strong>{r[0]}</strong></td><td>{r[1]}</td><td><span className="status-value pending">{r[2]}</span></td></tr>)}</tbody></table></div><div className="table-footnote"><CircleHelp size={15} /> CT, MRI, mammography/X-ray and BRCA prediction weights are not included. Compatible, authorized data and independently evaluated models are still required.</div></section><section className="info-banner"><CloudDownload size={20} /><div><strong>Local model configuration</strong><p>Set <code>RESEARCH_MODEL_PYTHON</code> to an existing Python environment with compatible PyTorch, torchvision, and Pillow. The Histopathology page lets you choose among the included ResNet-18 checkpoints. This project does not install or pin PyTorch.</p></div></section></div>;
}

function ExperimentResultsPage() {
  const results = [
    { magnification: "40×", accuracy: "77.0%", accuracyRange: "72.1–80.7%", recall: "82.9%", recallRange: "76.7–89.5%", specificity: "65.4%", specificityRange: "43.3–76.6%", balanced: "74.1%" },
    { magnification: "100×", accuracy: "77.2%", accuracyRange: "73.6–80.8%", recall: "83.7%", recallRange: "72.5–92.1%", specificity: "64.4%", specificityRange: "46.9–75.5%", balanced: "74.1%" },
    { magnification: "200×", accuracy: "81.4%", accuracyRange: "75.8–84.5%", recall: "82.9%", recallRange: "70.2–88.8%", specificity: "78.1%", specificityRange: "64.9–86.1%", balanced: "80.5%" },
    { magnification: "400×", accuracy: "81.3%", accuracyRange: "76.9–84.7%", recall: "83.0%", recallRange: "79.2–86.8%", specificity: "78.2%", specificityRange: "71.6–86.6%", balanced: "80.6%" },
  ];

  return <div className="page-content experiment-results-page">
    <PageIntro eyebrow="RESEARCH EVALUATION" title="BreaKHis experiment results" description="Five-fold summary of the research-only ResNet-18 runs across four image magnifications." />
    <section className="medical-disclaimer" aria-label="Research-only notice">
      <ShieldCheck size={18} />
      <div><strong>Research results only — not for diagnosis or clinical decisions</strong><p>This model has not been clinically validated and must not be used to assess patient images.</p></div>
    </section>

    <div className="stat-grid experiment-stat-grid">
      <StatCard icon={<FlaskConical size={19} />} label="Magnifications evaluated" value="4" note="40× · 100× · 200× · 400×" tone="teal" />
      <StatCard icon={<Activity size={19} />} label="Fold-level runs" value="20" note="Five official splits per magnification" tone="blue" />
      <StatCard icon={<BrainCircuit size={19} />} label="Model" value="ResNet-18" note="ImageNet weights; research baseline" tone="purple" />
      <StatCard icon={<ShieldCheck size={19} />} label="BACH research evaluation" value="400 images" note="49–52% mean accuracy; weak transfer" tone="orange" />
    </div>

    <section className="surface-card table-card experiment-table-card">
      <div className="table-intro"><div><div className="eyebrow">MEAN FOLD METRICS</div><h3>Magnification comparison</h3><p>Arithmetic mean across five fold-level runs; ranges show minimum to maximum fold results.</p></div><span className="badge badge-neutral">20 runs</span></div>
      <div className="table-scroll"><table className="experiment-table"><thead><tr><th>Magnification</th><th>Accuracy</th><th>Malignant recall</th><th>Benign specificity</th><th>Balanced accuracy</th></tr></thead><tbody>{results.map((row) => <tr key={row.magnification}><td><strong>{row.magnification}</strong></td><td><strong>{row.accuracy}</strong><small>{row.accuracyRange}</small></td><td><strong>{row.recall}</strong><small>{row.recallRange}</small></td><td><strong>{row.specificity}</strong><small>{row.specificityRange}</small></td><td><strong>{row.balanced}</strong></td></tr>)}</tbody></table></div>
      <div className="table-footnote"><CircleHelp size={15} /> Fold test sets overlap. Use mean fold-level metrics; do not interpret their counts as unique cases pooled into one test set.</div>
    </section>

    <section className="surface-card table-card experiment-table-card bach-results-card">
      <div className="table-intro"><div><div className="eyebrow">SEPARATE EXTERNAL RESEARCH EVALUATION</div><h3>BACH transfer results</h3><p>Each saved BreaKHis fold model was evaluated on the same 400 BACH Photos images; means below summarize five models per training magnification.</p></div><span className="badge badge-warning">Not clinical validation</span></div>
      <div className="table-scroll"><table className="experiment-table"><thead><tr><th>BreaKHis training magnification</th><th>BACH accuracy</th><th>Carcinoma recall</th><th>Non-carcinoma specificity</th><th>Balanced accuracy</th></tr></thead><tbody>
        <tr><td><strong>40×</strong></td><td>50.2%</td><td>70.1%</td><td>30.3%</td><td>50.2%</td></tr>
        <tr><td><strong>100×</strong></td><td>49.2%</td><td>79.6%</td><td>18.7%</td><td>49.2%</td></tr>
        <tr><td><strong>200×</strong></td><td>52.1%</td><td>79.7%</td><td>24.5%</td><td>52.1%</td></tr>
        <tr><td><strong>400×</strong></td><td>49.2%</td><td>85.7%</td><td>12.6%</td><td>49.2%</td></tr>
      </tbody></table></div>
      <div className="table-footnote"><CircleHelp size={15} /> Study-specific binary mapping: Benign + Normal → non-carcinoma; InSitu + Invasive → carcinoma. Low specificity shows many non-carcinoma images were labeled carcinoma. Results are near chance and indicate poor transfer in this setup.</div>
    </section>

    <div className="results-detail-grid">
      <section className="surface-card"><div className="eyebrow">EXPERIMENT SETUP</div><h3>How these results were produced</h3><div className="results-detail-list"><div><span>Dataset</span><strong>BreaKHis</strong></div><div><span>Task</span><strong>Benign vs malignant image classification</strong></div><div><span>Input size</span><strong>128 × 128 pixels</strong></div><div><span>Training</span><strong>Layer 4 and classifier fine-tuned; early stopping on validation loss</strong></div><div><span>Group separation</span><strong>Fit, validation, and test groups did not overlap within each run</strong></div></div></section>
      <section className="surface-card results-reading-card"><div className="eyebrow">INTERPRETATION</div><h3>External transfer was poor</h3><p>On BreaKHis, the 200× and 400× runs had higher mean accuracy than the 40× and 100× runs, with no reliable winning magnification established.</p><p>On BACH, all magnification groups were near 50% accuracy and had low non-carcinoma specificity. These models should not be used on patient images or for clinical decisions.</p><Link to="/models" className="text-link">Review model readiness <ArrowRight size={15} /></Link></section>
    </div>
  </div>;
}

function HistoryPage() {
  const [items, setItems] = useState<AnalysisHistoryItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [originalPreview, setOriginalPreview] = useState<{ id: number; kind: "image" | "pdf" | "text"; url?: string; text?: string; truncated?: boolean } | null>(null);
  useEffect(() => () => { if (originalPreview?.url) URL.revokeObjectURL(originalPreview.url); }, [originalPreview?.url]);
  async function refresh() {
    setLoading(true); setError("");
    try { setItems(await getAnalysisHistory()); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not load saved analyses."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);
  async function view(id: number) {
    setBusyId(id); setError("");
    try { const record = await getAnalysisHistoryDetail(id); setSelected(id); setDetail(record.result); setOriginalPreview(null); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not load this result."); }
    finally { setBusyId(null); }
  }
  async function download(id: number) {
    setBusyId(id); setError("");
    try {
      const blob = await downloadAnalysisFile(id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a"); anchor.href = url;
      anchor.download = items.find((item) => item.id === id)?.filename ?? "research-upload";
      anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not download this file."); }
    finally { setBusyId(null); }
  }
  async function previewOriginal(item: AnalysisHistoryItem) {
    if (originalPreview?.id === item.id) { setOriginalPreview(null); return; }
    setBusyId(item.id); setError("");
    try {
      const blob = await downloadAnalysisFile(item.id);
      if (item.content_type.startsWith("image/") || /\.(png|jpe?g|tiff?|bmp)$/i.test(item.filename)) setOriginalPreview({ id: item.id, kind: "image", url: URL.createObjectURL(blob) });
      else if (item.content_type === "application/pdf" || item.filename.toLowerCase().endsWith(".pdf")) setOriginalPreview({ id: item.id, kind: "pdf", url: URL.createObjectURL(blob) });
      else {
        const text = await blob.slice(0, 150_000).text();
        setOriginalPreview({ id: item.id, kind: "text", text, truncated: item.size_bytes > 150_000 });
      }
    } catch (err) { setError(err instanceof Error ? err.message : "Could not preview this original file."); }
    finally { setBusyId(null); }
  }  async function remove(id: number) {
    if (!window.confirm("Delete this saved result and its encrypted original upload? This cannot be undone.")) return;
    setBusyId(id); setError("");
    try { await deleteAnalysisHistory(id); setItems((current) => current.filter((item) => item.id !== id)); if (selected === id) { setSelected(null); setDetail(null); } if (originalPreview?.id === id) setOriginalPreview(null); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not delete this history entry."); }
    finally { setBusyId(null); }
  }
  return <div className="page-content">
    <PageIntro eyebrow="RESEARCH RECORDS" title="Analysis history" description="Uploads and results are encrypted in this local database and restricted to the signed-in account. Original files can be downloaded or deleted here." />
    {error && <div className="inline-notice" role="alert"><CircleHelp size={16} />{error}{error.toLowerCase().includes("sign in") && <> <Link to="/login" className="text-link">Sign in</Link></>}</div>}
    {loading ? <div className="empty-state surface-card"><p>Loading saved analyses…</p></div> : items.length === 0 ? <div className="empty-state surface-card"><div className="empty-state-icon"><ClipboardList size={27} /></div><h3>No saved analyses</h3><p>Sign in and submit an authorized, de-identified research file to save an encrypted analysis record.</p><Link to="/modules/csv" className="button button-primary">Open CSV Analysis <ArrowRight size={15} /></Link></div> : <section className="surface-card">
      <div className="table-intro"><div><div className="eyebrow">LOCAL ACCOUNT HISTORY</div><h3>{items.length} saved {items.length === 1 ? "analysis" : "analyses"}</h3></div><button className="button button-secondary" onClick={() => void refresh()}>Refresh</button></div>
      <div className="history-list">{items.map((item) => <article key={item.id} className="settings-row">
        <div><strong>{item.filename}</strong><p>{item.analysis_type} · {(item.size_bytes / 1024 / 1024).toFixed(2)} MB · {item.created_at ? new Date(item.created_at).toLocaleString() : "time unavailable"}</p></div>
        <div className="history-actions"><button className="button button-secondary button-small" disabled={busyId === item.id} onClick={() => void view(item.id)}>Result</button>{(item.content_type.startsWith("image/") || item.content_type === "application/pdf" || item.content_type.includes("csv") || /\.(png|jpe?g|tiff?|bmp|pdf)$/i.test(item.filename) || item.filename.toLowerCase().endsWith(".csv")) && <button className="button button-secondary button-small" disabled={busyId === item.id} onClick={() => void previewOriginal(item)}><Search size={14} /> Preview</button>}<button className="button button-secondary button-small" disabled={busyId === item.id} onClick={() => void download(item.id)}><Download size={14} /> Download original</button><button className="icon-button" aria-label={`Delete ${item.filename}`} disabled={busyId === item.id} onClick={() => void remove(item.id)}><Trash2 size={16} /></button></div>
                {selected === item.id && detail && <HistoryResultView result={detail} />}
        {originalPreview?.id === item.id && <div className="history-original-preview"><div className="history-preview-heading"><strong>Original uploaded file</strong><button className="button button-secondary button-small" onClick={() => setOriginalPreview(null)}>Close preview</button></div>{originalPreview.kind === "image" && originalPreview.url && <img src={originalPreview.url} alt={`Original upload ${item.filename}`} />}{originalPreview.kind === "pdf" && originalPreview.url && <iframe title={`Original PDF ${item.filename}`} src={originalPreview.url} />}{originalPreview.kind === "text" && <><pre>{originalPreview.text}</pre>{originalPreview.truncated && <p className="muted">Preview shows the first 150 KB. Download the original CSV to see the complete file.</p>}</>}</div>}
      </article>)}</div>
    </section>}
    <section className="medical-disclaimer"><ShieldCheck size={17} /><div><strong>Local storage is not clinical-grade storage</strong><p>Files are encrypted at rest using a local key. Keep the project folder private, back up the ignored encryption key securely if you need to preserve history, and never upload identifiable patient records.</p></div></section>
  </div>;
}
function SettingsPage() { return <div className="page-content"><PageIntro eyebrow="PREFERENCES" title="Settings" description="Local environment and project configuration." /><div className="settings-grid"><section className="surface-card"><div className="card-title-row"><h3>Runtime</h3><Zap size={19} /></div><div className="settings-row"><div><strong>Execution mode</strong><p>CSV, OCR, and metadata review run locally. The optional histopathology worker uses CUDA when available in its configured Python environment, otherwise CPU.</p></div><span className="badge badge-neutral">Local</span></div><div className="settings-row"><div><strong>Model availability</strong><p>Only the BreaKHis research checkpoint can be configured. CT, MRI, and radiology prediction models are not included.</p></div><span className="badge badge-warning">Research only</span></div><div className="settings-row"><div><strong>Connectivity</strong><p>After dependencies are installed, the interface and API can run locally.</p></div><span className="badge badge-success">Local</span></div></section><section className="surface-card"><div className="card-title-row"><h3>Account and saved data</h3><UserRound size={19} /></div><p className="muted">Sign in is required before uploading. Each analysis and original file is encrypted locally and restricted to its account. Delete history entries when they are no longer needed. This is not a secure clinical-record system.</p><div className="auth-actions"><Link className="text-link" to="/login">Open account page <ArrowRight size={15} /></Link><button className="button button-secondary button-small" onClick={() => { localStorage.removeItem("breastcare_access_token"); window.location.href = "/login"; }}>Sign out</button></div></section></div></div>; }
function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(() => new URLSearchParams(window.location.search).has("session_expired") ? "Your session expired. Please sign in again." : "");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setMessage("");
    try {
      if (mode === "register") {
        const response = await fetch(`${API_BASE}/api/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, username, password }) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Registration failed");
        setMessage("Account created. You can now sign in.");
        setMode("login");
      } else {
        const response = await fetch(`${API_BASE}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ username: username || email, password }) });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail ?? "Login failed");
        localStorage.setItem("breastcare_access_token", data.access_token);
        setMessage("Signed in. Research uploads and results are saved encrypted in your local account history.");
        setTimeout(() => navigate("/"), 700);
      }
    } catch (err) { setMessage(err instanceof Error ? err.message : "Request failed"); }
    finally { setBusy(false); }
  }
  return <div className="auth-wrap"><section className="auth-card surface-card"><div className="auth-brand"><Brand /></div><div className="eyebrow">LOCAL RESEARCH ACCOUNT</div><h1>{mode === "register" ? "Create your account" : "Welcome back"}</h1><p className="muted">Account access for your local BreastCare AI workspace.</p><div className="auth-tabs"><button type="button" aria-pressed={mode === "register"} className={mode === "register" ? "selected" : ""} onClick={() => { setMode("register"); setMessage(""); }}>Register</button><button type="button" aria-pressed={mode === "login"} className={mode === "login" ? "selected" : ""} onClick={() => { setMode("login"); setMessage(""); }}>Sign in</button></div><form onSubmit={submit} className="auth-form">{mode === "register" && <div className="form-field"><label>Email</label><input aria-label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" /></div>}{mode === "login" && <div className="form-field"><label>Email or username</label><input aria-label="Email or username" required value={username || email} onChange={(e) => { setUsername(e.target.value); setEmail(e.target.value); }} placeholder="Enter email or username" /></div>}{mode === "register" && <div className="form-field"><label>Username</label><input aria-label="Username" required minLength={3} value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Choose a username" /></div>}<div className="form-field"><label>Password</label><input aria-label="Password" type="password" required minLength={mode === "register" ? 10 : 1} value={password} onChange={(e) => setPassword(e.target.value)} placeholder={mode === "register" ? "At least 10 characters" : "Your password"} /></div><button className="button button-primary full-width" disabled={busy}>{busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"} <ArrowRight size={15} /></button>{message && <div className="inline-notice" role="status" aria-live="polite">{message}</div>}</form><p className="privacy-hint"><LockKeyhole size={13} /> Use only a local development environment. Configure a strong secret before any shared deployment.</p></section></div>;
}
function NotFound() { return <div className="empty-state surface-card"><h2>Page not found</h2><p>The page you requested does not exist.</p><Link className="button button-primary" to="/">Return to dashboard</Link></div>; }

export default App;

