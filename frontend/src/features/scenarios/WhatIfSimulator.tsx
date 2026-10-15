import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  Sparkles,
  Clock,
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  TrendingUp,
  FileText,
  Plus,
  Sliders,
  DollarSign,
  Lock,
  Zap,
  ArrowRight,
  Info,
  X,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type {
  ScenarioItem,
  ScenarioSimulationResponse,
  SimulationComparisonItem,
} from '../../types';

export const WhatIfSimulator: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([]);
  const [baselineScenario, setBaselineScenario] = useState<ScenarioItem | null>(null);
  const [activeScenario, setActiveScenario] = useState<ScenarioItem | null>(null);
  const [simulationResult, setSimulationResult] = useState<ScenarioSimulationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Parameter Controls for Active Scenario
  const [paramTimeMinutes, setParamTimeMinutes] = useState<number>(120);
  const [paramBudget, setParamBudget] = useState<number>(300);
  const [paramDurationMultiplier, setParamDurationMultiplier] = useState<number>(1.0);
  const [paramConstraints, setParamConstraints] = useState<string[]>([
    'Daily available time max 120 minutes',
    'Budget reduced to $300',
  ]);
  const [newConstraintInput, setNewConstraintInput] = useState<string>('');

  // New Scenario Modal
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [newScenarioName, setNewScenarioName] = useState<string>('');
  const [newScenarioDesc, setNewScenarioDesc] = useState<string>('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load baseline
      const base = await apiService.getBaselineScenario();
      setBaselineScenario(base);

      // Load all scenarios
      const all = await apiService.getScenarios();
      setScenarios(all);

      // Find an active non-baseline scenario or create/select one
      const nonBase = all.find((s) => !s.is_baseline);
      if (nonBase) {
        setActiveScenario(nonBase);
        syncParamsFromScenario(nonBase);
        if (nonBase.simulation_result) {
          setSimulationResult(nonBase.simulation_result);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load scenarios');
    } finally {
      setLoading(false);
    }
  };

  const syncParamsFromScenario = (scen: ScenarioItem) => {
    const p = scen.parameters || {};
    setParamTimeMinutes(p.available_time_minutes ?? 120);
    setParamBudget(p.budget ?? 300);
    setParamDurationMultiplier(p.task_duration_multiplier ?? 1.0);
    setParamConstraints(p.constraints || ['Daily available time max 120 minutes']);
  };

  const handleSelectScenario = (scen: ScenarioItem) => {
    setActiveScenario(scen);
    syncParamsFromScenario(scen);
    if (scen.simulation_result) {
      setSimulationResult(scen.simulation_result);
    } else {
      setSimulationResult(null);
    }
  };

  const handleRunSimulation = async (customOverrides?: Record<string, any>) => {
    try {
      setSimulating(true);
      setError(null);

      let targetScenario = activeScenario;

      // If no active scenario exists, create a default 2h/day scenario
      if (!targetScenario) {
        targetScenario = await apiService.createScenario({
          name: 'Crunch Mode (2 hours/day)',
          description: 'Simulate severe time constraint (120 mins vs 240 mins baseline).',
          is_baseline: false,
          parameters: {
            available_time_minutes: 120,
            budget: 300,
            task_duration_multiplier: 1.0,
            constraints: ['Daily available time max 120 minutes'],
          },
        });
        setActiveScenario(targetScenario);
        setScenarios((prev) => [...prev, targetScenario!]);
      }

      const overrides = customOverrides || {
        available_time_minutes: paramTimeMinutes,
        budget: paramBudget,
        task_duration_multiplier: paramDurationMultiplier,
        constraints: paramConstraints,
      };

      const result = await apiService.simulateScenario(targetScenario.id, {
        baseline_scenario_id: baselineScenario?.id,
        parameter_overrides: overrides,
      });

      setSimulationResult(result);

      // Refresh scenario in list
      const refreshed = await apiService.getScenario(targetScenario.id);
      setActiveScenario(refreshed);
      setScenarios((prev) => prev.map((s) => (s.id === refreshed.id ? refreshed : s)));
    } catch (err: any) {
      setError(err.message || 'Simulation failed');
    } finally {
      setSimulating(false);
    }
  };

  // Preset quick triggers
  const applyPreset2hVs4h = async () => {
    setParamTimeMinutes(120);
    setParamBudget(300);
    setParamDurationMultiplier(1.0);
    setParamConstraints(['Daily available time max 120 minutes', 'Budget reduced to $300']);
    await handleRunSimulation({
      available_time_minutes: 120,
      budget: 300,
      task_duration_multiplier: 1.0,
      constraints: ['Daily available time max 120 minutes', 'Budget reduced to $300'],
    });
  };

  const applyPresetTimeCrunch = async () => {
    setParamTimeMinutes(90);
    setParamDurationMultiplier(1.25);
    await handleRunSimulation({
      available_time_minutes: 90,
      task_duration_multiplier: 1.25,
    });
  };

  const handleCreateScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newScenarioName.trim()) return;

    try {
      setLoading(true);
      const created = await apiService.createScenario({
        name: newScenarioName.trim(),
        description: newScenarioDesc.trim() || undefined,
        is_baseline: false,
        parameters: {
          available_time_minutes: paramTimeMinutes,
          budget: paramBudget,
          task_duration_multiplier: paramDurationMultiplier,
          constraints: paramConstraints,
        },
      });

      setScenarios((prev) => [...prev, created]);
      setActiveScenario(created);
      setIsModalOpen(false);
      setNewScenarioName('');
      setNewScenarioDesc('');
      await handleRunSimulation();
    } catch (err: any) {
      setError(err.message || 'Failed to create scenario');
    } finally {
      setLoading(false);
    }
  };

  const addConstraint = () => {
    if (newConstraintInput.trim() && !paramConstraints.includes(newConstraintInput.trim())) {
      setParamConstraints([...paramConstraints, newConstraintInput.trim()]);
      setNewConstraintInput('');
    }
  };

  const removeConstraint = (c: string) => {
    setParamConstraints(paramConstraints.filter((x) => x !== c));
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-gradient-to-tr from-purple-500/20 to-cyan-500/20 border border-purple-500/30 rounded-xl text-purple-400">
            <GitBranch className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              What-If Simulation Engine
              <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800/60 uppercase">
                LifeOps Signature
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Simulate alternative futures and perturbations. Re-runs RAG, priority ranking, decision trade-offs, and action plans.
            </p>
          </div>
        </div>

        {/* Baseline Isolation Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-950/40 border border-emerald-800/50 rounded-xl text-emerald-300 text-xs">
          <Lock className="w-3.5 h-3.5 text-emerald-400" />
          <span className="font-semibold">Baseline Isolation Guaranteed</span>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/30 border border-rose-800/40 rounded-xl flex items-center space-x-3 text-rose-300 text-xs">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-rose-400 hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Preset Quick Actions */}
      <div className="p-4 bg-slate-900/30 border border-slate-800 rounded-xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-slate-300 font-semibold">
          <Zap className="w-4 h-4 text-cyan-400" />
          <span>Quick Simulation Presets:</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={applyPreset2hVs4h}
            disabled={simulating}
            className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600/30 to-cyan-600/30 hover:from-purple-600/40 hover:to-cyan-600/40 text-cyan-200 border border-cyan-500/40 text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>2 Hours/Day vs 4 Hours/Day Crunch</span>
          </button>

          <button
            onClick={applyPresetTimeCrunch}
            disabled={simulating}
            className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <TrendingDown className="w-3.5 h-3.5 text-amber-400" />
            <span>Extreme Crunch (90 min + 1.25x Duration)</span>
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1 cursor-pointer transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Scenario</span>
          </button>
        </div>
      </div>

      {/* Parameter Controls Panel */}
      <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Scenario Parameter Controls
            </h3>
            {activeScenario && (
              <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-purple-300 border border-purple-800/50 font-medium">
                {activeScenario.name}
              </span>
            )}
          </div>

          {/* Scenario Selector Dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Target Scenario:</span>
            <select
              value={activeScenario?.id || ''}
              onChange={(e) => {
                const scen = scenarios.find((s) => s.id === e.target.value);
                if (scen) handleSelectScenario(scen);
              }}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} {s.is_baseline ? '(Baseline)' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Sliders Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
          {/* Available Time Slider */}
          <div className="space-y-2 p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl">
            <div className="flex items-center justify-between">
              <label className="text-slate-300 font-semibold flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-400" /> Daily Available Time
              </label>
              <span className="font-mono font-bold text-cyan-400 text-sm">
                {paramTimeMinutes}m ({paramTimeMinutes / 60}h)
              </span>
            </div>
            <input
              type="range"
              min={30}
              max={480}
              step={30}
              value={paramTimeMinutes}
              onChange={(e) => setParamTimeMinutes(Number(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>30m</span>
              <span>120m (2h)</span>
              <span>240m (4h Base)</span>
              <span>480m (8h)</span>
            </div>
          </div>

          {/* Budget Cap Slider */}
          <div className="space-y-2 p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl">
            <div className="flex items-center justify-between">
              <label className="text-slate-300 font-semibold flex items-center gap-1.5">
                <DollarSign className="w-3.5 h-3.5 text-emerald-400" /> Operational Budget
              </label>
              <span className="font-mono font-bold text-emerald-400 text-sm">
                ${paramBudget}/mo
              </span>
            </div>
            <input
              type="range"
              min={100}
              max={1500}
              step={50}
              value={paramBudget}
              onChange={(e) => setParamBudget(Number(e.target.value))}
              className="w-full accent-emerald-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>$100</span>
              <span>$300</span>
              <span>$600 (Base)</span>
              <span>$1500</span>
            </div>
          </div>

          {/* Task Duration Multiplier */}
          <div className="space-y-2 p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl">
            <div className="flex items-center justify-between">
              <label className="text-slate-300 font-semibold flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-purple-400" /> Duration Multiplier
              </label>
              <span className="font-mono font-bold text-purple-400 text-sm">
                {paramDurationMultiplier}x
              </span>
            </div>
            <input
              type="range"
              min={0.75}
              max={2.0}
              step={0.25}
              value={paramDurationMultiplier}
              onChange={(e) => setParamDurationMultiplier(Number(e.target.value))}
              className="w-full accent-purple-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0.75x (Faster)</span>
              <span>1.0x (Normal)</span>
              <span>1.5x</span>
              <span>2.0x (Heavy)</span>
            </div>
          </div>
        </div>

        {/* Constraints Input */}
        <div className="space-y-2 text-xs">
          <label className="text-slate-300 font-semibold">Scenario Constraint Tags:</label>
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
              placeholder="e.g. Daily available time max 120 minutes, Remote only..."
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
          <div className="flex flex-wrap gap-1.5 pt-1">
            {paramConstraints.map((c, i) => (
              <span
                key={i}
                className="px-2.5 py-0.5 rounded-full bg-purple-950/60 border border-purple-800/60 text-purple-300 text-[11px] flex items-center gap-1.5"
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
        </div>

        {/* Run Simulation CTA */}
        <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-slate-500" />
            <span>Simulates time budgeting, re-evaluates priorities & decision options without touching baseline rows.</span>
          </div>

          <button
            onClick={() => handleRunSimulation()}
            disabled={simulating}
            className="flex items-center space-x-2 px-6 py-2.5 bg-gradient-to-r from-purple-500 via-indigo-600 to-cyan-500 hover:from-purple-400 hover:to-cyan-400 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-lg shadow-purple-500/20 transition-all cursor-pointer"
          >
            <Sparkles className={`w-4 h-4 ${simulating ? 'animate-spin' : ''}`} />
            <span>{simulating ? 'Simulating All Intelligence Layers...' : 'Run What-If Simulation'}</span>
          </button>
        </div>
      </div>

      {/* Side-by-Side Simulation Results */}
      {simulationResult && (
        <div className="space-y-6">
          {/* Dual Column Comparative Matrix */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Baseline Column (Left - Blue/Slate) */}
            <div className="p-6 bg-slate-900/40 border border-slate-700/80 rounded-2xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-blue-400 animate-pulse" />
                  <h3 className="font-bold text-sm text-white uppercase tracking-wider">
                    Baseline Reality
                  </h3>
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-blue-950/80 text-blue-300 border border-blue-800/60">
                  {simulationResult.baseline.available_time_minutes}m ({simulationResult.baseline.available_time_minutes / 60}h/day)
                </span>
              </div>

              {/* Baseline Metrics */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Allocated Time</span>
                  <span className="text-base font-bold text-white font-mono">
                    {simulationResult.baseline.allocated_time_minutes} min
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    of {simulationResult.baseline.available_time_minutes}m limit
                  </span>
                </div>

                <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/80">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Planned Actions</span>
                  <span className="text-base font-bold text-emerald-400 font-mono">
                    {simulationResult.baseline.planned_actions_count}
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    {simulationResult.baseline.deferred_actions_count} deferred
                  </span>
                </div>
              </div>

              {/* Baseline Action Schedule */}
              <div className="space-y-2 text-xs">
                <span className="text-slate-400 font-semibold text-[11px] uppercase tracking-wider block">
                  Planned Schedule:
                </span>
                <div className="space-y-1.5 max-h-60 overflow-y-auto">
                  {simulationResult.baseline.planned_actions.map((act: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-2.5 bg-slate-950/80 border border-slate-800/80 rounded-lg flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span className="font-medium text-slate-200 line-clamp-1">{act.title}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 shrink-0">
                        {act.estimated_minutes}m
                      </span>
                    </div>
                  ))}
                  {simulationResult.baseline.planned_actions.length === 0 && (
                    <p className="text-slate-500 text-xs italic">No actions planned.</p>
                  )}
                </div>
              </div>

              {/* Baseline Decision Outcome */}
              {simulationResult.baseline.decision_analysis && (
                <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-xs space-y-1">
                  <span className="text-slate-400 uppercase text-[10px] font-semibold block">Top Decision Option:</span>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">
                      {simulationResult.baseline.decision_analysis.top_option}
                    </span>
                    <span className="text-cyan-400 font-mono font-bold">
                      {simulationResult.baseline.decision_analysis.top_match_score}% Match
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Simulated Scenario Column (Right - Purple/Cyan) */}
            <div className="p-6 bg-purple-950/10 border border-purple-500/50 rounded-2xl space-y-4 shadow-xl shadow-purple-950/10">
              <div className="flex items-center justify-between pb-3 border-b border-purple-900/40">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse" />
                  <h3 className="font-bold text-sm text-purple-200 uppercase tracking-wider">
                    Simulated Scenario ({simulationResult.scenario_name})
                  </h3>
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-purple-950 text-purple-300 border border-purple-700/60">
                  {simulationResult.scenario.available_time_minutes}m ({simulationResult.scenario.available_time_minutes / 60}h/day)
                </span>
              </div>

              {/* Scenario Metrics */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-950/60 rounded-xl border border-purple-900/40">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Allocated Time</span>
                  <span className="text-base font-bold text-white font-mono">
                    {simulationResult.scenario.allocated_time_minutes} min
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    of {simulationResult.scenario.available_time_minutes}m limit
                  </span>
                </div>

                <div className="p-3 bg-slate-950/60 rounded-xl border border-purple-900/40">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Planned Actions</span>
                  <span className="text-base font-bold text-purple-300 font-mono">
                    {simulationResult.scenario.planned_actions_count}
                  </span>
                  <span className="text-[10px] text-amber-400 block font-semibold">
                    {simulationResult.scenario.deferred_actions_count} deferred
                  </span>
                </div>
              </div>

              {/* Scenario Action Schedule */}
              <div className="space-y-2 text-xs">
                <span className="text-slate-400 font-semibold text-[11px] uppercase tracking-wider block">
                  Simulated Allocation & Deferrals:
                </span>
                <div className="space-y-1.5 max-h-60 overflow-y-auto">
                  {/* Planned */}
                  {simulationResult.scenario.planned_actions.map((act: any, idx: number) => (
                    <div
                      key={`p-${idx}`}
                      className="p-2.5 bg-slate-950/80 border border-purple-900/40 rounded-lg flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                        <span className="font-medium text-slate-200 line-clamp-1">{act.title}</span>
                      </div>
                      <span className="text-[10px] font-mono text-purple-300 shrink-0">
                        {act.estimated_minutes}m
                      </span>
                    </div>
                  ))}

                  {/* Deferred */}
                  {simulationResult.scenario.deferred_actions.map((act: any, idx: number) => (
                    <div
                      key={`d-${idx}`}
                      className="p-2.5 bg-amber-950/20 border border-amber-800/40 rounded-lg flex items-center justify-between gap-2"
                    >
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <div>
                          <span className="font-medium text-amber-200 line-clamp-1">{act.title}</span>
                          <span className="text-[10px] text-amber-400/80 block">{act.reason}</span>
                        </div>
                      </div>
                      <span className="text-[10px] font-mono text-amber-400 shrink-0 font-bold">
                        DEFERRED
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Scenario Decision Outcome */}
              {simulationResult.scenario.decision_analysis && (
                <div className="p-3 bg-slate-950/60 border border-purple-900/40 rounded-xl text-xs space-y-1">
                  <span className="text-slate-400 uppercase text-[10px] font-semibold block">Simulated Top Option:</span>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">
                      {simulationResult.scenario.decision_analysis.top_option}
                    </span>
                    <span className="text-purple-300 font-mono font-bold">
                      {simulationResult.scenario.decision_analysis.top_match_score}% Match
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Variance & Causal Divergence Analysis */}
          <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-sm text-white flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-purple-400" />
                Variance & Causal Divergence Analysis
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Confidence:</span>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/50">
                  {Math.round(simulationResult.confidence * 100)}% {simulationResult.confidence_level}
                </span>
              </div>
            </div>

            {/* Differences Table */}
            <div className="space-y-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
                Quantified Delta Items:
              </span>
              <div className="space-y-2">
                {simulationResult.differences.map((diff: SimulationComparisonItem, idx: number) => (
                  <div
                    key={idx}
                    className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl text-xs flex flex-col md:flex-row md:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300">
                          {diff.category}
                        </span>
                        <h4 className="font-bold text-white">{diff.title}</h4>
                      </div>
                      <p className="text-slate-400 text-[11px] leading-relaxed">{diff.reason}</p>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 text-right">
                      <div className="text-[11px] font-mono">
                        <span className="text-slate-400 block">Baseline: {diff.baseline_value}</span>
                        <span className="text-purple-300 font-bold block">
                          Scenario: {diff.scenario_value}
                        </span>
                      </div>
                      <span className="px-2.5 py-1 rounded bg-purple-950 text-purple-300 border border-purple-800/50 font-mono font-bold text-xs">
                        {diff.difference}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Causal Reasons Breakdown */}
            <div className="space-y-2 pt-2 border-t border-slate-800/60 text-xs">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
                Causal Reasons & Impact Rationale:
              </span>
              <ul className="space-y-1 text-slate-300">
                {simulationResult.reasons.map((r: string, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <ArrowRight className="w-3.5 h-3.5 text-cyan-400 mt-0.5 shrink-0" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Grounded Evidence Citations */}
            {simulationResult.evidence.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-slate-800/60 text-xs">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  Grounded Evidence Supporting Simulation:
                </span>
                <div className="space-y-1.5">
                  {simulationResult.evidence.map((ev: string, idx: number) => (
                    <div
                      key={idx}
                      className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg font-mono text-[11px] text-cyan-300/90 leading-relaxed"
                    >
                      {ev}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* New Scenario Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-[#0b1120] border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <GitBranch className="w-5 h-5 text-purple-400" />
                <h2 className="text-base font-bold text-white">Create What-If Scenario</h2>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateScenario} className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-slate-300 font-semibold">Scenario Name *</label>
                <input
                  type="text"
                  required
                  value={newScenarioName}
                  onChange={(e) => setNewScenarioName(e.target.value)}
                  placeholder="e.g. Severe Time Crunch (2h/day)"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-semibold">Description</label>
                <textarea
                  rows={2}
                  value={newScenarioDesc}
                  onChange={(e) => setNewScenarioDesc(e.target.value)}
                  placeholder="What hypothetical constraint or perturbation are you testing?"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-end space-x-2">
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
                  className="px-4 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-xl font-semibold shadow-lg shadow-purple-500/20"
                >
                  Create & Run
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
