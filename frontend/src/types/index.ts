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

export type NavTab =
  | 'dashboard'
  | 'knowledge'
  | 'tasks'
  | 'goals'
  | 'decisions'
  | 'scenarios'
  | 'evidence'
  | 'history'
  | 'settings';
