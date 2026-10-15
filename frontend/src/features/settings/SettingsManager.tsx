import React, { useState, useEffect } from 'react';
import {
  Settings,
  Cpu,
  Database,
  Layers,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Save,
  Sliders,
  Zap,
  Info,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type { SettingsItem } from '../../types';

export const SettingsManager: React.FC = () => {
  const [settings, setSettings] = useState<SettingsItem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [engineStatus, setEngineStatus] = useState<any | null>(null);

  // Form edit states
  const [topK, setTopK] = useState<number>(5);
  const [relevanceThreshold, setRelevanceThreshold] = useState<number>(0.35);
  const [apiKeyInput, setApiKeyInput] = useState<string>('');

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getSettings();
      setSettings(data);
      setTopK(data.default_top_k);
      setRelevanceThreshold(data.default_relevance_threshold);
    } catch (err: any) {
      setError(err.message || 'Failed to load system settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);
      const payload: any = {
        default_top_k: topK,
        default_relevance_threshold: relevanceThreshold,
      };
      if (apiKeyInput.trim()) {
        payload.gemini_api_key = apiKeyInput.trim();
      }

      const updated = await apiService.updateSettings(payload);
      setSettings(updated);
      setApiKeyInput('');
      setSuccessMsg('Settings updated successfully!');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleVerifyEngine = async () => {
    try {
      setVerifying(true);
      setError(null);
      const res = await apiService.verifyEngine();
      setEngineStatus(res);
      setSuccessMsg('AI engine verification check succeeded: Connected.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err.message || 'AI engine verification failed.');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-gradient-to-tr from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 rounded-xl text-cyan-400 shadow-md">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              System Configuration & AI Settings
              <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/60 uppercase">
                v{settings?.version || '1.0.0'}
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Inspect underlying LLM provider, ChromaDB vector store parameters, and runtime RAG thresholds.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleVerifyEngine}
            disabled={verifying}
            className="px-3.5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-purple-500/20 flex items-center gap-1.5 cursor-pointer transition-all"
          >
            <Zap className={`w-3.5 h-3.5 ${verifying ? 'animate-spin' : ''}`} />
            <span>{verifying ? 'Testing Engines...' : 'Test AI Engine'}</span>
          </button>

          <button
            onClick={loadSettings}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
            <span>Reload</span>
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

      {successMsg && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-800/60 rounded-xl flex items-center gap-2 text-emerald-300 text-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Engine Status Callout if verified */}
      {engineStatus && (
        <div className="p-4 bg-cyan-950/20 border border-cyan-800/40 rounded-xl text-xs flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-cyan-300">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span>{engineStatus.message}</span>
          </div>
          <div className="flex items-center gap-3 font-mono text-[11px]">
            <span className={engineStatus.vector_store_connected ? 'text-emerald-400' : 'text-rose-400'}>
              Vector Store: {engineStatus.vector_store_connected ? 'HEALTHY' : 'OFFLINE'}
            </span>
            <span className={engineStatus.llm_configured ? 'text-emerald-400' : 'text-amber-400'}>
              LLM: {engineStatus.llm_configured ? 'AUTHENTICATED' : 'KEY REQUIRED'}
            </span>
          </div>
        </div>
      )}

      {/* Architecture Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        {/* LLM Engine */}
        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white uppercase text-xs flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-cyan-400" />
              AI Reasoning Engine
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${settings?.llm_configured ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-amber-950 text-amber-300 border border-amber-800'}`}>
              {settings?.llm_configured ? 'CONFIGURED' : 'KEY REQUIRED'}
            </span>
          </div>
          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between text-slate-400">
              <span>Provider:</span>
              <span className="text-white font-medium">{settings?.llm_provider || 'Gemini'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Model:</span>
              <span className="text-cyan-400 font-mono">{settings?.llm_model || 'gemini-2.5-flash'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Grounding Mode:</span>
              <span className="text-slate-300">Strict RAG & Zero Fabrication</span>
            </div>
          </div>
        </div>

        {/* Vector Store */}
        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white uppercase text-xs flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-purple-400" />
              Vector Memory (RAG)
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
              ONLINE
            </span>
          </div>
          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between text-slate-400">
              <span>Engine:</span>
              <span className="text-white font-medium">{settings?.vector_store_type || 'ChromaDB'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Embedding Model:</span>
              <span className="text-purple-400 font-mono text-[11px] truncate max-w-[150px]">
                {settings?.embedding_model || 'all-MiniLM-L6-v2'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Chunking Size:</span>
              <span className="text-slate-300 font-mono">{settings?.chunk_size || 500} tokens</span>
            </div>
          </div>
        </div>

        {/* Relational Storage */}
        <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-bold text-white uppercase text-xs flex items-center gap-1.5">
              <Database className="w-4 h-4 text-indigo-400" />
              Persistent Relational DB
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
              SQLITE ONLINE
            </span>
          </div>
          <div className="space-y-1.5 pt-1">
            <div className="flex justify-between text-slate-400">
              <span>Database Engine:</span>
              <span className="text-white font-medium capitalize">{settings?.database_type || 'SQLite'}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Storage Path:</span>
              <span className="text-indigo-400 font-mono text-[10px] truncate max-w-[160px]">
                {settings?.database_path || 'data/lifeops.db'}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Environment:</span>
              <span className="text-slate-300 uppercase font-mono">{settings?.environment || 'development'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Runtime Parameter Adjustments Form */}
      <form onSubmit={handleSaveSettings} className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl space-y-5">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
          <Sliders className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Runtime RAG & Retrieval Tuning
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
          {/* Default Top-K Slider */}
          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-slate-300 font-semibold">
                Default Candidate Chunks (Top-K)
              </label>
              <span className="font-mono text-cyan-400 font-bold text-sm">{topK}</span>
            </div>
            <input
              type="range"
              min={1}
              max={15}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>1 (Minimal)</span>
              <span>5 (Recommended)</span>
              <span>15 (Broad)</span>
            </div>
          </div>

          {/* Default Relevance Threshold */}
          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-slate-300 font-semibold">
                Default Relevance Threshold
              </label>
              <span className="font-mono text-cyan-400 font-bold text-sm">
                {(relevanceThreshold * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range"
              min={0.1}
              max={0.8}
              step={0.05}
              value={relevanceThreshold}
              onChange={(e) => setRelevanceThreshold(Number(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>10% (Permissive)</span>
              <span>35% (Recommended)</span>
              <span>80% (Strict)</span>
            </div>
          </div>
        </div>

        {/* Optional Gemini API Key input */}
        <div className="space-y-1.5 text-xs">
          <label className="text-slate-300 font-semibold flex items-center gap-1.5">
            <span>Gemini API Key (Optional Update)</span>
            <span className="text-[10px] text-slate-500 font-normal">
              — Leave blank to preserve active environment key
            </span>
          </label>
          <input
            type="password"
            value={apiKeyInput}
            onChange={(e) => setApiKeyInput(e.target.value)}
            placeholder="AIzaSy... (Enter new key to update)"
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono text-xs"
          />
        </div>

        <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Info className="w-3.5 h-3.5 text-slate-500" />
            <span>Updates take effect immediately across all background and reasoning services.</span>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-cyan-500/20 flex items-center gap-2 cursor-pointer transition-all disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving Settings...' : 'Save Settings'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
export default SettingsManager;
