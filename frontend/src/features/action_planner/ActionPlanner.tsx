import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Clock,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileText,
  History,
  Send,
  Zap,
  Sliders,
  ShieldCheck,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type { ActionPlan } from '../../types';

export const ActionPlanner: React.FC = () => {
  const [query, setQuery] = useState<string>('What should I do today?');
  const [availableMinutes, setAvailableMinutes] = useState<number>(240);
  const [focusAreas, setFocusAreas] = useState<string[]>(['Engineering']);
  const [focusInput, setFocusInput] = useState<string>('');
  const [currentPlan, setCurrentPlan] = useState<ActionPlan | null>(null);
  const [planHistory, setPlanHistory] = useState<ActionPlan[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState<boolean>(false);

  useEffect(() => {
    loadLatestPlan();
    loadHistory();
  }, []);

  const loadLatestPlan = async () => {
    try {
      setLoading(true);
      setError(null);
      const latest = await apiService.getLatestActionPlan();
      if (latest) {
        setCurrentPlan(latest);
      }
    } catch (err: any) {
      console.warn('No active plan or failed to load:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    try {
      setHistoryLoading(true);
      const history = await apiService.getActionPlanHistory(15);
      setPlanHistory(history);
    } catch (err: any) {
      console.warn('Failed to load plan history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleGeneratePlan = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      setError(null);
      const plan = await apiService.generateActionPlan({
        query: query.trim(),
        available_minutes: availableMinutes,
        focus_areas: focusAreas,
      });
      setCurrentPlan(plan);
      await loadHistory();
    } catch (err: any) {
      setError(err.message || 'Failed to generate action plan.');
    } finally {
      setLoading(false);
    }
  };

  const addFocusArea = () => {
    const val = focusInput.trim();
    if (val && !focusAreas.includes(val)) {
      setFocusAreas([...focusAreas, val]);
      setFocusInput('');
    }
  };

  const removeFocusArea = (tag: string) => {
    setFocusAreas(focusAreas.filter((f) => f !== tag));
  };

  const getPriorityStyle = (label: string) => {
    const upper = label.toUpperCase();
    if (upper.includes('URGENT')) {
      return 'bg-red-500/10 text-red-400 border-red-500/30';
    }
    if (upper.includes('HIGH')) {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
    if (upper.includes('MEDIUM')) {
      return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
    }
    return 'bg-slate-800 text-slate-400 border-slate-700';
  };

  const quickPrompts = [
    'What should I do today?',
    'Prioritize my high-impact engineering work',
    'What urgent items need focus this morning?',
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-[#10192e] to-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 bg-gradient-to-tr from-purple-500 to-indigo-600 text-white rounded-lg shadow-md shadow-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              AI Action Planner
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/30">
                Grounded Reasoning
              </span>
            </h1>
          </div>
          <p className="text-slate-400 text-sm max-w-2xl">
            Synthesizes real tasks, strategic goals, deadlines, user constraints, and RAG document evidence into a deterministic, explainable daily action plan.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => setShowHistory(!showHistory)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium border transition-colors ${
              showHistory
                ? 'bg-purple-950/40 border-purple-800 text-purple-300'
                : 'bg-slate-900 border-slate-800 text-slate-300 hover:text-white'
            }`}
          >
            <History className="w-4 h-4" />
            <span>Plan History ({planHistory.length})</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Query Bar and Constraint Controls */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
        <form onSubmit={handleGeneratePlan} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              Planning Query / Focus Instruction
            </label>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. What should I do today?"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-5 py-2.5 rounded-xl shadow-lg transition-all text-sm shrink-0 disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Synthesizing...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Generate Action Plan</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Quick Prompt Chips */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-500 font-medium">Quick Prompts:</span>
            {quickPrompts.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setQuery(p)}
                className="bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-slate-200 px-2.5 py-1 rounded-lg border border-slate-800 transition-colors"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Constraints Selector Bar */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-slate-800/80">
            {/* Time Budget */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Time Budget: {Math.floor(availableMinutes / 60)}h {availableMinutes % 60 ? `${availableMinutes % 60}m` : ''} ({availableMinutes}m)</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                {[120, 240, 360, 480].map((mins) => (
                  <button
                    key={mins}
                    type="button"
                    onClick={() => setAvailableMinutes(mins)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      availableMinutes === mins
                        ? 'bg-purple-600 text-white shadow-sm'
                        : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    {mins / 60}h ({mins}m)
                  </button>
                ))}
              </div>
            </div>

            {/* Focus Areas */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-purple-400" />
                  <span>Focus Domains</span>
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5">
                {focusAreas.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-purple-950/40 text-purple-300 border border-purple-800/60"
                  >
                    <span>{tag}</span>
                    <button
                      type="button"
                      onClick={() => removeFocusArea(tag)}
                      className="text-purple-400 hover:text-white"
                    >
                      ×
                    </button>
                  </span>
                ))}
                <div className="inline-flex items-center gap-1">
                  <input
                    type="text"
                    value={focusInput}
                    onChange={(e) => setFocusInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addFocusArea();
                      }
                    }}
                    placeholder="+ add tag"
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-300 w-24 focus:outline-none focus:ring-1 focus:ring-purple-500"
                  />
                  {focusInput.trim() && (
                    <button
                      type="button"
                      onClick={addFocusArea}
                      className="text-[10px] px-1.5 py-1 rounded bg-purple-600 text-white"
                    >
                      Add
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>

      {/* History Drawer if toggled */}
      {showHistory && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <History className="w-4 h-4 text-purple-400" />
              <span>Saved Action Plan History</span>
            </h3>
            <span className="text-xs text-slate-500">Persisted in SQLite database</span>
          </div>

          {historyLoading ? (
            <p className="text-xs text-slate-500">Loading history...</p>
          ) : planHistory.length === 0 ? (
            <p className="text-xs text-slate-500">No previously saved plans found.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {planHistory.map((p) => (
                <div
                  key={p.id}
                  onClick={() => setCurrentPlan(p)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    currentPlan?.id === p.id
                      ? 'bg-purple-950/30 border-purple-500 text-white'
                      : 'bg-slate-950 border-slate-800/80 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1">
                    <span>{new Date(p.created_at).toLocaleString()}</span>
                    <span className="font-mono text-purple-400 font-semibold">{p.items.length} actions</span>
                  </div>
                  <h4 className="font-semibold text-xs text-white truncate">{p.query}</h4>
                  <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">{p.summary}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Action Plan Display */}
      {loading ? (
        <div className="p-16 text-center text-slate-500 space-y-3">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-purple-400" />
          <h3 className="text-base font-semibold text-white">Synthesizing Grounded Action Plan</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Retrieving active tasks, parent goals, imminent deadlines, ChromaDB document evidence, and user constraints...
          </p>
        </div>
      ) : !currentPlan ? (
        <div className="p-16 bg-slate-900/40 border border-slate-800 rounded-2xl text-center space-y-3">
          <Sparkles className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-lg font-bold text-white">No Action Plan Generated Yet</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            Ask "What should I do today?" above to synthesize an explainable priority schedule connecting your tasks, strategic goals, and uploaded evidence.
          </p>
          <button
            type="button"
            onClick={() => handleGeneratePlan()}
            className="mt-2 inline-flex items-center gap-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-5 py-2.5 rounded-xl text-xs font-semibold shadow-lg hover:from-purple-500 hover:to-indigo-500"
          >
            <Zap className="w-3.5 h-3.5" /> Synthesize Plan Now
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Executive Summary Card */}
          <div className="bg-gradient-to-r from-slate-900 via-[#131c33] to-slate-900 border border-slate-800 p-5 rounded-2xl shadow-xl space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-purple-400">
                  Plan Executive Summary
                </span>
                <h3 className="text-base font-bold text-white">"{currentPlan.query}"</h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg text-xs bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium">
                  {currentPlan.total_estimated_minutes}m Total / {currentPlan.available_minutes_constraint}m Budget
                </span>
                <span className="px-2.5 py-1 rounded-lg text-xs bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-medium flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" /> Persisted
                </span>
              </div>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed">{currentPlan.summary}</p>
          </div>

          {/* Action Items List */}
          <div className="space-y-3">
            {currentPlan.items.map((item) => (
              <div
                key={item.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 shadow-lg transition-all space-y-3.5"
              >
                {/* Top Row: Priority Badge, Action Title, Duration */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <span
                      className={`text-xs font-bold px-2.5 py-1 rounded-lg border shrink-0 ${getPriorityStyle(
                        item.priority_label
                      )}`}
                    >
                      {item.priority_label}
                    </span>
                    <div>
                      <h4 className="font-bold text-white text-base leading-snug">
                        {item.action}
                      </h4>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                        <strong className="text-slate-300 font-semibold">Reasoning: </strong>
                        {item.reason}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 self-end sm:self-auto">
                    <div className="flex items-center gap-1 text-xs text-cyan-400 bg-cyan-950/40 border border-cyan-800/60 px-2.5 py-1 rounded-lg">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{item.estimated_time}</span>
                    </div>

                    <div className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-2.5 py-1 rounded-lg">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>{Math.round(item.confidence * 100)}% Conf</span>
                    </div>
                  </div>
                </div>

                {/* Grounded Evidence Box */}
                <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-3 text-xs space-y-1">
                  <div className="flex items-center gap-1.5 text-slate-400 font-semibold text-[11px] uppercase tracking-wider">
                    <FileText className="w-3.5 h-3.5 text-purple-400" />
                    <span>Verified Evidence & Grounding</span>
                  </div>
                  <p className="text-slate-300 font-mono text-[11px] leading-relaxed">
                    {item.evidence}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
