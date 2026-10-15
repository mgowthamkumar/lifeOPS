import type {
  HealthResponse,
  Collection,
  DocumentItem,
  DocumentDetail,
  RAGQueryResponse,
  RAGConfig,
  TaskItem,
  GoalItem,
  ActionPlan,
  ActionPlanRequest,
  DecisionItem,
  DecisionCreate,
  DecisionAnalysisResponse,
  DecisionOptionItem,
  ScenarioItem,
  ScenarioCreate,
  ScenarioSimulationResponse,
  EvidenceExploreRequest,
  EvidenceExploreResponse,
  EvidenceInvestigationSummary,
  EvidenceConflictItem,
  ActivityLogItem,
  ActivityStats,
  SettingsItem,
  SettingsUpdatePayload,
  DashboardStats,
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

  // Tasks
  async getTasks(filters?: {
    status?: string;
    priority?: string;
    goalId?: string;
    category?: string;
  }): Promise<TaskItem[]> {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status_filter', filters.status);
    if (filters?.priority) params.append('priority_filter', filters.priority);
    if (filters?.goalId) params.append('goal_id', filters.goalId);
    if (filters?.category) params.append('category', filters.category);

    const url = `/api/tasks${params.toString() ? `?${params.toString()}` : ''}`;
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load tasks: ${response.status}`);
    }
    return response.json();
  },

  async createTask(data: {
    title: string;
    description?: string;
    deadline?: string;
    priority?: string;
    estimated_duration_minutes?: number;
    status?: string;
    category?: string;
    goal_id?: string;
    document_ids?: string[];
  }): Promise<TaskItem> {
    const response = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create task: ${response.status}`);
    }
    return response.json();
  },

  async updateTask(
    id: string,
    data: {
      title?: string;
      description?: string;
      deadline?: string;
      priority?: string;
      estimated_duration_minutes?: number;
      status?: string;
      category?: string;
      goal_id?: string;
      document_ids?: string[];
    }
  ): Promise<TaskItem> {
    const response = await fetch(`/api/tasks/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update task: ${response.status}`);
    }
    return response.json();
  },

  async toggleTaskComplete(id: string): Promise<TaskItem> {
    const response = await fetch(`/api/tasks/${id}/complete`, {
      method: 'PATCH',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to toggle task completion: ${response.status}`);
    }
    return response.json();
  },

  async deleteTask(id: string): Promise<void> {
    const response = await fetch(`/api/tasks/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete task: ${response.status}`);
    }
  },

  // Goals
  async getGoals(statusFilter?: string): Promise<GoalItem[]> {
    const url = statusFilter
      ? `/api/goals?status_filter=${encodeURIComponent(statusFilter)}`
      : '/api/goals';
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load goals: ${response.status}`);
    }
    return response.json();
  },

  async createGoal(data: {
    title: string;
    description?: string;
    deadline?: string;
    importance?: string;
    status?: string;
    progress?: number;
  }): Promise<GoalItem> {
    const response = await fetch('/api/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create goal: ${response.status}`);
    }
    return response.json();
  },

  async updateGoal(
    id: string,
    data: {
      title?: string;
      description?: string;
      deadline?: string;
      importance?: string;
      status?: string;
      progress?: number;
    }
  ): Promise<GoalItem> {
    const response = await fetch(`/api/goals/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update goal: ${response.status}`);
    }
    return response.json();
  },

  async deleteGoal(id: string): Promise<void> {
    const response = await fetch(`/api/goals/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete goal: ${response.status}`);
    }
  },

  // Action Planner
  async generateActionPlan(data: ActionPlanRequest): Promise<ActionPlan> {
    const response = await fetch('/api/action-planner/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to generate action plan: ${response.status}`);
    }
    return response.json();
  },

  async getLatestActionPlan(): Promise<ActionPlan | null> {
    const response = await fetch('/api/action-planner/latest', {
      headers: { 'Accept': 'application/json' },
    });
    if (response.status === 404) {
      return null;
    }
    if (!response.ok) {
      throw new Error(`Failed to load latest action plan: ${response.status}`);
    }
    return response.json();
  },

  async getActionPlanHistory(limit: number = 20): Promise<ActionPlan[]> {
    const response = await fetch(`/api/action-planner/history?limit=${limit}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load action plan history: ${response.status}`);
    }
    return response.json();
  },

  async getActionPlanById(id: string): Promise<ActionPlan> {
    const response = await fetch(`/api/action-planner/${id}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load action plan: ${response.status}`);
    }
    return response.json();
  },

  // Decisions & Decision Intelligence
  async getDecisions(status?: string): Promise<DecisionItem[]> {
    const url = status ? `/api/decisions?status=${encodeURIComponent(status)}` : '/api/decisions';
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load decisions: ${response.status}`);
    }
    return response.json();
  },

  async getDecision(id: string): Promise<DecisionItem> {
    const response = await fetch(`/api/decisions/${id}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load decision: ${response.status}`);
    }
    return response.json();
  },

  async createDecision(data: DecisionCreate): Promise<DecisionItem> {
    const response = await fetch('/api/decisions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create decision: ${response.status}`);
    }
    return response.json();
  },

  async updateDecision(
    id: string,
    data: {
      title?: string;
      question?: string;
      context_description?: string;
      deadline?: string;
      constraints?: string[];
      goal_ids?: string[];
      status?: string;
    }
  ): Promise<DecisionItem> {
    const response = await fetch(`/api/decisions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update decision: ${response.status}`);
    }
    return response.json();
  },

  async deleteDecision(id: string): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`/api/decisions/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete decision: ${response.status}`);
    }
    return response.json();
  },

  async addDecisionOption(
    decisionId: string,
    data: { title: string; description?: string; effort_estimate?: string }
  ): Promise<DecisionOptionItem> {
    const response = await fetch(`/api/decisions/${decisionId}/options`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to add option: ${response.status}`);
    }
    return response.json();
  },

  async deleteDecisionOption(
    decisionId: string,
    optionId: string
  ): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`/api/decisions/${decisionId}/options/${optionId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete option: ${response.status}`);
    }
    return response.json();
  },

  async analyzeDecision(decisionId: string): Promise<DecisionAnalysisResponse> {
    const response = await fetch(`/api/decisions/${decisionId}/analyze`, {
      method: 'POST',
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to analyze decision: ${response.status}`);
    }
    return response.json();
  },

  async selectDecisionOption(
    decisionId: string,
    optionId: string
  ): Promise<DecisionItem> {
    const response = await fetch(`/api/decisions/${decisionId}/select-option`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ option_id: optionId }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to select option: ${response.status}`);
    }
    return response.json();
  },

  // What-If Scenarios & Simulation
  async getScenarios(decisionId?: string): Promise<ScenarioItem[]> {
    const url = decisionId ? `/api/scenarios?decision_id=${encodeURIComponent(decisionId)}` : '/api/scenarios';
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load scenarios: ${response.status}`);
    }
    return response.json();
  },

  async getBaselineScenario(decisionId?: string): Promise<ScenarioItem> {
    const url = decisionId ? `/api/scenarios/baseline?decision_id=${encodeURIComponent(decisionId)}` : '/api/scenarios/baseline';
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load baseline scenario: ${response.status}`);
    }
    return response.json();
  },

  async getScenario(id: string): Promise<ScenarioItem> {
    const response = await fetch(`/api/scenarios/${id}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load scenario: ${response.status}`);
    }
    return response.json();
  },

  async createScenario(data: ScenarioCreate): Promise<ScenarioItem> {
    const response = await fetch('/api/scenarios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create scenario: ${response.status}`);
    }
    return response.json();
  },

  async updateScenario(id: string, data: Partial<ScenarioCreate>): Promise<ScenarioItem> {
    const response = await fetch(`/api/scenarios/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update scenario: ${response.status}`);
    }
    return response.json();
  },

  async deleteScenario(id: string): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`/api/scenarios/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete scenario: ${response.status}`);
    }
    return response.json();
  },

  async simulateScenario(
    id: string,
    payload?: { baseline_scenario_id?: string; parameter_overrides?: Record<string, any> }
  ): Promise<ScenarioSimulationResponse> {
    const response = await fetch(`/api/scenarios/${id}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to run simulation: ${response.status}`);
    }
    return response.json();
  },

  // Evidence Explorer
  async exploreEvidence(data: EvidenceExploreRequest): Promise<EvidenceExploreResponse> {
    const response = await fetch('/api/evidence/explore', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to explore evidence: ${response.status}`);
    }
    return response.json();
  },

  async getEvidenceInvestigations(collectionId?: string): Promise<EvidenceInvestigationSummary[]> {
    const url = collectionId
      ? `/api/evidence?collection_id=${encodeURIComponent(collectionId)}`
      : '/api/evidence';
    const response = await fetch(url, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load evidence investigations: ${response.status}`);
    }
    return response.json();
  },

  async getEvidenceConflicts(): Promise<EvidenceConflictItem[]> {
    const response = await fetch('/api/evidence/conflicts', {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load detected conflicts: ${response.status}`);
    }
    return response.json();
  },

  async getEvidenceInvestigation(id: string): Promise<EvidenceExploreResponse> {
    const response = await fetch(`/api/evidence/${id}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load evidence investigation: ${response.status}`);
    }
    return response.json();
  },

  async deleteEvidenceInvestigation(id: string): Promise<{ success: boolean; message?: string }> {
    const response = await fetch(`/api/evidence/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to delete evidence investigation: ${response.status}`);
    }
    return response.json();
  },

  // Dashboard Telemetry
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await fetch('/api/dashboard/stats', {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load dashboard statistics: ${response.status}`);
    }
    return response.json();
  },

  // History / Activity Logs
  async getHistory(entityType?: string, limit: number = 50): Promise<ActivityLogItem[]> {
    const params = new URLSearchParams();
    if (entityType && entityType !== 'ALL') params.append('entity_type', entityType);
    params.append('limit', limit.toString());

    const response = await fetch(`/api/history?${params.toString()}`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load activity history: ${response.status}`);
    }
    return response.json();
  },

  async getHistoryStats(): Promise<ActivityStats> {
    const response = await fetch('/api/history/stats', {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load activity stats: ${response.status}`);
    }
    return response.json();
  },

  async clearHistory(): Promise<{ message: string; deleted_count: number }> {
    const response = await fetch('/api/history', {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error(`Failed to clear activity history: ${response.status}`);
    }
    return response.json();
  },

  // Settings
  async getSettings(): Promise<SettingsItem> {
    const response = await fetch('/api/settings', {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to load system settings: ${response.status}`);
    }
    return response.json();
  },

  async updateSettings(data: SettingsUpdatePayload): Promise<SettingsItem> {
    const response = await fetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update settings: ${response.status}`);
    }
    return response.json();
  },

  async verifyEngine(): Promise<{ status: string; llm_configured: boolean; vector_store_connected: boolean; message: string }> {
    const response = await fetch('/api/settings/verify-engine', {
      method: 'POST',
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to verify AI engine: ${response.status}`);
    }
    return response.json();
  },

  async getUserProfile(): Promise<import('../types').UserContextProfile> {
    const response = await fetch('/api/users/me', {
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to get user profile: ${response.status}`);
    }
    return response.json();
  },

  async updateUserContext(data: {
    full_name?: string;
    preferences?: Record<string, any>;
    context?: Record<string, any>;
  }): Promise<import('../types').UserContextProfile> {
    const response = await fetch('/api/users/context', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update user context: ${response.status}`);
    }
    return response.json();
  },
};
