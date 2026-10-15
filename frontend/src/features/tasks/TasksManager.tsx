import React, { useState, useEffect } from 'react';
import {
  ListTodo,
  Plus,
  Trash2,
  Edit2,
  CheckCircle2,
  Circle,
  Clock,
  Calendar,
  AlertTriangle,
  RefreshCw,
  X,
  Target,
  FileText,
  Tag,
  Search,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type { TaskItem, GoalItem, DocumentItem } from '../../types';

interface TasksManagerProps {
  initialGoalId?: string;
  onClearGoalFilter?: () => void;
}

export const TasksManager: React.FC<TasksManagerProps> = ({
  initialGoalId,
  onClearGoalFilter,
}) => {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [goals, setGoals] = useState<GoalItem[]>([]);
  const [availableDocs, setAvailableDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [selectedGoalId, setSelectedGoalId] = useState<string>(initialGoalId || 'ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Modal State
  const [showModal, setShowModal] = useState<boolean>(false);
  const [editingTask, setEditingTask] = useState<TaskItem | null>(null);
  const [formTitle, setFormTitle] = useState<string>('');
  const [formDesc, setFormDesc] = useState<string>('');
  const [formDeadline, setFormDeadline] = useState<string>('');
  const [formPriority, setFormPriority] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'>('MEDIUM');
  const [formDuration, setFormDuration] = useState<number>(30);
  const [formStatus, setFormStatus] = useState<'TODO' | 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED' | 'CANCELLED'>('TODO');
  const [formCategory, setFormCategory] = useState<string>('General');
  const [formGoalId, setFormGoalId] = useState<string>('');
  const [formDocIds, setFormDocIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState<boolean>(false);

  useEffect(() => {
    if (initialGoalId) {
      setSelectedGoalId(initialGoalId);
    }
  }, [initialGoalId]);

  useEffect(() => {
    loadAuxiliaryData();
  }, []);

  useEffect(() => {
    loadTasks();
  }, [statusFilter, priorityFilter, selectedGoalId]);

  const loadAuxiliaryData = async () => {
    try {
      const [goalsData, docsData] = await Promise.all([
        apiService.getGoals(),
        apiService.getDocuments(),
      ]);
      setGoals(goalsData);
      setAvailableDocs(docsData);
    } catch (err: any) {
      console.error('Failed to load auxiliary data:', err);
    }
  };

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      const filters: any = {};
      if (statusFilter !== 'ALL') filters.status = statusFilter;
      if (priorityFilter !== 'ALL') filters.priority = priorityFilter;
      if (selectedGoalId !== 'ALL') filters.goalId = selectedGoalId;

      const data = await apiService.getTasks(filters);
      setTasks(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load tasks.');
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingTask(null);
    setFormTitle('');
    setFormDesc('');
    setFormDeadline('');
    setFormPriority('MEDIUM');
    setFormDuration(30);
    setFormStatus('TODO');
    setFormCategory('General');
    setFormGoalId(selectedGoalId !== 'ALL' ? selectedGoalId : '');
    setFormDocIds([]);
    setShowModal(true);
  };

  const openEditModal = (task: TaskItem) => {
    setEditingTask(task);
    setFormTitle(task.title);
    setFormDesc(task.description || '');
    setFormDeadline(task.deadline ? task.deadline.slice(0, 10) : '');
    setFormPriority(task.priority);
    setFormDuration(task.estimated_duration_minutes || 30);
    setFormStatus(task.status);
    setFormCategory(task.category || 'General');
    setFormGoalId(task.goal_id || '');
    setFormDocIds(task.documents ? task.documents.map((d) => d.id) : []);
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) return;

    try {
      setSubmitting(true);
      setError(null);
      const payload: any = {
        title: formTitle.trim(),
        description: formDesc.trim() || undefined,
        deadline: formDeadline ? new Date(formDeadline).toISOString() : undefined,
        priority: formPriority,
        estimated_duration_minutes: Number(formDuration) || 0,
        status: formStatus,
        category: formCategory.trim() || undefined,
        goal_id: formGoalId || undefined,
        document_ids: formDocIds,
      };

      if (editingTask) {
        await apiService.updateTask(editingTask.id, payload);
      } else {
        await apiService.createTask(payload);
      }

      setShowModal(false);
      await loadTasks();
      // Reload goals to update task counts and progress
      const refreshedGoals = await apiService.getGoals();
      setGoals(refreshedGoals);
    } catch (err: any) {
      setError(err.message || 'Failed to save task.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleComplete = async (taskId: string) => {
    try {
      setError(null);
      await apiService.toggleTaskComplete(taskId);
      await loadTasks();
      const refreshedGoals = await apiService.getGoals();
      setGoals(refreshedGoals);
    } catch (err: any) {
      setError(err.message || 'Failed to toggle task status.');
    }
  };

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`Are you sure you want to delete task "${title}"?`)) return;
    try {
      setError(null);
      await apiService.deleteTask(id);
      await loadTasks();
      const refreshedGoals = await apiService.getGoals();
      setGoals(refreshedGoals);
    } catch (err: any) {
      setError(err.message || 'Failed to delete task.');
    }
  };

  const toggleDocSelection = (docId: string) => {
    setFormDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const getPriorityColor = (p: string) => {
    switch (p) {
      case 'URGENT':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'HIGH':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'MEDIUM':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'COMPLETED':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'IN_PROGRESS':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      case 'BLOCKED':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'CANCELLED':
        return 'bg-slate-800 text-slate-500 border-slate-700';
      default:
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
    }
  };

  const formatDuration = (mins: number) => {
    if (!mins || mins <= 0) return '0m';
    if (mins < 60) return `${mins}m`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  };

  const filteredTasks = tasks.filter((t) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      t.title.toLowerCase().includes(q) ||
      (t.description && t.description.toLowerCase().includes(q)) ||
      (t.category && t.category.toLowerCase().includes(q)) ||
      (t.goal_title && t.goal_title.toLowerCase().includes(q))
    );
  });

  const completedCount = tasks.filter((t) => t.status === 'COMPLETED').length;
  const inProgressCount = tasks.filter((t) => t.status === 'IN_PROGRESS').length;
  const urgentCount = tasks.filter((t) => t.priority === 'URGENT' && t.status !== 'COMPLETED').length;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg">
              <ListTodo className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Action Tasks Workspace
            </h1>
          </div>
          <p className="text-slate-400 text-sm">
            Execute tangible tasks linked directly to strategic goals and knowledge base documents.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={loadTasks}
            title="Refresh Tasks"
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-colors border border-slate-700"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
          <button
            type="button"
            onClick={openCreateModal}
            className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white font-medium px-4 py-2.5 rounded-xl shadow-lg transition-all text-sm"
          >
            <Plus className="w-4 h-4" />
            Create Task
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Metrics Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Total Tasks</div>
          <div className="text-2xl font-bold text-white mt-1">{tasks.length}</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">Completed</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{completedCount}</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-cyan-400">In Progress</div>
          <div className="text-2xl font-bold text-cyan-400 mt-1">{inProgressCount}</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-red-400">Urgent Pending</div>
          <div className="text-2xl font-bold text-red-400 mt-1">{urgentCount}</div>
        </div>
      </div>

      {/* Controls: Search & Filters */}
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between bg-slate-900/80 border border-slate-800 p-4 rounded-xl">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by title, category, goal..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Status Filter */}
          <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-xl px-2 py-1 text-xs">
            <span className="text-slate-500 font-medium px-1">Status:</span>
            {['ALL', 'TODO', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED'].map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setStatusFilter(st)}
                className={`px-2 py-1 rounded-lg font-medium transition-all ${
                  statusFilter === st
                    ? 'bg-cyan-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {st.replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Priority Filter */}
          <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-xl px-2 py-1 text-xs">
            <span className="text-slate-500 font-medium px-1">Priority:</span>
            {['ALL', 'URGENT', 'HIGH', 'MEDIUM', 'LOW'].map((pr) => (
              <button
                key={pr}
                type="button"
                onClick={() => setPriorityFilter(pr)}
                className={`px-2 py-1 rounded-lg font-medium transition-all ${
                  priorityFilter === pr
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {pr}
              </button>
            ))}
          </div>

          {/* Goal Filter */}
          <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs">
            <Target className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={selectedGoalId}
              onChange={(e) => setSelectedGoalId(e.target.value)}
              className="bg-transparent text-slate-300 focus:outline-none text-xs cursor-pointer"
            >
              <option value="ALL">All Goals</option>
              {goals.map((g) => (
                <option key={g.id} value={g.id} className="bg-slate-900 text-white">
                  {g.title}
                </option>
              ))}
            </select>
            {selectedGoalId !== 'ALL' && onClearGoalFilter && (
              <button
                type="button"
                onClick={() => {
                  setSelectedGoalId('ALL');
                  onClearGoalFilter();
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Task List */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 space-y-3">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-cyan-400" />
          <p className="text-sm">Loading action tasks...</p>
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="p-12 bg-slate-900/40 border border-slate-800 rounded-2xl text-center space-y-3">
          <ListTodo className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-white">No Tasks Found</h3>
          <p className="text-sm text-slate-400 max-w-sm mx-auto">
            {tasks.length === 0
              ? 'Start by creating your first task to take action on your strategic goals.'
              : 'No tasks match your current filter parameters.'}
          </p>
          <button
            type="button"
            onClick={openCreateModal}
            className="mt-2 inline-flex items-center gap-2 bg-cyan-600 text-white px-4 py-2 rounded-xl text-xs font-medium hover:bg-cyan-500"
          >
            <Plus className="w-3.5 h-3.5" /> Create Task
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((task) => {
            const isCompleted = task.status === 'COMPLETED';
            return (
              <div
                key={task.id}
                className={`group bg-slate-900 border rounded-2xl p-4 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  isCompleted
                    ? 'border-slate-800/60 opacity-75 bg-slate-900/40'
                    : 'border-slate-800 hover:border-slate-700/80 shadow-md'
                }`}
              >
                {/* Left: Completion Checkbox + Main Details */}
                <div className="flex items-start gap-3.5 flex-1 min-w-0">
                  <button
                    type="button"
                    onClick={() => handleToggleComplete(task.id)}
                    title={isCompleted ? 'Mark incomplete' : 'Mark completed'}
                    className={`mt-1 shrink-0 transition-colors ${
                      isCompleted ? 'text-emerald-400' : 'text-slate-500 hover:text-cyan-400'
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <Circle className="w-5 h-5" />
                    )}
                  </button>

                  <div className="flex-1 min-w-0 space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3
                        className={`font-semibold text-sm leading-snug break-words ${
                          isCompleted ? 'line-through text-slate-400' : 'text-white'
                        }`}
                      >
                        {task.title}
                      </h3>

                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getPriorityColor(
                          task.priority
                        )}`}
                      >
                        {task.priority}
                      </span>

                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${getStatusBadge(
                          task.status
                        )}`}
                      >
                        {task.status.replace('_', ' ')}
                      </span>

                      {task.category && (
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1">
                          <Tag className="w-2.5 h-2.5 text-cyan-400" />
                          {task.category}
                        </span>
                      )}
                    </div>

                    {task.description && (
                      <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                        {task.description}
                      </p>
                    )}

                    {/* Meta Row: Goal & Documents */}
                    <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-slate-400">
                      {task.goal_title && (
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-[11px]">
                          <Target className="w-3 h-3 text-indigo-400" />
                          <span>Goal: {task.goal_title}</span>
                        </div>
                      )}

                      {task.documents && task.documents.length > 0 && (
                        <div className="inline-flex items-center gap-1.5">
                          <FileText className="w-3 h-3 text-cyan-400" />
                          <span className="text-[11px] text-slate-300">
                            {task.documents.length} doc{task.documents.length > 1 ? 's' : ''}:
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {task.documents.map((doc) => (
                              <span
                                key={doc.id}
                                className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded border border-slate-700 truncate max-w-[130px]"
                                title={doc.filename}
                              >
                                {doc.filename}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Metrics & Actions */}
                <div className="flex items-center justify-between md:justify-end gap-4 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800/80">
                  <div className="flex items-center gap-3 text-xs text-slate-400">
                    <div className="flex items-center gap-1" title="Estimated Duration">
                      <Clock className="w-3.5 h-3.5 text-cyan-400" />
                      <span>{formatDuration(task.estimated_duration_minutes)}</span>
                    </div>

                    {task.deadline && (
                      <div className="flex items-center gap-1" title="Deadline">
                        <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                        <span>{new Date(task.deadline).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => openEditModal(task)}
                      title="Edit Task"
                      className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(task.id, task.title)}
                      title="Delete Task"
                      className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Task Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <ListTodo className="w-5 h-5 text-cyan-400" />
                <span>{editingTask ? 'Edit Action Task' : 'Create Action Task'}</span>
              </h2>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  Task Title *
                </label>
                <input
                  type="text"
                  required
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="e.g. Implement ChromaDB filtering service"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="Actionable steps, acceptance criteria, notes..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Priority
                  </label>
                  <select
                    value={formPriority}
                    onChange={(e: any) => setFormPriority(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="URGENT">URGENT</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Status
                  </label>
                  <select
                    value={formStatus}
                    onChange={(e: any) => setFormStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  >
                    <option value="TODO">TODO</option>
                    <option value="IN_PROGRESS">IN PROGRESS</option>
                    <option value="COMPLETED">COMPLETED</option>
                    <option value="BLOCKED">BLOCKED</option>
                    <option value="CANCELLED">CANCELLED</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Category
                  </label>
                  <input
                    type="text"
                    value={formCategory}
                    onChange={(e) => setFormCategory(e.target.value)}
                    placeholder="Work, Health, Dev..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Estimated Duration (Minutes)
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={5}
                    value={formDuration}
                    onChange={(e) => setFormDuration(parseInt(e.target.value) || 0)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Deadline
                  </label>
                  <input
                    type="date"
                    value={formDeadline}
                    onChange={(e) => setFormDeadline(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                  />
                </div>
              </div>

              {/* Goal Selector */}
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  Associate With Strategic Goal
                </label>
                <select
                  value={formGoalId}
                  onChange={(e) => setFormGoalId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="">(None - Standalone Task)</option>
                  {goals.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.title} [{g.importance} - {g.progress.toFixed(0)}%]
                    </option>
                  ))}
                </select>
              </div>

              {/* Document Multi-Select */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Link Knowledge Base Documents ({formDocIds.length} Selected)
                  </label>
                  {formDocIds.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setFormDocIds([])}
                      className="text-[11px] text-cyan-400 hover:text-cyan-300"
                    >
                      Clear Selection
                    </button>
                  )}
                </div>

                {availableDocs.length === 0 ? (
                  <p className="text-xs text-slate-500 bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                    No documents uploaded in knowledge base yet.
                  </p>
                ) : (
                  <div className="max-h-36 overflow-y-auto bg-slate-950 border border-slate-800 rounded-xl p-2 space-y-1">
                    {availableDocs.map((doc) => {
                      const isSelected = formDocIds.includes(doc.id);
                      return (
                        <div
                          key={doc.id}
                          onClick={() => toggleDocSelection(doc.id)}
                          className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-cyan-950/40 border border-cyan-800/60 text-cyan-300'
                              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                          }`}
                        >
                          <div className="flex items-center gap-2 truncate">
                            <FileText className={`w-3.5 h-3.5 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
                            <span className="truncate">{doc.filename}</span>
                          </div>
                          <span className="text-[10px] font-mono uppercase text-slate-500 shrink-0">
                            {doc.file_type}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Submit Buttons */}
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : editingTask ? 'Update Task' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
