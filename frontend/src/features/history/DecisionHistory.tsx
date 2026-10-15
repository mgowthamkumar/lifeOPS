import React, { useState, useEffect } from 'react';
import {
  History,
  Trash2,
  RefreshCw,
  Filter,
  CheckCircle2,
  Database,
  ListTodo,
  Target,
  Compass,
  GitBranch,
  Search,
  Activity,
  AlertTriangle,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type { ActivityLogItem, ActivityStats } from '../../types';

export const DecisionHistory: React.FC = () => {
  const [logs, setLogs] = useState<ActivityLogItem[]>([]);
  const [stats, setStats] = useState<ActivityStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('ALL');

  const filterTabs = [
    { id: 'ALL', label: 'All Activities' },
    { id: 'TASK', label: 'Tasks' },
    { id: 'GOAL', label: 'Goals' },
    { id: 'DECISION', label: 'Decisions' },
    { id: 'DOCUMENT', label: 'Documents' },
    { id: 'SCENARIO', label: 'Scenarios' },
    { id: 'EVIDENCE', label: 'Evidence' },
  ];

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const [logData, statsData] = await Promise.all([
        apiService.getHistory(filterType === 'ALL' ? undefined : filterType, 100),
        apiService.getHistoryStats(),
      ]);
      setLogs(logData);
      setStats(statsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load activity history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [filterType]);

  const handleClearHistory = async () => {
    if (!confirm('Are you sure you want to clear your activity audit history? This action cannot be undone.')) {
      return;
    }
    try {
      setLoading(true);
      await apiService.clearHistory();
      await loadHistory();
    } catch (err: any) {
      setError(err.message || 'Failed to clear activity history.');
    } finally {
      setLoading(false);
    }
  };

  const getEntityIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case 'TASK':
        return <ListTodo className="w-4 h-4 text-blue-400" />;
      case 'GOAL':
        return <Target className="w-4 h-4 text-indigo-400" />;
      case 'DECISION':
        return <Compass className="w-4 h-4 text-cyan-400" />;
      case 'DOCUMENT':
        return <Database className="w-4 h-4 text-purple-400" />;
      case 'SCENARIO':
        return <GitBranch className="w-4 h-4 text-pink-400" />;
      case 'EVIDENCE':
        return <Search className="w-4 h-4 text-amber-400" />;
      default:
        return <Activity className="w-4 h-4 text-slate-400" />;
    }
  };

  const getActionBadge = (action: string) => {
    let color = 'bg-slate-800 text-slate-300 border-slate-700';
    if (action.includes('CREATED') || action.includes('UPLOADED') || action.includes('ANSWERED')) {
      color = 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80';
    } else if (action.includes('UPDATED') || action.includes('MODIFIED')) {
      color = 'bg-blue-950/80 text-blue-300 border-blue-800/80';
    } else if (action.includes('DELETED') || action.includes('PURGED')) {
      color = 'bg-rose-950/80 text-rose-300 border-rose-800/80';
    } else if (action.includes('ANALYZED') || action.includes('SIMULATED') || action.includes('EXPLORED')) {
      color = 'bg-purple-950/80 text-purple-300 border-purple-800/80';
    }

    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${color}`}>
        {action}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-gradient-to-tr from-cyan-500/20 to-indigo-600/20 border border-cyan-500/30 rounded-xl text-cyan-400 shadow-md">
            <History className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              Decision & Activity Audit Trail
              <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/60 uppercase">
                Persistent Audit
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Comprehensive chronological telemetry capturing all database mutations, AI generations, and user actions.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadHistory}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleClearHistory}
            disabled={loading || logs.length === 0}
            className="px-3.5 py-2 bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 text-xs font-semibold rounded-xl border border-rose-800/60 flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear History</span>
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

      {/* Telemetry Summary Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3 text-xs">
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Total Events</span>
            <span className="text-lg font-bold text-white font-mono">{stats.total_events}</span>
          </div>
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Decisions</span>
            <span className="text-lg font-bold text-cyan-400 font-mono">
              {stats.by_entity_type['DECISION'] || 0}
            </span>
          </div>
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Tasks</span>
            <span className="text-lg font-bold text-blue-400 font-mono">
              {stats.by_entity_type['TASK'] || 0}
            </span>
          </div>
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Goals</span>
            <span className="text-lg font-bold text-indigo-400 font-mono">
              {stats.by_entity_type['GOAL'] || 0}
            </span>
          </div>
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Documents</span>
            <span className="text-lg font-bold text-purple-400 font-mono">
              {stats.by_entity_type['DOCUMENT'] || 0}
            </span>
          </div>
          <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
            <span className="text-[10px] text-slate-400 uppercase font-semibold block">Simulations</span>
            <span className="text-lg font-bold text-pink-400 font-mono">
              {stats.by_entity_type['SCENARIO'] || 0}
            </span>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-800 pb-2">
        <Filter className="w-3.5 h-3.5 text-slate-500 mr-1" />
        {filterTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilterType(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              filterType === tab.id
                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Activity Event Feed */}
      <div className="space-y-3">
        {logs.length === 0 ? (
          <div className="p-12 bg-slate-900/30 border border-slate-800 rounded-2xl text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto" />
            <h3 className="text-sm font-bold text-white">No Activity Events Found</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Any tasks created, goals updated, AI plans synthesized, or documents uploaded will appear in this real-time audit trail.
            </p>
          </div>
        ) : (
          logs.map((log) => (
            <div
              key={log.id}
              className="p-4 bg-slate-900/60 hover:bg-slate-900/90 border border-slate-800 hover:border-slate-700/80 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs transition-all"
            >
              <div className="flex items-start md:items-center gap-3 min-w-0">
                <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 shrink-0 mt-0.5 md:mt-0">
                  {getEntityIcon(log.entity_type)}
                </div>
                <div className="space-y-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-white text-xs">{log.entity_type}</span>
                    {getActionBadge(log.action)}
                    {log.entity_id && (
                      <span className="font-mono text-[10px] text-slate-500 truncate max-w-[150px]">
                        ID: {log.entity_id}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-300 text-xs leading-relaxed">
                    {log.details || `Performed ${log.action} on ${log.entity_type}`}
                  </p>
                </div>
              </div>

              <div className="text-right shrink-0">
                <span className="text-[11px] text-slate-400 font-mono block">
                  {new Date(log.created_at).toLocaleDateString()}
                </span>
                <span className="text-[10px] text-slate-500 font-mono block">
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
export default DecisionHistory;
