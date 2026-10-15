import React, { useState, useEffect } from 'react';
import {
  Target,
  Plus,
  Trash2,
  Edit2,
  Calendar,
  AlertTriangle,
  RefreshCw,
  X,
  ListTodo,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type { GoalItem } from '../../types';

interface GoalsManagerProps {
  onSelectGoalForTasks?: (goalId: string) => void;
}

export const GoalsManager: React.FC<GoalsManagerProps> = ({ onSelectGoalForTasks }) => {
  const [goals, setGoals] = useState<GoalItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  // Modal State
  const [showModal, setShowModal] = useState<boolean>(false);
  const [editingGoal, setEditingGoal] = useState<GoalItem | null>(null);
  const [formTitle, setFormTitle] = useState<string>('');
  const [formDesc, setFormDesc] = useState<string>('');
  const [formDeadline, setFormDeadline] = useState<string>('');
  const [formImportance, setFormImportance] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'>('MEDIUM');
  const [formStatus, setFormStatus] = useState<'ACTIVE' | 'IN_PROGRESS' | 'ACHIEVED' | 'CANCELLED'>('ACTIVE');
  const [formProgress, setFormProgress] = useState<number>(0);
  const [submitting, setSubmitting] = useState<boolean>(false);

  useEffect(() => {
    loadGoals();
  }, [statusFilter]);

  const loadGoals = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getGoals(statusFilter === 'ALL' ? undefined : statusFilter);
      setGoals(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load goals.');
    } finally {
      setLoading(false);
    }
  };

  const openCreateModal = () => {
    setEditingGoal(null);
    setFormTitle('');
    setFormDesc('');
    setFormDeadline('');
    setFormImportance('MEDIUM');
    setFormStatus('ACTIVE');
    setFormProgress(0);
    setShowModal(true);
  };

  const openEditModal = (goal: GoalItem) => {
    setEditingGoal(goal);
    setFormTitle(goal.title);
    setFormDesc(goal.description || '');
    setFormDeadline(goal.deadline ? goal.deadline.slice(0, 10) : '');
    setFormImportance(goal.importance);
    setFormStatus(goal.status);
    setFormProgress(goal.progress);
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) return;

    try {
      setSubmitting(true);
      setError(null);
      const payload = {
        title: formTitle.trim(),
        description: formDesc.trim() || undefined,
        deadline: formDeadline ? new Date(formDeadline).toISOString() : undefined,
        importance: formImportance,
        status: formStatus,
        progress: formProgress,
      };

      if (editingGoal) {
        await apiService.updateGoal(editingGoal.id, payload);
      } else {
        await apiService.createGoal(payload);
      }

      setShowModal(false);
      await loadGoals();
    } catch (err: any) {
      setError(err.message || 'Failed to save goal.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string, title: string) => {
    if (!confirm(`Are you sure you want to delete goal "${title}"? Associated tasks will be deleted.`)) return;
    try {
      setError(null);
      await apiService.deleteGoal(id);
      await loadGoals();
    } catch (err: any) {
      setError(err.message || 'Failed to delete goal.');
    }
  };

  const getImportanceColor = (imp: string) => {
    switch (imp) {
      case 'CRITICAL':
        return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'HIGH':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'MEDIUM':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getStatusColor = (st: string) => {
    switch (st) {
      case 'ACHIEVED':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'IN_PROGRESS':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
      case 'CANCELLED':
        return 'bg-slate-800 text-slate-500 border-slate-700';
      default:
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Target className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Strategic Goals Workspace
            </h1>
          </div>
          <p className="text-slate-400 text-sm">
            Define high-level milestones with automated progress tracking derived from task execution.
          </p>
        </div>

        <button
          type="button"
          onClick={openCreateModal}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2.5 rounded-xl shadow-lg transition-all text-sm shrink-0"
        >
          <Plus className="w-4 h-4" />
          Create New Goal
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        {['ALL', 'ACTIVE', 'IN_PROGRESS', 'ACHIEVED', 'CANCELLED'].map((st) => (
          <button
            key={st}
            type="button"
            onClick={() => setStatusFilter(st)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              statusFilter === st
                ? 'bg-indigo-600 text-white shadow-md'
                : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            {st.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Goals Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 space-y-3">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-400" />
          <p className="text-sm">Loading strategic goals...</p>
        </div>
      ) : goals.length === 0 ? (
        <div className="p-12 bg-slate-900/40 border border-slate-800 rounded-2xl text-center space-y-3">
          <Target className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-semibold text-white">No Goals Found</h3>
          <p className="text-sm text-slate-400 max-w-sm mx-auto">
            {statusFilter === 'ALL'
              ? 'Start by creating your first strategic goal to organize your tasks.'
              : `No goals found with status "${statusFilter}".`}
          </p>
          <button
            type="button"
            onClick={openCreateModal}
            className="mt-2 inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl text-xs font-medium hover:bg-indigo-500"
          >
            <Plus className="w-3.5 h-3.5" /> Create Goal
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {goals.map((goal) => (
            <div
              key={goal.id}
              className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 shadow-lg flex flex-col justify-between space-y-4 transition-all"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getImportanceColor(
                      goal.importance
                    )}`}
                  >
                    {goal.importance} IMPORTANCE
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() => openEditModal(goal)}
                      title="Edit Goal"
                      className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(goal.id, goal.title)}
                      title="Delete Goal"
                      className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <h3 className="font-bold text-white text-base leading-snug line-clamp-2">
                  {goal.title}
                </h3>
                {goal.description && (
                  <p className="text-slate-400 text-xs mt-1.5 line-clamp-2 leading-relaxed">
                    {goal.description}
                  </p>
                )}
              </div>

              {/* Progress & Stats */}
              <div className="space-y-3 pt-3 border-t border-slate-800/80">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Completion</span>
                    <span className="font-bold text-white">{goal.progress.toFixed(0)}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        goal.progress >= 100
                          ? 'bg-emerald-500'
                          : goal.progress > 50
                          ? 'bg-indigo-500'
                          : 'bg-cyan-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, goal.progress))}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <ListTodo className="w-3.5 h-3.5 text-indigo-400" />
                    <span>
                      {goal.completed_task_count}/{goal.task_count} Tasks
                    </span>
                  </div>

                  {goal.deadline ? (
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{new Date(goal.deadline).toLocaleDateString()}</span>
                    </div>
                  ) : (
                    <span className="text-[11px] text-slate-500">No deadline</span>
                  )}
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${getStatusColor(
                      goal.status
                    )}`}
                  >
                    {goal.status}
                  </span>

                  {onSelectGoalForTasks && (
                    <button
                      type="button"
                      onClick={() => onSelectGoalForTasks(goal.id)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                    >
                      View Tasks →
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Goal Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white">
                {editingGoal ? 'Edit Strategic Goal' : 'Create New Goal'}
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
                  Goal Title *
                </label>
                <input
                  type="text"
                  required
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="e.g. Master Full-Stack AI Engineering"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="Details, key outcomes, and milestone metrics..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Importance
                  </label>
                  <select
                    value={formImportance}
                    onChange={(e: any) => setFormImportance(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Status
                  </label>
                  <select
                    value={formStatus}
                    onChange={(e: any) => setFormStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="IN_PROGRESS">IN PROGRESS</option>
                    <option value="ACHIEVED">ACHIEVED</option>
                    <option value="CANCELLED">CANCELLED</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Target Deadline
                  </label>
                  <input
                    type="date"
                    value={formDeadline}
                    onChange={(e) => setFormDeadline(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Initial Progress ({formProgress}%)
                  </label>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={formProgress}
                    onChange={(e) => setFormProgress(parseFloat(e.target.value))}
                    className="w-full accent-indigo-500 mt-2"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg disabled:opacity-50"
                >
                  {submitting ? 'Saving...' : editingGoal ? 'Update Goal' : 'Create Goal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
