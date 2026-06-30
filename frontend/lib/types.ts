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

export interface SerpItem {
  title: string;
  link: string;
  snippet: string;
}

export interface MatchedTrial {
  trial: Trial;
  retrieval_score: number;
  rerank_score: number;
  nearest_location: TrialLocation | null;
  eligibility: Eligibility;
  enrichment?: { provider: string; items: SerpItem[] } | null;
}

export interface EfficiencyComparison {
  always_on_cost_per_day: number;
  always_on_idle_pct: number;
  flash_run_cost: number;
  flash_utilization_pct: number;
  cheaper_factor: number;
}

export interface DataSource {
  name: string;
  via: string;
  items: number;
  ok: boolean;
}

export interface Telemetry {
  provider?: string;
  endpoint_host?: string;
  gpu?: string;
  embed_endpoint?: string;
  rerank_endpoint?: string;
  embed_endpoint_id?: string;
  rerank_endpoint_id?: string;
  embed_model?: string;
  rerank_model?: string;
  reason_engine?: string;
  batch_size?: number;
  vector_dim?: number | null;
  ingest_source?: string;
  ingest_total?: number;
  ingest_fetched?: number;
  data_sources?: DataSource[];
  enrichment?: { provider: string; via: string; enriched: number; ok: boolean } | null;
}

export interface ComputeMetrics {
  mode: "flash_live" | "local_cpu" | "demo_simulated";
  trials_total_available: number;
  trials_processed: number;
  gpu_work_items: number;
  batch_count: number;
  peak_workers: number;
  gpu_seconds_est: number;
  cost_est: number;
  elapsed_s: number;
  timeline: { t: number; workers: number }[];
  efficiency: EfficiencyComparison;
  telemetry: Telemetry;
}

export interface LogEvent {
  t: number;
  level: "info" | "warn" | "error";
  msg: string;
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
  gpu_work_items: number;
  gpu_calls: number;
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
