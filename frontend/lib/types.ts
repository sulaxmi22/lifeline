// Mirrors backend/models.py — keep in sync.

export type Verdict =
  | "likely_eligible"
  | "possibly_eligible"
  | "likely_ineligible";

export interface PatientProfile {
  age: number | null;
  sex: string | null;
  condition: string;
  location: string | null;
  priorTreatments: string[];
  notes: string | null;
}

export interface TrialLocation {
  city: string | null;
  state: string | null;
  country: string | null;
  facility: string | null;
}

export interface TrialContact {
  name: string | null;
  phone: string | null;
  email: string | null;
}

export interface Trial {
  nctId: string;
  briefTitle: string;
  conditions: string[];
  phase: string | null;
  status: string | null;
  eligibilityCriteria: string;
  minAge: string | null;
  maxAge: string | null;
  sex: string | null;
  healthyVolunteers: boolean | null;
  locations: TrialLocation[];
  briefSummary: string;
  contacts: TrialContact[];
}

export interface Eligibility {
  verdict: Verdict;
  confidence: number;
  reasons_for: string[];
  reasons_against: string[];
  plain_language_summary: string;
}

export interface MatchedTrial {
  trial: Trial;
  retrieval_score: number;
  rerank_score: number;
  nearest_location: TrialLocation | null;
  eligibility: Eligibility;
}

export interface EfficiencyComparison {
  always_on_cost_per_day: number;
  always_on_idle_pct: number;
  flash_run_cost: number;
  flash_utilization_pct: number;
  cheaper_factor: number;
}

export interface ComputeMetrics {
  mode: "flash_live" | "local_cpu" | "demo_simulated";
  trials_total_available: number;
  trials_processed: number;
  batch_count: number;
  peak_workers: number;
  gpu_seconds_est: number;
  cost_est: number;
  elapsed_s: number;
  timeline: { t: number; workers: number }[];
  efficiency: EfficiencyComparison;
}

export interface DonePayload {
  results: MatchedTrial[];
  compute_metrics: ComputeMetrics;
  searched_count: number;
  profile: PatientProfile;
}

export interface StageEvent {
  stage: "ingest" | "embed" | "rerank" | "reason" | "done";
  status: "active" | "complete";
  detail: string;
}

export interface TickEvent {
  t: number;
  workers: number;
  peak_workers: number;
  trials_processed: number;
  gpu_seconds_est: number;
  cost_est: number;
  elapsed: number;
}

export interface AppConfig {
  demo_mode: boolean;
  use_flash: boolean;
  use_claude: boolean;
  use_live_ingest: boolean;
  max_workers: number;
  gpu_cost_per_second: number;
}
