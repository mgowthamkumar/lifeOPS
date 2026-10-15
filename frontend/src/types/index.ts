export interface DatabaseHealth {
  connected: boolean;
  type: string;
  message: string;
}

export interface VectorDBHealth {
  configured: boolean;
  persist_dir: string;
  status: string;
}

export interface LLMHealth {
  provider: string;
  configured: boolean;
  model: string;
  message: string;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  app_name: string;
  version: string;
  database: DatabaseHealth;
  vector_db: VectorDBHealth;
  llm: LLMHealth;
  environment: string;
}

export interface Collection {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface Chunk {
  id: string;
  chunk_index: number;
  page_number?: number;
  content: string;
  token_count?: number;
  vector_id: string;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  collection_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  content_hash: string;
  current_version: number;
  status: 'UPLOADED' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'UPDATED' | 'DELETED';
  error_message?: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentItem {
  chunks: Chunk[];
}

export interface RAGSource {
  document_id: string;
  document_name: string;
  chunk_index: number;
  page_number?: number;
  version: number;
  similarity_score: number;
  content_snippet: string;
}

export interface RAGQueryResponse {
  question: string;
  answer: string;
  has_sufficient_evidence: boolean;
  confidence_score: number;
  sources: RAGSource[];
  collection_id: string;
  retrieval_count: number;
  model_used: string;
  created_at: string;
}

export interface RAGConfig {
  llm_model: string;
  embedding_model: string;
  embedding_backend: string;
  gemini_api_configured: boolean;
}

export interface TaskDocumentRef {
  id: string;
  filename: string;
  file_type: string;
}

export interface TaskItem {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  deadline?: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  estimated_duration_minutes: number;
  status: 'TODO' | 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED' | 'CANCELLED';
  category?: string;
  goal_id?: string;
  goal_title?: string;
  documents: TaskDocumentRef[];
  created_at: string;
  updated_at: string;
}

export interface GoalItem {
  id: string;
  user_id: string;
  title: string;
  description?: string;
  deadline?: string;
  importance: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'ACTIVE' | 'IN_PROGRESS' | 'ACHIEVED' | 'CANCELLED';
  progress: number;
  task_count: number;
  completed_task_count: number;
  created_at: string;
  updated_at: string;
}

export interface ActionPlanItem {
  id: string;
  plan_id: string;
  task_id?: string;
  goal_id?: string;
  priority: number;
  priority_label: string;
  action: string;
  reason: string;
  estimated_time: string;
  estimated_minutes: number;
  evidence: string;
  confidence: number;
  confidence_level: string;
  is_completed: boolean;
}

export interface ActionPlan {
  id: string;
  user_id: string;
  query: string;
  summary: string;
  total_estimated_minutes: number;
  available_minutes_constraint: number;
  user_context_snapshot: Record<string, any>;
  status: string;
  items: ActionPlanItem[];
  created_at: string;
  updated_at: string;
}

export interface ActionPlanRequest {
  query?: string;
  available_minutes?: number;
  focus_areas?: string[];
  constraints?: Record<string, any>;
}

export interface DecisionOptionItem {
  id: string;
  decision_id: string;
  title: string;
  description?: string;
  match_score?: number;
  effort_estimate?: string;
  created_at: string;
  updated_at: string;
}

export interface DecisionGoalRef {
  id: string;
  title: string;
  importance: string;
}

export interface OptionAnalysisItem {
  option_id: string;
  option_title: string;
  match: number;
  strengths: string[];
  weaknesses: string[];
  gaps: string[];
  constraints: string[];
  goal_alignment: string;
  evidence: string[];
  confidence: number;
  recommendation: string;
}

export interface DecisionAnalysisResponse {
  decision_id: string;
  recommendation: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  reasoning_summary: string;
  top_option_id?: string;
  options_analysis: OptionAnalysisItem[];
  created_at: string;
}

export interface DecisionItem {
  id: string;
  user_id: string;
  title: string;
  question: string;
  context_description?: string;
  deadline?: string;
  constraints: string[];
  status: 'DRAFT' | 'ANALYZED' | 'DECIDED' | 'ARCHIVED';
  selected_option_id?: string;
  goals: DecisionGoalRef[];
  options: DecisionOptionItem[];
  latest_analysis?: DecisionAnalysisResponse;
  created_at: string;
  updated_at: string;
}

export interface DecisionCreate {
  title: string;
  question: string;
  context_description?: string;
  deadline?: string;
  constraints: string[];
  goal_ids: string[];
  options: {
    title: string;
    description?: string;
    effort_estimate?: string;
  }[];
}

export interface SimulationComparisonItem {
  category: string;
  title: string;
  baseline_value: any;
  scenario_value: any;
  difference: string;
  reason: string;
}

export interface ScenarioSimulationResponse {
  scenario_id: string;
  scenario_name: string;
  baseline_scenario_id?: string;
  baseline: Record<string, any>;
  scenario: Record<string, any>;
  differences: SimulationComparisonItem[];
  reasons: string[];
  evidence: string[];
  confidence: number;
  confidence_level: string;
  created_at: string;
}

export interface ScenarioItem {
  id: string;
  user_id?: string;
  decision_id?: string;
  name: string;
  is_baseline: boolean;
  description?: string;
  parameters: Record<string, any>;
  simulation_result?: ScenarioSimulationResponse;
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreate {
  name: string;
  description?: string;
  decision_id?: string;
  is_baseline?: boolean;
  parameters: Record<string, any>;
}

export interface EvidenceExploreRequest {
  claim: string;
  collection_id?: string;
  top_k?: number;
  relevance_threshold?: number;
}

export interface EvidenceItem {
  id: string;
  claim: string;
  document_id?: string;
  source_filename: string;
  page_number?: number;
  chunk_index?: number;
  chunk_id?: string;
  chunk_text: string;
  relevance: number;
  reasoning: string;
  confidence: number;
  uncertainty: number;
  uncertainty_reasons: string[];
  stance: 'SUPPORTS' | 'CONTRADICTS' | 'NEUTRAL';
}

export interface ConflictSourceDetail {
  document_name: string;
  document_id?: string;
  page_number?: number;
  chunk_index?: number;
  chunk_text: string;
  assertion: string;
}

export interface EvidenceConflictItem {
  topic: string;
  source_a: ConflictSourceDetail;
  source_b: ConflictSourceDetail;
  discrepancy_explanation: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  suggested_resolution?: string;
}

export interface EvidenceExploreResponse {
  investigation_id: string;
  claim: string;
  status: 'VERIFIED_SUPPORT' | 'CONFLICT_DETECTED' | 'CONTRADICTED' | 'INSUFFICIENT_EVIDENCE';
  has_sufficient_evidence: boolean;
  conflict_detected: boolean;
  confidence: number;
  uncertainty: number;
  uncertainty_level: 'LOW' | 'MEDIUM' | 'HIGH';
  reasoning_summary: string;
  evidence_items: EvidenceItem[];
  conflicts: EvidenceConflictItem[];
  collection_id?: string;
  total_sources_evaluated: number;
  created_at: string;
}

export interface EvidenceInvestigationSummary {
  id: string;
  claim: string;
  status: 'VERIFIED_SUPPORT' | 'CONFLICT_DETECTED' | 'CONTRADICTED' | 'INSUFFICIENT_EVIDENCE';
  conflict_detected: boolean;
  confidence: number;
  uncertainty: number;
  uncertainty_level: 'LOW' | 'MEDIUM' | 'HIGH';
  sources_count: number;
  created_at: string;
}

export interface ActivityLogItem {
  id: string;
  user_id?: string;
  entity_type: string;
  entity_id?: string;
  action: string;
  details?: string;
  created_at: string;
}

export interface ActivityStats {
  total_events: number;
  by_entity_type: Record<string, number>;
  by_action: Record<string, number>;
}

export interface SettingsItem {
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
  embedding_backend: string;
  embedding_model: string;
  database_type: string;
  database_path: string;
  vector_store_type: string;
  vector_store_path: string;
  chunk_size: number;
  chunk_overlap: number;
  default_top_k: number;
  default_relevance_threshold: number;
  version: string;
  environment: string;
}

export interface SettingsUpdatePayload {
  default_top_k?: number;
  default_relevance_threshold?: number;
  gemini_api_key?: string;
}

export interface DashboardStats {
  collections_count: number;
  documents_count: number;
  chunks_count: number;
  tasks_total: number;
  tasks_completed: number;
  tasks_pending: number;
  tasks_urgent: number;
  goals_total: number;
  goals_active: number;
  goals_achieved: number;
  goals_average_progress: number;
  decisions_total: number;
  decisions_analyzed: number;
  decisions_decided: number;
  scenarios_total: number;
  evidence_investigations_total: number;
  conflicts_detected_total: number;
  latest_action_plan_summary?: string;
  latest_action_plan_time?: string;
  recent_activities: ActivityLogItem[];
  system_status: string;
}

export type NavTab =
  | 'dashboard'
  | 'knowledge'
  | 'rag'
  | 'planner'
  | 'tasks'
  | 'goals'
  | 'decisions'
  | 'scenarios'
  | 'evidence'
  | 'history'
  | 'settings';

export interface UserContextProfile {
  id: string;
  email: string;
  full_name?: string;
  preferences: Record<string, any>;
  context: Record<string, any>;
}
