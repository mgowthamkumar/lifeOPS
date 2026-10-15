import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Brain,
  Compass,
  Database,
  GitBranch,
  History,
  ListTodo,
  RefreshCw,
  Search,
  Settings,
  Target,
  Zap,
  Sparkles,
} from 'lucide-react';
import { apiService } from './services/api';
import type { HealthResponse, NavTab } from './types';
import KnowledgeBase from './features/knowledge/KnowledgeBase';
import { RAGInterface } from './features/rag/RAGInterface';
import { GoalsManager } from './features/goals/GoalsManager';
import { TasksManager } from './features/tasks/TasksManager';
import { ActionPlanner } from './features/action_planner/ActionPlanner';
import { DecisionWorkspace } from './features/decisions/DecisionWorkspace';
import { WhatIfSimulator } from './features/scenarios/WhatIfSimulator';
import { EvidenceExplorer } from './features/evidence/EvidenceExplorer';
import { Dashboard } from './features/dashboard/Dashboard';
import { DecisionHistory } from './features/history/DecisionHistory';
import { SettingsManager } from './features/settings/SettingsManager';

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [tasksGoalFilter, setTasksGoalFilter] = useState<string | undefined>(undefined);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = async () => {
    setLoadingHealth(true);
    setHealthError(null);
    try {
      const data = await apiService.getHealth();
      setHealth(data);
      setLastChecked(new Date());
    } catch (err: any) {
      setHealthError(err.message || 'Failed to connect to backend');
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // Poll every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const navItems: { id: NavTab; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <Activity className="w-5 h-5" />, badge: 'LIVE' },
    { id: 'knowledge', label: 'Knowledge Base', icon: <Database className="w-5 h-5" />, badge: 'LIVE' },
    { id: 'rag', label: 'RAG Intelligence', icon: <Zap className="w-5 h-5" />, badge: 'LIVE' },
    { id: 'planner', label: 'AI Action Planner', icon: <Sparkles className="w-5 h-5" />, badge: 'AI' },
    { id: 'tasks', label: 'Tasks', icon: <ListTodo className="w-5 h-5" />, badge: 'LIVE' },
    { id: 'goals', label: 'Goals', icon: <Target className="w-5 h-5" />, badge: 'LIVE' },
    { id: 'decisions', label: 'Decision Workspace', icon: <Compass className="w-5 h-5" />, badge: 'LIVE' },
    { id: 'scenarios', label: 'What-If Simulator', icon: <GitBranch className="w-5 h-5" />, badge: 'SIGNATURE' },
    { id: 'evidence', label: 'Evidence Explorer', icon: <Search className="w-5 h-5" />, badge: 'AUDIT' },
    { id: 'history', label: 'Decision History', icon: <History className="w-5 h-5" />, badge: 'AUDIT' },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" />, badge: 'SYSTEM' },
  ];

  return (
    <div className="flex h-screen bg-[#070b14] text-slate-100 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-[#0d1424] border-r border-slate-800 flex flex-col justify-between shrink-0 select-none">
        <div>
          {/* Logo Brand Header */}
          <div className="p-5 border-b border-slate-800/80 flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="font-bold text-lg tracking-tight text-white flex items-center gap-1.5">
                LifeOps <span className="text-cyan-400 font-extrabold text-xs uppercase px-1.5 py-0.5 bg-cyan-950/80 border border-cyan-800/60 rounded">AI</span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">Decision Intelligence</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                    active
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className={active ? 'text-cyan-400' : 'text-slate-500'}>{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Live Backend Connection Indicator in Sidebar */}
        <div className="p-4 border-t border-slate-800/80 bg-[#090e1a]/80">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">System Link</span>
            <button
              onClick={fetchHealth}
              disabled={loadingHealth}
              title="Refresh connection"
              className="text-slate-400 hover:text-cyan-400 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHealth ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>

          {healthError ? (
            <div className="bg-rose-950/40 border border-rose-800/50 rounded-lg p-2.5">
              <div className="flex items-center space-x-2 text-rose-400 text-xs font-medium">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>Backend Offline</span>
              </div>
              <p className="text-[10px] text-rose-300/70 mt-1 line-clamp-2">{healthError}</p>
            </div>
          ) : health ? (
            <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-2.5 space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">FastAPI:</span>
                <span className="inline-flex items-center gap-1.5 font-medium text-emerald-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  v{health.version}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Database:</span>
                <span className="text-slate-200 font-mono text-[10px]">
                  {health.database.type.toUpperCase()} ({health.database.connected ? 'ONLINE' : 'ERR'})
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-400">AI Engine:</span>
                <span className={`text-[10px] font-medium ${health.llm.configured ? 'text-cyan-400' : 'text-amber-400'}`}>
                  {health.llm.configured ? 'READY' : 'KEY REQUIRED'}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-500 py-1 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-slate-600 animate-pulse"></span>
              Checking connection...
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Header Bar */}
        <header className="h-16 border-b border-slate-800 bg-[#0d1424]/60 backdrop-blur-md px-8 flex items-center justify-between shrink-0 sticky top-0 z-10">
          <div className="flex items-center space-x-3">
            <h1 className="text-lg font-semibold text-white capitalize">
              {activeTab.replace('-', ' ')}
            </h1>
            <span className="text-slate-600">/</span>
            <span className="text-xs text-slate-400 bg-slate-800/60 border border-slate-700/60 px-2 py-0.5 rounded-full">
              Phase 1: Foundation
            </span>
          </div>

          <div className="flex items-center space-x-4">
            {health && (
              <div className="flex items-center space-x-2 text-xs bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
                <span
                  className={`w-2 h-2 rounded-full ${
                    health.status === 'healthy'
                      ? 'bg-emerald-400'
                      : health.status === 'degraded'
                      ? 'bg-amber-400'
                      : 'bg-rose-400'
                  }`}
                ></span>
                <span className="text-slate-300 font-medium capitalize">System Status: {health.status}</span>
                {lastChecked && (
                  <span className="text-slate-500 text-[10px]">
                    ({lastChecked.toLocaleTimeString()})
                  </span>
                )}
              </div>
            )}
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-slate-300">
              LO
            </div>
          </div>
        </header>

        {/* Viewport Container */}
        <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Health Banner If Degraded or Error */}
          {healthError && (
            <div className="p-4 bg-rose-950/30 border border-rose-800/60 rounded-xl flex items-start space-x-3 text-rose-300">
              <AlertCircle className="w-5 h-5 shrink-0 text-rose-400 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-rose-200">Backend Connection Error</h3>
                <p className="text-xs text-rose-300/80 mt-1">
                  Could not reach FastAPI at <code className="bg-rose-900/40 px-1 py-0.5 rounded">/api/health</code>. Ensure the FastAPI backend server is running on port 8000.
                </p>
              </div>
            </div>
          )}

          {health && !health.llm.configured && (
            <div className="p-4 bg-amber-950/20 border border-amber-800/40 rounded-xl flex items-start space-x-3 text-amber-300">
              <Zap className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-amber-200">LLM Provider Configuration Notice</h3>
                <p className="text-xs text-amber-300/80 mt-1">
                  {health.llm.message}. The system foundation is operational. Add your key to <code className="bg-amber-900/40 px-1 py-0.5 rounded text-amber-200">.env</code> when ready for RAG and generation phases.
                </p>
              </div>
            </div>
          )}

          {/* Module Content */}
          {activeTab === 'dashboard' && <Dashboard onNavigate={setActiveTab} />}

          {activeTab === 'knowledge' && <KnowledgeBase />}

          {activeTab === 'rag' && <RAGInterface />}

          {activeTab === 'planner' && <ActionPlanner />}

          {activeTab === 'tasks' && (
            <TasksManager
              initialGoalId={tasksGoalFilter}
              onClearGoalFilter={() => setTasksGoalFilter(undefined)}
            />
          )}

          {activeTab === 'goals' && (
            <GoalsManager
              onSelectGoalForTasks={(goalId) => {
                setTasksGoalFilter(goalId);
                setActiveTab('tasks');
              }}
            />
          )}

          {activeTab === 'decisions' && <DecisionWorkspace />}

          {activeTab === 'scenarios' && <WhatIfSimulator />}

          {activeTab === 'evidence' && <EvidenceExplorer />}

          {activeTab === 'history' && <DecisionHistory />}

          {activeTab === 'settings' && <SettingsManager />}
        </div>
      </main>
    </div>
  );
}
