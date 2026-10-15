import type {
  HealthResponse,
  Collection,
  DocumentItem,
  DocumentDetail,
  RAGQueryResponse,
  RAGConfig,
} from '../types';

export const apiService = {
  async getHealth(): Promise<HealthResponse> {
    const response = await fetch('/api/health', {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`API health check error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  },

  // Collections
  async getCollections(): Promise<Collection[]> {
    const response = await fetch('/api/collections', {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load collections: ${response.status}`);
    }
    return response.json();
  },

  async createCollection(name: string, description?: string): Promise<Collection> {
    const response = await fetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create collection: ${response.status}`);
    }
    return response.json();
  },

  async deleteCollection(id: string): Promise<void> {
    const response = await fetch(`/api/collections/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete collection: ${response.status}`);
    }
  },

  // Documents
  async getDocuments(collectionId?: string): Promise<DocumentItem[]> {
    const url = collectionId
      ? `/api/documents?collection_id=${encodeURIComponent(collectionId)}`
      : '/api/documents';
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load documents: ${response.status}`);
    }
    return response.json();
  },

  async getDocument(id: string): Promise<DocumentDetail> {
    const response = await fetch(`/api/documents/${id}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load document details: ${response.status}`);
    }
    return response.json();
  },

  async uploadDocument(collectionId: string, file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('collection_id', collectionId);
    formData.append('file', file);

    const response = await fetch('/api/documents/upload', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to upload document: ${response.status}`);
    }
    return response.json();
  },

  async reprocessDocument(id: string): Promise<DocumentItem> {
    const response = await fetch(`/api/documents/${id}/reprocess`, {
      method: 'POST',
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to reprocess document: ${response.status}`);
    }
    return response.json();
  },

  async updateDocument(id: string, file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`/api/documents/${id}/update`, {
      method: 'PUT',
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update document: ${response.status}`);
    }
    return response.json();
  },

  async deleteDocument(id: string): Promise<void> {
    const response = await fetch(`/api/documents/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete document: ${response.status}`);
    }
  },

  // RAG Decision Intelligence
  async queryRAG(
    collectionId: string,
    question: string,
    topK: number = 5,
    relevanceThreshold: number = 0.35
  ): Promise<RAGQueryResponse> {
    const response = await fetch('/api/rag/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        collection_id: collectionId,
        question,
        top_k: topK,
        relevance_threshold: relevanceThreshold,
      }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `RAG query failed: ${response.status}`);
    }
    return response.json();
  },

  async getRAGRecentEvidence(limit: number = 10): Promise<any[]> {
    const response = await fetch(`/api/rag/evidence?limit=${limit}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load evidence: ${response.status}`);
    }
    return response.json();
  },

  async getRAGConfig(): Promise<RAGConfig> {
    const response = await fetch('/api/rag/config', {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load RAG config: ${response.status}`);
    }
    return response.json();
  },
};
