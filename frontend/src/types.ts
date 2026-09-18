export type RiskLevel = 'low' | 'medium' | 'high' | string
export type RunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'budget_exceeded' | string

export interface EvalCase {
  id: number
  external_id: string
  title: string
  category: string
  input_text: string
  reference_answer: string
  expected_keywords: string[]
  source_title: string
  source_url: string
  risk_level: RiskLevel
  expected_behavior: string
}

export interface PromptVersion {
  id: number
  name: string
  model: string
  system_prompt: string
  temperature: number
  is_baseline: boolean
}

export interface EvalRun {
  id: number
  prompt_version_id: number
  status: RunStatus
  mode: 'demo' | 'deepseek' | string
  started_at: string | null
  completed_at: string | null
  spent_cny: number
  error_message?: string | null
  case_count?: number
}

export interface EvalResult {
  id: number
  run_id: number
  case_id: number
  output_text: string
  correctness_score: number
  groundedness_score: number
  task_completion_score: number
  safety_pass: boolean
  latency_ms: number
  input_tokens: number
  output_tokens: number
  cost_cny: number
  failure_category?: string | null
  severity?: string | null
  needs_review: boolean
  review_status?: string | null
  external_id?: string
  case_title?: string
  risk_level?: RiskLevel
  effective_correctness_score?: number
  effective_groundedness_score?: number
  effective_task_completion_score?: number
  effective_failure_category?: string | null
  effective_severity?: string | null
  effective_pass?: boolean
  case?: EvalCase
}

export interface HumanReview {
  decision: string
  correctness_score?: number
  groundedness_score?: number
  task_completion_score?: number
  failure_category?: string
  severity?: string
  notes?: string
}

export interface Summary {
  case_count?: number
  version_count?: number
  run_count?: number
  pending_review_count?: number
  latest_run?: EvalRun | null
  counts?: { cases?: number; versions?: number; runs?: number; results?: number; reviews?: number }
  latest_runs?: EvalRun[]
  [key: string]: unknown
}

export interface CompareData {
  baseline_run_id?: number
  candidate_run_id?: number
  metrics?: Record<string, number | string | null>
  regressions?: Array<Record<string, unknown>>
  baseline_metrics?: Record<string, number>
  candidate_metrics?: Record<string, number>
  rows?: Array<Record<string, unknown>>
  severe_regressions?: number
  [key: string]: unknown
}

export interface ReleaseGateData {
  passed?: boolean
  decision?: string
  checks?: Array<{ name?: string; label?: string; passed?: boolean; actual?: number | string; threshold?: number | string; minimum?: number | string; maximum?: number | string; limit?: number | string; expected?: number | string }> | Record<string, { passed?: boolean; actual?: number | string; threshold?: number | string; minimum?: number | string; maximum?: number | string; limit?: number | string; expected?: number | string }>
  reasons?: string[]
  [key: string]: unknown
}

export interface ApiErrorShape { detail?: string | { msg?: string }[]; message?: string }
