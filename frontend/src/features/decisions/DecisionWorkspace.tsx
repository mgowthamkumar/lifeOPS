import React, { useState, useEffect } from 'react';
import {
  Brain,
  Sparkles,
  Plus,
  Trash2,
  CheckCircle,
  AlertCircle,
  CheckCircle2,
  Clock,
  Target,
  ShieldAlert,
  FileText,
  ChevronRight,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Award,
  Layers,
  HelpCircle,
  X,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type {
  DecisionItem,
  DecisionCreate,
  GoalItem,
} from '../../types';

export const DecisionWorkspace: React.FC = () => {
  const [decisions, setDecisions] = useState<DecisionItem[]>([]);
  const [selectedDecision, setSelectedDecision] = useState<DecisionItem | null>(null);
  const [goals, setGoals] = useState<GoalItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [error, setError] = useState<string | null>(null);

  // New Decision Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formTitle, setFormTitle] = useState<string>('');
  const [formQuestion, setFormQuestion] = useState<string>('');
  const [formContext, setFormContext] = useState<string>('');
  const [formDeadline, setFormDeadline] = useState<string>('');
  const [selectedGoalIds, setSelectedGoalIds] = useState<string[]>([]);
  const [constraintsList, setConstraintsList] = useState<string[]>([]);
  const [newConstraintInput, setNewConstraintInput] = useState<string>('');
  const [formOptions, setFormOptions] = useState<
    { title: string; description: string; effort_estimate: string }[]
  >([
    { title: '', description: '', effort_estimate: 'MEDIUM' },
    { title: '', description: '', effort_estimate: 'HIGH' },
  ]);

  useEffect(() => {
    loadDecisions();
    loadGoals();
  }, []);

  const loadDecisions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getDecisions();
      setDecisions(data);
      if (data.length > 0 && !selectedDecision) {
        setSelectedDecision(data[0]);
      } else if (selectedDecision) {
        // Refresh selected decision data
        const updated = data.find((d) => d.id === selectedDecision.id);
        if (updated) setSelectedDecision(updated);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load decisions');
    } finally {
      setLoading(false);
    }
  };

  const loadGoals = async () => {
    try {
      const data = await apiService.getGoals();
      setGoals(data);
    } catch (err) {
      console.warn('Could not load goals:', err);
    }
  };

  const handleSelectDecision = async (id: string) => {
    try {
      const full = await apiService.getDecision(id);
      setSelectedDecision(full);
    } catch (err: any) {
      setError(err.message || 'Failed to load decision details');
    }
  };

  const handleCreateDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || !formQuestion.trim()) {
      setError('Title and Question are required.');
      return;
    }

    const validOptions = formOptions.filter((o) => o.title.trim().length > 0);
    if (validOptions.length < 2) {
      setError('Please provide at least 2 candidate options to evaluate.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const payload: DecisionCreate = {
        title: formTitle.trim(),
        question: formQuestion.trim(),
        context_description: formContext.trim() || undefined,
        deadline: formDeadline ? new Date(formDeadline).toISOString() : undefined,
        constraints: constraintsList,
        goal_ids: selectedGoalIds,
        options: validOptions.map((o) => ({
          title: o.title.trim(),
          description: o.description.trim() || undefined,
          effort_estimate: o.effort_estimate,
        })),
      };

      const created = await apiService.createDecision(payload);
      setDecisions((prev) => [created, ...prev]);
      setSelectedDecision(created);
      setIsModalOpen(false);
      resetForm();
    } catch (err: any) {
      setError(err.message || 'Failed to create decision');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeDecision = async () => {
    if (!selectedDecision) return;
    try {
      setAnalyzing(true);
      setError(null);
      await apiService.analyzeDecision(selectedDecision.id);
      // Fetch fresh updated decision with persisted analysis
      const updated = await apiService.getDecision(selectedDecision.id);
      setSelectedDecision(updated);
      setDecisions((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    } catch (err: any) {
      setError(err.message || 'Failed to analyze decision');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSelectOption = async (optionId: string) => {
    if (!selectedDecision) return;
    try {
      const updated = await apiService.selectDecisionOption(selectedDecision.id, optionId);
      setSelectedDecision(updated);
      setDecisions((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    } catch (err: any) {
      setError(err.message || 'Failed to adopt option');
    }
  };

  const handleDeleteDecision = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this decision?')) return;
    try {
      await apiService.deleteDecision(id);
      const remaining = decisions.filter((d) => d.id !== id);
      setDecisions(remaining);
      if (selectedDecision?.id === id) {
        setSelectedDecision(remaining.length > 0 ? remaining[0] : null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete decision');
    }
  };

  const resetForm = () => {
    setFormTitle('');
    setFormQuestion('');
    setFormContext('');
    setFormDeadline('');
    setSelectedGoalIds([]);
    setConstraintsList([]);
    setNewConstraintInput('');
    setFormOptions([
      { title: '', description: '', effort_estimate: 'MEDIUM' },
      { title: '', description: '', effort_estimate: 'HIGH' },
    ]);
  };

  const addConstraint = () => {
    if (newConstraintInput.trim() && !constraintsList.includes(newConstraintInput.trim())) {
      setConstraintsList([...constraintsList, newConstraintInput.trim()]);
      setNewConstraintInput('');
    }
  };

  const removeConstraint = (c: string) => {
    setConstraintsList(constraintsList.filter((item) => item !== c));
  };

  const addOptionField = () => {
    setFormOptions([...formOptions, { title: '', description: '', effort_estimate: 'MEDIUM' }]);
  };

  const removeOptionField = (idx: number) => {
    if (formOptions.length <= 2) return;
    setFormOptions(formOptions.filter((_, i) => i !== idx));
  };

  const updateOptionField = (idx: number, field: string, val: string) => {
    const updated = [...formOptions];
    updated[idx] = { ...updated[idx], [field]: val };
    setFormOptions(updated);
  };

  const filteredDecisions = decisions.filter((d) => {
    if (statusFilter === 'ALL') return true;
    return d.status === statusFilter;
  });

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-slate-900/40 border border-slate-800 rounded-2xl">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 rounded-xl text-cyan-400">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                Decision Intelligence Workspace
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/60 uppercase">
                  Grounded AI
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Multi-option evaluation, evidence retrieval, goal alignment & constraint validation.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded-lg p-1 text-xs">
            {['ALL', 'DRAFT', 'ANALYZED', 'DECIDED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
                  statusFilter === st
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-medium text-xs rounded-xl shadow-lg shadow-cyan-500/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Decision</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/30 border border-rose-800/40 rounded-xl flex items-center space-x-3 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-rose-400 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Decision Sidebar / Cards */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
            <span>Decisions ({filteredDecisions.length})</span>
            <button
              onClick={loadDecisions}
              disabled={loading}
              className="hover:text-cyan-400 transition-colors"
              title="Refresh decisions"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>

          {filteredDecisions.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/20 border border-slate-800/60 rounded-xl space-y-3">
              <HelpCircle className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400">No decisions match this filter.</p>
              <button
                onClick={() => setIsModalOpen(true)}
                className="text-xs text-cyan-400 hover:underline inline-flex items-center gap-1 font-medium"
              >
                Create your first decision <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              {filteredDecisions.map((dec) => {
                const isSelected = selectedDecision?.id === dec.id;
                return (
                  <div
                    key={dec.id}
                    onClick={() => handleSelectDecision(dec.id)}
                    className={`p-4 rounded-xl border transition-all cursor-pointer relative ${
                      isSelected
                        ? 'bg-slate-800/90 border-cyan-500/50 shadow-md shadow-cyan-500/10'
                        : 'bg-slate-900/40 border-slate-800/80 hover:bg-slate-800/40 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1 pr-6">
                        <span
                          className={`inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                            dec.status === 'DECIDED'
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/50'
                              : dec.status === 'ANALYZED'
                              ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/50'
                              : 'bg-slate-800 text-slate-300 border border-slate-700'
                          }`}
                        >
                          {dec.status}
                        </span>
                        <h3 className="font-semibold text-sm text-white line-clamp-1">
                          {dec.title}
                        </h3>
                        <p className="text-xs text-slate-400 line-clamp-2">{dec.question}</p>
                      </div>

                      <button
                        onClick={(e) => handleDeleteDecision(dec.id, e)}
                        className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                        title="Delete decision"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <div className="mt-3 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <Layers className="w-3 h-3 text-slate-500" />
                          {dec.options.length} options
                        </span>
                        {dec.goals.length > 0 && (
                          <span className="flex items-center gap-1 text-cyan-400">
                            <Target className="w-3 h-3" />
                            {dec.goals.length} goal
                          </span>
                        )}
                      </div>
                      <ChevronRight
                        className={`w-4 h-4 transition-transform ${
                          isSelected ? 'text-cyan-400 translate-x-0.5' : 'text-slate-600'
                        }`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Full Decision Inspector & Analysis View */}
        <div className="lg:col-span-8 space-y-6">
          {!selectedDecision ? (
            <div className="p-12 text-center bg-slate-900/30 border border-slate-800 rounded-2xl space-y-4">
              <Brain className="w-12 h-12 text-slate-600 mx-auto" />
              <div>
                <h3 className="text-base font-semibold text-white">Select a Decision to Inspect</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                  Choose a decision from the left panel or create a new one to evaluate candidate options against your documents and goals.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Decision Hero Card */}
              <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl space-y-4">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                          selectedDecision.status === 'DECIDED'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/50'
                            : selectedDecision.status === 'ANALYZED'
                            ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/50'
                            : 'bg-slate-800 text-slate-300 border border-slate-700'
                        }`}
                      >
                        {selectedDecision.status}
                      </span>
                      {selectedDecision.deadline && (
                        <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                          <Clock className="w-3 h-3 text-slate-500" />
                          Due: {new Date(selectedDecision.deadline).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <h2 className="text-lg font-bold text-white tracking-tight">
                      {selectedDecision.title}
                    </h2>
                    <p className="text-sm text-cyan-300/90 font-medium">
                      "{selectedDecision.question}"
                    </p>
                    {selectedDecision.context_description && (
                      <p className="text-xs text-slate-400 mt-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800/60 leading-relaxed">
                        <span className="text-slate-300 font-semibold block mb-0.5">Context:</span>
                        {selectedDecision.context_description}
                      </p>
                    )}
                  </div>

                  <div className="shrink-0 flex items-center gap-2">
                    <button
                      onClick={handleAnalyzeDecision}
                      disabled={analyzing}
                      className="flex items-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-medium text-xs rounded-xl shadow-lg shadow-cyan-500/20 transition-all cursor-pointer"
                    >
                      <Sparkles className={`w-4 h-4 ${analyzing ? 'animate-spin' : ''}`} />
                      <span>{analyzing ? 'Evaluating Evidence...' : 'Analyze Decision'}</span>
                    </button>
                  </div>
                </div>

                {/* Badges for Goals & Constraints */}
                <div className="pt-3 border-t border-slate-800/60 flex flex-wrap gap-4 text-xs">
                  {selectedDecision.goals.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-slate-400 font-semibold text-[11px] flex items-center gap-1">
                        <Target className="w-3.5 h-3.5 text-cyan-400" /> Linked Goals:
                      </span>
                      {selectedDecision.goals.map((g) => (
                        <span
                          key={g.id}
                          className="px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/60 text-cyan-300 text-[11px]"
                        >
                          {g.title} ({g.importance})
                        </span>
                      ))}
                    </div>
                  )}

                  {selectedDecision.constraints.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-slate-400 font-semibold text-[11px] flex items-center gap-1">
                        <ShieldAlert className="w-3.5 h-3.5 text-amber-400" /> Constraints:
                      </span>
                      {selectedDecision.constraints.map((c, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded bg-amber-950/40 border border-amber-800/40 text-amber-300 text-[11px]"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Latest Analysis Results Section */}
              {selectedDecision.latest_analysis ? (
                <div className="space-y-6">
                  {/* Executive Recommendation Banner */}
                  <div className="p-5 bg-gradient-to-r from-emerald-950/40 via-cyan-950/30 to-blue-950/20 border border-emerald-500/40 rounded-2xl relative overflow-hidden shadow-lg shadow-emerald-950/30">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="p-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-300">
                            <Award className="w-4 h-4" />
                          </span>
                          <span className="text-xs font-bold text-emerald-300 uppercase tracking-wider">
                            Executive Recommendation
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-900 border border-slate-700 text-slate-300 font-mono">
                            Confidence: {selectedDecision.latest_analysis.confidence}
                          </span>
                        </div>
                        <h3 className="text-base font-bold text-white">
                          {selectedDecision.latest_analysis.recommendation}
                        </h3>
                        <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
                          {selectedDecision.latest_analysis.reasoning_summary}
                        </p>
                      </div>

                      {selectedDecision.latest_analysis.top_option_id &&
                        selectedDecision.status !== 'DECIDED' && (
                          <button
                            onClick={() =>
                              handleSelectOption(selectedDecision.latest_analysis!.top_option_id!)
                            }
                            className="shrink-0 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-emerald-900/40 transition-all flex items-center gap-1.5"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Adopt Winning Option</span>
                          </button>
                        )}
                    </div>
                  </div>

                  {/* Multi-Option Comparative Cards */}
                  <div>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                      <TrendingUp className="w-4 h-4 text-cyan-400" />
                      Comparative Options Evaluation ({selectedDecision.latest_analysis.options_analysis.length})
                    </h3>

                    <div className="space-y-4">
                      {selectedDecision.latest_analysis.options_analysis.map((opt) => {
                        const isWinner =
                          selectedDecision.latest_analysis?.top_option_id === opt.option_id;
                        const isDecidedSelection =
                          selectedDecision.selected_option_id === opt.option_id;

                        return (
                          <div
                            key={opt.option_id}
                            className={`p-5 rounded-2xl border transition-all ${
                              isDecidedSelection
                                ? 'bg-emerald-950/20 border-emerald-500/60 shadow-lg shadow-emerald-950/20'
                                : isWinner
                                ? 'bg-cyan-950/20 border-cyan-500/50 shadow-md shadow-cyan-950/20'
                                : 'bg-slate-900/40 border-slate-800'
                            }`}
                          >
                            {/* Option Header */}
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
                              <div className="flex items-center gap-3">
                                <div
                                  className={`w-12 h-12 rounded-xl flex flex-col items-center justify-center font-bold font-mono border ${
                                    opt.match >= 80
                                      ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60'
                                      : opt.match >= 60
                                      ? 'bg-cyan-950/80 text-cyan-300 border-cyan-700/60'
                                      : 'bg-amber-950/80 text-amber-300 border-amber-700/60'
                                  }`}
                                >
                                  <span className="text-base">{Math.round(opt.match)}%</span>
                                  <span className="text-[9px] uppercase tracking-wider opacity-80">
                                    Match
                                  </span>
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <h4 className="font-bold text-base text-white">
                                      {opt.option_title}
                                    </h4>
                                    {isDecidedSelection && (
                                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-900 text-emerald-200 border border-emerald-600">
                                        ACCEPTED DECISION
                                      </span>
                                    )}
                                    {isWinner && !isDecidedSelection && (
                                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-900 text-cyan-200 border border-cyan-600">
                                        TOP CHOICE
                                      </span>
                                    )}
                                  </div>
                                  <span className="text-xs text-slate-400 font-medium">
                                    Verdict: <span className="text-slate-200 font-semibold">{opt.recommendation}</span>
                                  </span>
                                </div>
                              </div>

                              <div className="flex items-center gap-3">
                                {selectedDecision.status !== 'DECIDED' && (
                                  <button
                                    onClick={() => handleSelectOption(opt.option_id)}
                                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-emerald-600 hover:text-white text-slate-300 border border-slate-700 transition-colors"
                                  >
                                    Adopt This Option
                                  </button>
                                )}
                              </div>
                            </div>

                            {/* Detailed Analysis Breakdown */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-xs">
                              {/* Strengths */}
                              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                                <span className="font-semibold text-emerald-400 flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                                  <CheckCircle className="w-3.5 h-3.5" /> Strengths
                                </span>
                                <ul className="space-y-1 text-slate-300">
                                  {opt.strengths.map((s, i) => (
                                    <li key={i} className="flex items-start gap-1.5">
                                      <span className="text-emerald-400 text-xs mt-0.5">•</span>
                                      <span>{s}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              {/* Weaknesses */}
                              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                                <span className="font-semibold text-amber-400 flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                                  <AlertCircle className="w-3.5 h-3.5" /> Weaknesses & Risks
                                </span>
                                <ul className="space-y-1 text-slate-300">
                                  {opt.weaknesses.map((w, i) => (
                                    <li key={i} className="flex items-start gap-1.5">
                                      <span className="text-amber-400 text-xs mt-0.5">•</span>
                                      <span>{w}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              {/* Constraints Evaluation */}
                              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                                <span className="font-semibold text-blue-400 flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                                  <ShieldAlert className="w-3.5 h-3.5" /> Constraints Evaluation
                                </span>
                                <ul className="space-y-1 text-slate-300">
                                  {opt.constraints.map((c, i) => (
                                    <li key={i} className="flex items-start gap-1.5">
                                      <span className="text-blue-400 text-xs mt-0.5">•</span>
                                      <span>{c}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              {/* Gaps & Missing Information */}
                              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5">
                                <span className="font-semibold text-purple-400 flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                                  <HelpCircle className="w-3.5 h-3.5" /> Information Gaps
                                </span>
                                <ul className="space-y-1 text-slate-300">
                                  {opt.gaps.map((g, i) => (
                                    <li key={i} className="flex items-start gap-1.5">
                                      <span className="text-purple-400 text-xs mt-0.5">•</span>
                                      <span>{g}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </div>

                            {/* Goal Alignment & Citations */}
                            <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-3 text-xs">
                              <div className="bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
                                <span className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider block mb-0.5">
                                  Goal Alignment:
                                </span>
                                <p className="text-slate-200">{opt.goal_alignment}</p>
                              </div>

                              {opt.evidence && opt.evidence.length > 0 && (
                                <div className="space-y-1.5">
                                  <span className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider flex items-center gap-1">
                                    <FileText className="w-3 h-3 text-cyan-400" /> Grounded Evidence Citations:
                                  </span>
                                  <div className="space-y-1">
                                    {opt.evidence.map((ev, i) => (
                                      <div
                                        key={i}
                                        className="p-2 bg-slate-950 border border-slate-800 rounded-md font-mono text-[11px] text-cyan-300/90 leading-relaxed"
                                      >
                                        {ev}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center bg-slate-900/30 border border-slate-800 rounded-2xl space-y-3">
                  <Sparkles className="w-8 h-8 text-cyan-400 mx-auto" />
                  <h3 className="text-sm font-semibold text-white">Decision Not Analyzed Yet</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Click "Analyze Decision" above to query your uploaded knowledge base documents, evaluate trade-offs, and generate grounded recommendations.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* New Decision Creation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#0b1120] border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Brain className="w-5 h-5 text-cyan-400" />
                <h2 className="text-base font-bold text-white">Create Strategic Decision</h2>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateDecision} className="space-y-4 text-xs">
              {/* Title & Deadline */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="md:col-span-2 space-y-1">
                  <label className="text-slate-300 font-semibold">Decision Title *</label>
                  <input
                    type="text"
                    required
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    placeholder="e.g., Database Caching Architecture"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold">Deadline</label>
                  <input
                    type="date"
                    value={formDeadline}
                    onChange={(e) => setFormDeadline(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              {/* Core Question */}
              <div className="space-y-1">
                <label className="text-slate-300 font-semibold">Core Question *</label>
                <textarea
                  required
                  rows={2}
                  value={formQuestion}
                  onChange={(e) => setFormQuestion(e.target.value)}
                  placeholder="e.g., Which caching layer should we adopt to handle 100k users with <50ms latency?"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-500 leading-relaxed"
                />
              </div>

              {/* Context Description */}
              <div className="space-y-1">
                <label className="text-slate-300 font-semibold">Context & Background</label>
                <textarea
                  rows={2}
                  value={formContext}
                  onChange={(e) => setFormContext(e.target.value)}
                  placeholder="Background situation, assumptions, current operational pain points..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-500 leading-relaxed"
                />
              </div>

              {/* Linked Strategic Goals */}
              {goals.length > 0 && (
                <div className="space-y-1">
                  <label className="text-slate-300 font-semibold flex items-center gap-1">
                    <Target className="w-3.5 h-3.5 text-cyan-400" /> Link Strategic Goals
                  </label>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {goals.map((g) => {
                      const selected = selectedGoalIds.includes(g.id);
                      return (
                        <button
                          type="button"
                          key={g.id}
                          onClick={() => {
                            if (selected) {
                              setSelectedGoalIds(selectedGoalIds.filter((id) => id !== g.id));
                            } else {
                              setSelectedGoalIds([...selectedGoalIds, g.id]);
                            }
                          }}
                          className={`px-2.5 py-1 rounded-md text-[11px] font-medium border transition-colors cursor-pointer ${
                            selected
                              ? 'bg-cyan-950 border-cyan-500 text-cyan-300 font-semibold'
                              : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          {g.title} ({g.importance})
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Constraints Tags */}
              <div className="space-y-1.5">
                <label className="text-slate-300 font-semibold flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5 text-amber-400" /> Constraints & Boundaries
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newConstraintInput}
                    onChange={(e) => setNewConstraintInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addConstraint();
                      }
                    }}
                    placeholder="e.g. Budget under $500/mo, P99 latency <50ms..."
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-white focus:outline-none focus:border-cyan-500"
                  />
                  <button
                    type="button"
                    onClick={addConstraint}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg font-semibold"
                  >
                    Add
                  </button>
                </div>
                {constraintsList.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {constraintsList.map((c, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800/60 text-amber-300 text-[11px] flex items-center gap-1"
                      >
                        {c}
                        <button
                          type="button"
                          onClick={() => removeConstraint(c)}
                          className="hover:text-rose-400"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Candidate Options */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <div className="flex items-center justify-between">
                  <label className="text-slate-300 font-semibold">Candidate Options (min 2)</label>
                  <button
                    type="button"
                    onClick={addOptionField}
                    className="text-cyan-400 hover:text-cyan-300 text-xs font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" /> Add Option
                  </button>
                </div>

                <div className="space-y-2.5">
                  {formOptions.map((opt, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-xl space-y-2"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center font-bold text-[10px]">
                          {idx + 1}
                        </span>
                        <input
                          type="text"
                          required
                          value={opt.title}
                          onChange={(e) => updateOptionField(idx, 'title', e.target.value)}
                          placeholder={`Option ${idx + 1} Title (e.g. Distributed Redis Cluster)`}
                          className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-white focus:outline-none focus:border-cyan-500"
                        />
                        <select
                          value={opt.effort_estimate}
                          onChange={(e) =>
                            updateOptionField(idx, 'effort_estimate', e.target.value)
                          }
                          className="bg-slate-900 border border-slate-800 rounded-lg px-2 py-1.5 text-slate-300 focus:outline-none"
                        >
                          <option value="LOW">Low Effort</option>
                          <option value="MEDIUM">Medium Effort</option>
                          <option value="HIGH">High Effort</option>
                        </select>
                        {formOptions.length > 2 && (
                          <button
                            type="button"
                            onClick={() => removeOptionField(idx)}
                            className="text-slate-500 hover:text-rose-400 p-1"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                      <input
                        type="text"
                        value={opt.description}
                        onChange={(e) => updateOptionField(idx, 'description', e.target.value)}
                        placeholder="Brief description or architectural implementation details..."
                        className="w-full bg-slate-900/60 border border-slate-800/60 rounded-lg px-2.5 py-1 text-slate-300 text-[11px] focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Modal Actions */}
              <div className="pt-3 border-t border-slate-800 flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-5 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-xl font-semibold shadow-lg shadow-cyan-500/20 disabled:opacity-50 cursor-pointer"
                >
                  {loading ? 'Creating...' : 'Create Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
