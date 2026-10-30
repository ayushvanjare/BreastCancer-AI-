export type ModuleStatus =
  | "interface_ready_model_missing"
  | "research_checkpoints_present_unverified"
  | "research_model_paths_set_unverified"
  | "metadata_review_available_model_missing"
  | "interface_ready_text_extraction"
  | "interface_ready_descriptive_analysis"
  | "readiness_plan_only"
  | "input_preflight_available_model_missing"
  | "interface_ready_processing_not_implemented";

export interface ResearchModule {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  icon: string;
  input_types: string[];
  status: ModuleStatus;
  available_checkpoints?: number;
  available_baselines?: number;
  checkpoints?: { id: string; fold: string; magnification: string; architecture: string }[];
  accent: string;
}

