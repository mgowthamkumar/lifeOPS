import React, { useState, useEffect } from 'react';
import {
  Activity,
  Database,
  ListTodo,
  Target,
  Sparkles,
  Compass,
  GitBranch,
  Search,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
  Clock,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type { DashboardStats, NavTab } from '../../types';

interface DashboardProps {
  onNavigate: (tab: NavTab) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getDashboardStats();
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const getEntityIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case 'TASK':
        return <ListTodo className="w-3.5 h-3.5 text-blue-400" />;
      case 'GOAL':
        return <Target className="w-3.5 h-3.5 text-indigo-400" />;
      case 'DECISION':
        return <Compass className="w-3.5 h-3.5 text-cyan-400" />;
      case 'DOCUMENT':
        return <Database className="w-3.5 h-3.5 text-purple-400" />;
      case 'SCENARIO':
        return <GitBranch className="w-3.5 h-3.5 text-pink-400" />;
      case 'EVIDENCE':
        return <Search className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Activity className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Hero Welcome Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-[#0e1629] to-slate-900 border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium mb-3">
            <ShieldCheck className="w-3.5 h-3.5" /> Full Product Integration Operational
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white">
            LifeOps Central Intelligence Command
          </h2>
          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
            All 10 modules are persistently integrated: Knowledge Base, RAG Retrieval, Tasks & Goals, AI Action Planner, Decision Intelligence, What-If Simulation, and Grounded Evidence Auditing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadStats}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-800/80 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700/80 flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Refresh Telemetry</span>
          </button>
          <button
            onClick={() => onNavigate('planner')}
            className="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-purple-500/20 flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Plan Today</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-800/60 rounded-xl flex items-center justify-between text-rose-300 text-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-white font-bold ml-4">
            ×
          </button>
        </div>
      )}

      {/* Aggregate Telemetry Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Knowledge & Documents */}
        <div
          onClick={() => onNavigate('knowledge')}
          className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-purple-500/40 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase text-slate-400">Knowledge Memory</span>
            <Database className="w-4 h-4 text-purple-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {stats ? stats.documents_count : '...'} <span className="text-xs font-normal text-slate-400 font-sans">Docs</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center justify-between">
            <span>{stats?.collections_count ?? 0} Collections</span>
            <span>{stats?.chunks_count ?? 0} Chroma Chunks</span>
          </div>
        </div>

        {/* Tasks & Execution */}
        <div
          onClick={() => onNavigate('tasks')}
          className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-blue-500/40 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase text-slate-400">Tasks Queue</span>
            <ListTodo className="w-4 h-4 text-blue-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {stats ? stats.tasks_pending : '...'} <span className="text-xs font-normal text-slate-400 font-sans">Pending</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center justify-between">
            <span className="text-emerald-400 font-semibold">{stats?.tasks_completed ?? 0} completed</span>
            {stats && stats.tasks_urgent > 0 && (
              <span className="text-amber-400 font-semibold">{stats.tasks_urgent} urgent</span>
            )}
          </div>
        </div>

        {/* Goals & Outcomes */}
        <div
          onClick={() => onNavigate('goals')}
          className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/40 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase text-slate-400">Strategic Goals</span>
            <Target className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {stats ? stats.goals_average_progress : 0}% <span className="text-xs font-normal text-slate-400 font-sans">Avg Progress</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center justify-between">
            <span>{stats?.goals_active ?? 0} active</span>
            <span className="text-emerald-400 font-semibold">{stats?.goals_achieved ?? 0} achieved</span>
          </div>
        </div>

        {/* Decisions & Scenarios */}
        <div
          onClick={() => onNavigate('decisions')}
          className="p-4 rounded-xl bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/40 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase text-slate-400">Decision Intelligence</span>
            <Compass className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {stats ? stats.decisions_total : '...'} <span className="text-xs font-normal text-slate-400 font-sans">Decisions</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center justify-between">
            <span className="text-cyan-400">{stats?.decisions_analyzed ?? 0} analyzed</span>
            <span>{stats?.scenarios_total ?? 0} scenarios</span>
          </div>
        </div>
      </div>

      {/* Two Column Section: Action Plan Showcase + Live Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Latest AI Action Plan Showcase */}
        <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Latest AI Action Plan
                </h3>
              </div>
              {stats?.latest_action_plan_time && (
                <span className="text-[10px] text-slate-500 font-mono">
                  {new Date(stats.latest_action_plan_time).toLocaleDateString()}
                </span>
              )}
            </div>

            {stats?.latest_action_plan_summary ? (
              <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
                <p className="text-xs text-slate-200 leading-relaxed italic">
                  "{stats.latest_action_plan_summary}"
                </p>
                <div className="flex items-center gap-2 text-[11px] text-cyan-400">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Synthesized with deadlines, tasks, and document evidence.</span>
                </div>
              </div>
            ) : (
              <div className="p-6 bg-slate-950/50 border border-slate-800/80 rounded-xl text-center space-y-2">
                <Clock className="w-6 h-6 text-slate-600 mx-auto" />
                <p className="text-xs text-slate-400">No action plan generated yet today.</p>
                <span className="text-[11px] text-slate-500 block">
                  Run the AI Action Planner to synthesize your tasks, goals, and constraints.
                </span>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-400">Grounded Daily Optimization</span>
            <button
              onClick={() => onNavigate('planner')}
              className="text-xs font-semibold text-purple-400 hover:text-purple-300 flex items-center gap-1 cursor-pointer"
            >
              <span>Open Action Planner</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Live Relational Activity Stream */}
        <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Live System Activity Log
                </h3>
              </div>
              <span className="text-[10px] text-emerald-400 font-mono font-semibold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                STREAMING
              </span>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto">
              {stats?.recent_activities && stats.recent_activities.length > 0 ? (
                stats.recent_activities.map((act) => (
                  <div
                    key={act.id}
                    className="p-2.5 bg-slate-950/70 border border-slate-800/80 rounded-lg flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {getEntityIcon(act.entity_type)}
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300">
                        {act.entity_type}
                      </span>
                      <span className="text-slate-300 truncate text-[11px]">
                        {act.details || `${act.action} ${act.entity_type.toLowerCase()}`}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-500 shrink-0 font-mono">
                      {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-xs text-slate-500 italic">
                  No recent activity logged yet.
                </div>
              )}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-400">Audit Trail & Security</span>
            <button
              onClick={() => onNavigate('history')}
              className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1 cursor-pointer"
            >
              <span>View Full History</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Quick Launchpad to All Connected Modules */}
      <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-2xl space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
          <TrendingUp className="w-4 h-4 text-cyan-400" />
          Full System Launchpad (All 10 Connected Engines)
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs">
          <button
            onClick={() => onNavigate('knowledge')}
            className="p-3 bg-slate-950/70 hover:bg-slate-900 border border-slate-800 hover:border-purple-500/40 rounded-xl flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer group"
          >
            <Database className="w-5 h-5 text-purple-400 group-hover:scale-110 transition-transform" />
            <span className="font-semibold text-slate-200">Knowledge</span>
          </button>

          <button
            onClick={() => onNavigate('rag')}
            className="p-3 bg-slate-950/70 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/40 rounded-xl flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer group"
          >
            <Activity className="w-5 h-5 text-cyan-400 group-hover:scale-110 transition-transform" />
            <span className="font-semibold text-slate-200">RAG Chat</span>
          </button>

          <button
            onClick={() => onNavigate('planner')}
            className="p-3 bg-slate-950/70 hover:bg-slate-900 border border-slate-800 hover:border-purple-500/40 rounded-xl flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer group"
          >
            <Sparkles className="w-5 h-5 text-purple-400 group-hover:scale-110 transition-transform" />
            <span className="font-semibold text-slate-200">AI Planner</span>
          </button>

          <button
            onClick={() => onNavigate('decisions')}
            className="p-3 bg-slate-950/70 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/40 rounded-xl flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer group"
          >
            <Compass className="w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform" />
            <span className="font-semibold text-slate-200">Decisions</span>
          </button>

          <button
            onClick={() => onNavigate('scenarios')}
            className="p-3 bg-slate-950/70 hover:bg-slate-900 border border-slate-800 hover:border-pink-500/40 rounded-xl flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer group"
          >
            <GitBranch className="w-5 h-5 text-pink-400 group-hover:scale-110 transition-transform" />
            <span className="font-semibold text-slate-200">What-If</span>
          </button>

          <button
            onClick={() => onNavigate('evidence')}
            className="p-3 bg-slate-950/70 hover:bg-slate-900 border border-slate-800 hover:border-amber-500/40 rounded-xl flex flex-col items-center justify-center gap-2 text-center transition-all cursor-pointer group"
          >
            <Search className="w-5 h-5 text-amber-400 group-hover:scale-110 transition-transform" />
            <span className="font-semibold text-slate-200">Evidence</span>
          </button>
        </div>
      </div>
    </div>
  );
};
export default Dashboard;
