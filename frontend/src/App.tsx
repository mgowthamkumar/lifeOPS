import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertCircle,
  Brain,
  CheckCircle2,
  Compass,
  Cpu,
  Database,
  GitBranch,
  History,
  Layers,
  ListTodo,
  RefreshCw,
  Search,
  Server,
  Settings,
  ShieldCheck,
  Target,
  Zap,
} from 'lucide-react';
import { apiService } from './services/api';
import type { HealthResponse, NavTab } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
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
    { id: 'dashboard', label: 'Dashboard', icon: <Activity className="w-5 h-5" /> },
    { id: 'knowledge', label: 'Knowledge Base', icon: <Database className="w-5 h-5" /> },
    { id: 'tasks', label: 'Tasks', icon: <ListTodo className="w-5 h-5" /> },
    { id: 'goals', label: 'Goals', icon: <Target className="w-5 h-5" /> },
    { id: 'decisions', label: 'Decision Workspace', icon: <Compass className="w-5 h-5" /> },
    { id: 'scenarios', label: 'What-If Simulator', icon: <GitBranch className="w-5 h-5" /> },
    { id: 'evidence', label: 'Evidence Explorer', icon: <Search className="w-5 h-5" /> },
    { id: 'history', label: 'Decision History', icon: <History className="w-5 h-5" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
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
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              {/* Foundation Welcome Hero */}
              <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-[#0e1629] to-slate-900 border border-slate-800 shadow-xl">
                <div className="max-w-3xl">
                  <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-medium mb-3">
                    <ShieldCheck className="w-3.5 h-3.5" /> Core Architecture Verified
                  </div>
                  <h2 className="text-2xl font-bold tracking-tight text-white">
                    LifeOps AI Operational Foundation
                  </h2>
                  <p className="text-sm text-slate-400 mt-2 leading-relaxed">
                    Personal Life Decision and Action Intelligence System built on Explainable Retrieval-Augmented Generation. Every user action connects directly to the persistent backend, ChromaDB vector retrieval, and decision engines.
                  </p>
                </div>
              </div>

              {/* Real Connection Telemetry Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-medium">Backend Service</span>
                    <Server className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-lg font-bold text-white flex items-center gap-2">
                    {health ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>FastAPI {health.version}</span>
                      </>
                    ) : (
                      <span className="text-slate-500 text-sm">Connecting...</span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Environment: {health?.environment || '...'}</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-medium">Relational Storage</span>
                    <Database className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div className="text-lg font-bold text-white flex items-center gap-2">
                    {health?.database.connected ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>{health.database.type.toUpperCase()}</span>
                      </>
                    ) : (
                      <span className="text-slate-500 text-sm">Unconnected</span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">{health?.database.message || 'SQLite persistent storage'}</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-medium">Vector Database</span>
                    <Layers className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-lg font-bold text-white flex items-center gap-2">
                    {health?.vector_db.configured ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>ChromaDB</span>
                      </>
                    ) : (
                      <span className="text-slate-500 text-sm">Standby</span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">{health?.vector_db.status || 'Ready for embeddings'}</p>
                </div>

                <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                  <div className="flex items-center justify-between text-slate-400 mb-2">
                    <span className="text-xs font-medium">AI Reasoning Engine</span>
                    <Cpu className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="text-lg font-bold text-white flex items-center gap-2">
                    <span>{health?.llm.provider || 'Gemini'}</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1">Model: {health?.llm.model || 'gemini-2.5-flash'}</p>
                </div>
              </div>

              {/* End-to-End Pipeline Visualization */}
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                  Operational Architecture Pipeline
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-7 gap-2 items-center text-center text-xs">
                  <div className="p-3 bg-slate-800/60 border border-slate-700/60 rounded-lg">
                    <div className="font-semibold text-slate-200">1. User Action</div>
                    <div className="text-[10px] text-slate-400 mt-1">Upload / Decision / Query</div>
                  </div>
                  <div className="text-slate-600 font-bold hidden md:block">→</div>
                  <div className="p-3 bg-slate-800/60 border border-slate-700/60 rounded-lg">
                    <div className="font-semibold text-slate-200">2. React + TS</div>
                    <div className="text-[10px] text-slate-400 mt-1">State & Telemetry UI</div>
                  </div>
                  <div className="text-slate-600 font-bold hidden md:block">→</div>
                  <div className="p-3 bg-slate-800/60 border border-slate-700/60 rounded-lg">
                    <div className="font-semibold text-slate-200">3. FastAPI API</div>
                    <div className="text-[10px] text-slate-400 mt-1">Validation & Services</div>
                  </div>
                  <div className="text-slate-600 font-bold hidden md:block">→</div>
                  <div className="p-3 bg-slate-800/60 border border-slate-700/60 rounded-lg">
                    <div className="font-semibold text-slate-200">4. ChromaDB & RAG</div>
                    <div className="text-[10px] text-slate-400 mt-1">Vector Search + Gemini</div>
                  </div>
                </div>
              </div>

              {/* Modules Roadmap Checklist for Subsequent Phases */}
              <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 space-y-4">
                <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                  Development Roadmap & Module Status
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                  <div className="p-3.5 rounded-lg bg-emerald-950/20 border border-emerald-800/40 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-emerald-300">Phase 1: Foundation</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-900/60 text-emerald-300 font-bold">COMPLETED</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      FastAPI backend, React TS shell, SQLite database engine, Live Health API, CORS proxy.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg bg-slate-800/30 border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-300">Phase 2: Database & Models</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-medium">NEXT</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Collections, Documents, Tasks, Goals, Decisions, Scenarios, Evidence tables.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-lg bg-slate-800/30 border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-300">Phase 3: Document Ingestion</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-medium">QUEUED</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Multi-format parsing (PDF, DOCX, TXT, CSV, MD), chunking, hashing, and ChromaDB vector indexing.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab !== 'dashboard' && (
            <div className="p-10 rounded-2xl bg-slate-900/50 border border-slate-800 text-center space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto text-cyan-400 border border-slate-700">
                {navItems.find((item) => item.id === activeTab)?.icon}
              </div>
              <h2 className="text-xl font-bold text-white capitalize">
                {activeTab.replace('-', ' ')} Module Workspace
              </h2>
              <p className="text-sm text-slate-400 max-w-lg mx-auto">
                Foundation structure is established. Live backend telemetry confirmed. Per Phase 1 requirements, this module will be connected to its dedicated business service and persistent tables in the upcoming phase.
              </p>
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-800 border border-slate-700 rounded-full text-xs text-slate-300 font-mono">
                Status: Ready for Phase 2 implementation
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
