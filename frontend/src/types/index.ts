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

export type NavTab =
  | 'dashboard'
  | 'knowledge'
  | 'rag'
  | 'tasks'
  | 'goals'
  | 'decisions'
  | 'scenarios'
  | 'evidence'
  | 'history'
  | 'settings';

