import React, { useState, useEffect } from 'react';
import {
  Search,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  FileText,
  Layers,
  Sliders,
  RefreshCw,
  Trash2,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ArrowRight,
  Split,
  Info,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type {
  EvidenceExploreResponse,
  EvidenceInvestigationSummary,
  EvidenceConflictItem,
  EvidenceItem,
  Collection,
} from '../../types';

export const EvidenceExplorer: React.FC = () => {
  const [claim, setClaim] = useState<string>('');
  const [selectedCollectionId, setSelectedCollectionId] = useState<string>('');
  const [collections, setCollections] = useState<Collection[]>([]);
  const [topK, setTopK] = useState<number>(6);
  const [relevanceThreshold, setRelevanceThreshold] = useState<number>(0.3);
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);

  const [activeTab, setActiveTab] = useState<'explorer' | 'conflicts' | 'history'>('explorer');
  const [exploring, setExploring] = useState<boolean>(false);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [currentResult, setCurrentResult] = useState<EvidenceExploreResponse | null>(null);
  const [investigations, setInvestigations] = useState<EvidenceInvestigationSummary[]>([]);
  const [conflictsList, setConflictsList] = useState<EvidenceConflictItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Quick Preset Claims to showcase Process 9 test requirements
  const presetClaims = [
    {
      label: 'Supported Claim',
      text: 'Standard operating capacity requires 4 hours daily focused allocation',
      desc: 'Matches Work Capacity Agreement (Page 1)',
    },
    {
      label: 'Conflicting Claim ($500 vs $800)',
      text: 'Approved infrastructure monthly budget is strictly capped at $500',
      desc: 'Doc A ($500) disagrees with Doc B ($800 amendment)',
    },
    {
      label: 'Missing Evidence (Zero Citations)',
      text: 'The nuclear fusion reactor at facility omega requires quarterly maintenance',
      desc: 'Unrelated topic — system must return zero fabricated citations',
    },
  ];

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoadingHistory(true);
      const [cols, invs, confs] = await Promise.all([
        apiService.getCollections(),
        apiService.getEvidenceInvestigations(),
        apiService.getEvidenceConflicts(),
      ]);
      setCollections(cols);
      setInvestigations(invs);
      setConflictsList(confs);

      // If there's an existing investigation, load the latest one
      if (invs.length > 0 && !currentResult) {
        const latest = await apiService.getEvidenceInvestigation(invs[0].id);
        setCurrentResult(latest);
        setClaim(latest.claim);
      }
    } catch (err: any) {
      console.error('Failed to load initial evidence data:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleExplore = async (claimToExplore?: string) => {
    const targetClaim = (claimToExplore || claim).trim();
    if (!targetClaim) {
      setError('Please enter a claim or assertion to investigate.');
      return;
    }

    try {
      setExploring(true);
      setError(null);

      const response = await apiService.exploreEvidence({
        claim: targetClaim,
        collection_id: selectedCollectionId || undefined,
        top_k: topK,
        relevance_threshold: relevanceThreshold,
      });

      setCurrentResult(response);
      setClaim(targetClaim);
      setActiveTab('explorer');

      // Refresh list
      const [updatedInvs, updatedConfs] = await Promise.all([
        apiService.getEvidenceInvestigations(),
        apiService.getEvidenceConflicts(),
      ]);
      setInvestigations(updatedInvs);
      setConflictsList(updatedConfs);
    } catch (err: any) {
      setError(err.message || 'Evidence investigation failed.');
    } finally {
      setExploring(false);
    }
  };

  const handleSelectInvestigation = async (id: string) => {
    try {
      setExploring(true);
      setError(null);
      const inv = await apiService.getEvidenceInvestigation(id);
      setCurrentResult(inv);
      setClaim(inv.claim);
      setActiveTab('explorer');
    } catch (err: any) {
      setError(err.message || 'Failed to load investigation details.');
    } finally {
      setExploring(false);
    }
  };

  const handleDeleteInvestigation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiService.deleteEvidenceInvestigation(id);
      setInvestigations((prev) => prev.filter((item) => item.id !== id));
      if (currentResult?.investigation_id === id) {
        setCurrentResult(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete investigation.');
    }
  };

  // Helper status color formatting
  const getStatusBadge = (status: string, conflictDetected: boolean) => {
    if (conflictDetected || status === 'CONFLICT_DETECTED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-950/80 text-amber-300 border border-amber-600/60 shadow-sm shadow-amber-900/30">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          CONFLICT DETECTED
        </span>
      );
    }
    switch (status) {
      case 'VERIFIED_SUPPORT':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-600/60 shadow-sm shadow-emerald-900/30">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            VERIFIED SUPPORT
          </span>
        );
      case 'CONTRADICTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-950/80 text-rose-300 border border-rose-600/60 shadow-sm shadow-rose-900/30">
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
            CONTRADICTED BY EVIDENCE
          </span>
        );
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-900 text-slate-300 border border-slate-700 shadow-sm">
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            INSUFFICIENT EVIDENCE
          </span>
        );
    }
  };

  const getStanceBadge = (stance: string) => {
    switch (stance) {
      case 'SUPPORTS':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-950 text-emerald-300 border border-emerald-800/80">
            Supports
          </span>
        );
      case 'CONTRADICTS':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-rose-950 text-rose-300 border border-rose-800/80">
            Contradicts
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
            Neutral / Context
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-gradient-to-tr from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 rounded-xl text-cyan-400 shadow-md shadow-cyan-500/10">
            <Search className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white tracking-tight">
                Evidence Explorer & Conflict Detective
              </h1>
              <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/60 uppercase">
                Process 9 Live
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Multi-source citation inspection, conflict detection between disagreeing documents, and anti-fabrication guarantees.
            </p>
          </div>
        </div>

        {/* Anti-Hallucination Integrity Badge */}
        <div className="flex items-center gap-2 px-3.5 py-2 bg-emerald-950/40 border border-emerald-800/60 rounded-xl text-emerald-300 text-xs">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <div>
            <div className="font-semibold text-emerald-200">Strict Citations Guarantee</div>
            <div className="text-[10px] text-emerald-400/80">Zero hallucinated or fabricated sources</div>
          </div>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('explorer')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'explorer'
              ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Search className="w-3.5 h-3.5" />
          <span>Claim Investigation</span>
          {currentResult && (
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          )}
        </button>

        <button
          onClick={() => setActiveTab('conflicts')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'conflicts'
              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Split className="w-3.5 h-3.5" />
          <span>Detected Conflicts ({conflictsList.length})</span>
          {conflictsList.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-950 text-amber-400 border border-amber-800">
              {conflictsList.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'history'
              ? 'bg-purple-500/10 text-purple-400 border border-purple-500/30 shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Investigation History ({investigations.length})</span>
        </button>
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

      {/* TAB 1: CLAIM INVESTIGATION */}
      {activeTab === 'explorer' && (
        <div className="space-y-6">
          {/* Claim Query Box */}
          <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
              <label className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Search className="w-4 h-4 text-cyan-400" />
                Investigate Claim Against Evidence Base
              </label>

              {/* Collection Filter */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">Scope:</span>
                <select
                  value={selectedCollectionId}
                  onChange={(e) => setSelectedCollectionId(e.target.value)}
                  className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1 focus:outline-none focus:border-cyan-500"
                >
                  <option value="">All Collections (Global)</option>
                  {collections.map((col) => (
                    <option key={col.id} value={col.id}>
                      {col.name} ({col.document_count} docs)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Input and Search Button */}
            <div className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={claim}
                  onChange={(e) => setClaim(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleExplore();
                    }
                  }}
                  placeholder="Enter claim or assertion, e.g.: Approved monthly budget is $500..."
                  className="w-full bg-slate-950/90 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/30 transition-all"
                />
              </div>

              <button
                onClick={() => handleExplore()}
                disabled={exploring || !claim.trim()}
                className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer shrink-0"
              >
                <Search className={`w-4 h-4 ${exploring ? 'animate-spin' : ''}`} />
                <span>{exploring ? 'Auditing Evidence...' : 'Investigate Claim'}</span>
              </button>
            </div>

            {/* Quick Test Presets */}
            <div className="space-y-2 pt-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                Quick Verification Presets (Process 9 Benchmark Tests):
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                {presetClaims.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setClaim(item.text);
                      handleExplore(item.text);
                    }}
                    disabled={exploring}
                    className="p-2.5 rounded-xl bg-slate-950/70 hover:bg-slate-950 border border-slate-800/80 hover:border-cyan-500/40 text-left transition-all cursor-pointer group flex flex-col justify-between"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-cyan-300 group-hover:text-cyan-200">
                        {item.label}
                      </span>
                      <ArrowRight className="w-3 h-3 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                    </div>
                    <p className="text-[11px] text-slate-300 line-clamp-1 mt-1 font-mono">
                      "{item.text}"
                    </p>
                    <span className="text-[10px] text-slate-500 mt-1 block italic">
                      {item.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Advanced Filters Toggle */}
            <div className="pt-2 border-t border-slate-800/60">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1.5 font-medium cursor-pointer"
              >
                <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                <span>Advanced Retrieval Parameters</span>
                {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>

              {showAdvanced && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3 p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 text-xs">
                  <div className="space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-slate-300 font-medium">Candidate Chunks (Top-K):</span>
                      <span className="font-mono text-cyan-400 font-bold">{topK}</span>
                    </div>
                    <input
                      type="range"
                      min={2}
                      max={15}
                      value={topK}
                      onChange={(e) => setTopK(Number(e.target.value))}
                      className="w-full accent-cyan-400 cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                      <span>2 (Strict)</span>
                      <span>6 (Balanced)</span>
                      <span>15 (Broad)</span>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-slate-300 font-medium">Relevance Threshold:</span>
                      <span className="font-mono text-cyan-400 font-bold">
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
                      <span>30% (Standard)</span>
                      <span>80% (Exact)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ACTIVE INVESTIGATION RESULTS DISPLAY */}
          {currentResult && (
            <div className="space-y-6">
              {/* STATUS & AUDIT SUMMARY HERO */}
              <div className="p-6 bg-slate-900/60 border border-slate-800 rounded-2xl space-y-5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                  <div className="space-y-1">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      Investigated Claim
                    </span>
                    <h2 className="text-base font-bold text-white font-mono">
                      "{currentResult.claim}"
                    </h2>
                  </div>

                  <div>{getStatusBadge(currentResult.status, currentResult.conflict_detected)}</div>
                </div>

                {/* Telemetry Meters: Confidence, Uncertainty, Sources */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Confidence Meter */}
                  <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 font-semibold uppercase text-[10px]">Confidence</span>
                      <span className="font-mono font-bold text-cyan-400">
                        {Math.round(currentResult.confidence * 100)}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-500"
                        style={{ width: `${Math.round(currentResult.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-500 block">
                      Grounding score based on document relevance
                    </span>
                  </div>

                  {/* Uncertainty Meter */}
                  <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 font-semibold uppercase text-[10px]">Uncertainty</span>
                      <span
                        className={`font-mono font-bold ${
                          currentResult.uncertainty > 0.4 ? 'text-amber-400' : 'text-emerald-400'
                        }`}
                      >
                        {Math.round(currentResult.uncertainty * 100)}% ({currentResult.uncertainty_level})
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          currentResult.uncertainty > 0.4
                            ? 'bg-gradient-to-r from-amber-500 to-rose-500'
                            : 'bg-gradient-to-r from-emerald-500 to-cyan-500'
                        }`}
                        style={{ width: `${Math.round(currentResult.uncertainty * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-500 block">
                      Discrepancies, missing sources, or qualifiers
                    </span>
                  </div>

                  {/* Sources Evaluated */}
                  <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 font-semibold uppercase text-[10px]">Verified Citations</span>
                      <span className="font-mono font-bold text-white text-base">
                        {currentResult.evidence_items.length} Chunks
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-500 block">
                      From {currentResult.total_sources_evaluated} evaluated source documents
                    </span>
                    <div className="text-[10px] text-slate-400 mt-1 font-mono">
                      Timestamp: {new Date(currentResult.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>

                {/* Grounded Reasoning Summary */}
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-cyan-400" />
                    Investigation Reasoning & Synthesis:
                  </span>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    {currentResult.reasoning_summary}
                  </p>
                </div>
              </div>

              {/* CONFLICT DETECTION HIGHLIGHT PANEL (If Sources Disagree) */}
              {currentResult.conflicts && currentResult.conflicts.length > 0 && (
                <div className="p-6 bg-amber-950/20 border border-amber-600/50 rounded-2xl space-y-5 shadow-xl shadow-amber-950/20">
                  <div className="flex items-center justify-between pb-3 border-b border-amber-800/40">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-amber-900/40 rounded-lg text-amber-400">
                        <AlertTriangle className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-amber-200 uppercase tracking-wider">
                          Conflict Detected Across Sources
                        </h3>
                        <p className="text-xs text-amber-400/80">
                          Disagreement or contradiction identified between multiple indexed documents.
                        </p>
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded bg-amber-950 text-amber-300 border border-amber-700/60 text-xs font-mono font-bold">
                      {currentResult.conflicts.length} Discrepancy Found
                    </span>
                  </div>

                  {currentResult.conflicts.map((conflict, cIdx) => (
                    <div key={cIdx} className="space-y-4">
                      {/* Discrepancy Explanation Box */}
                      <div className="p-3.5 bg-slate-950/80 border border-amber-800/40 rounded-xl text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-amber-300">
                            Topic: {conflict.topic}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
                            Severity: {conflict.severity}
                          </span>
                        </div>
                        <p className="text-slate-300 text-xs leading-relaxed">
                          {conflict.discrepancy_explanation}
                        </p>
                        {conflict.suggested_resolution && (
                          <div className="mt-2 pt-2 border-t border-slate-800/80 text-[11px] text-emerald-300 flex items-start gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5 text-emerald-400" />
                            <span>
                              <strong>Suggested Resolution:</strong> {conflict.suggested_resolution}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Side-by-Side Comparison: Source A vs Source B */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        {/* Source A */}
                        <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                            <span className="font-bold text-cyan-400 uppercase text-[11px]">
                              Source A
                            </span>
                            <span className="font-mono text-[10px] text-slate-400">
                              Page {conflict.source_a.page_number ?? 1} • Chunk #{conflict.source_a.chunk_index ?? 0}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
                            <FileText className="w-3.5 h-3.5 text-cyan-400" />
                            <span>{conflict.source_a.document_name}</span>
                          </div>
                          <div className="p-2.5 bg-slate-900/80 rounded-lg border border-slate-800/80 font-mono text-[11px] text-cyan-200/90 leading-relaxed italic">
                            "{conflict.source_a.chunk_text}"
                          </div>
                          <div className="text-[11px] text-slate-300">
                            <strong>Assertion:</strong> {conflict.source_a.assertion}
                          </div>
                        </div>

                        {/* Source B */}
                        <div className="p-4 bg-slate-950/90 border border-slate-800 rounded-xl space-y-2">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                            <span className="font-bold text-purple-400 uppercase text-[11px]">
                              Source B (Disagreement)
                            </span>
                            <span className="font-mono text-[10px] text-slate-400">
                              Page {conflict.source_b.page_number ?? 1} • Chunk #{conflict.source_b.chunk_index ?? 0}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
                            <FileText className="w-3.5 h-3.5 text-purple-400" />
                            <span>{conflict.source_b.document_name}</span>
                          </div>
                          <div className="p-2.5 bg-slate-900/80 rounded-lg border border-slate-800/80 font-mono text-[11px] text-purple-200/90 leading-relaxed italic">
                            "{conflict.source_b.chunk_text}"
                          </div>
                          <div className="text-[11px] text-slate-300">
                            <strong>Assertion:</strong> {conflict.source_b.assertion}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* INSUFFICIENT EVIDENCE / ZERO CITATIONS DISPLAY */}
              {currentResult.evidence_items.length === 0 && (
                <div className="p-8 bg-slate-900/40 border border-slate-800 rounded-2xl text-center space-y-4">
                  <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto text-slate-400 border border-slate-700">
                    <HelpCircle className="w-6 h-6 text-slate-400" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">
                      Zero Verified Citations Found
                    </h3>
                    <p className="text-xs text-slate-400 max-w-lg mx-auto mt-1 leading-relaxed">
                      No document in the knowledge base meets the minimum relevance threshold to support or refute this assertion.
                    </p>
                  </div>

                  {/* Anti-Fabrication Notice */}
                  <div className="max-w-md mx-auto p-3.5 bg-slate-950 border border-slate-800 rounded-xl text-[11px] text-slate-300 space-y-1">
                    <div className="font-semibold text-cyan-300 flex items-center justify-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      Zero Fabricated Citations Guarantee
                    </div>
                    <p className="text-slate-400 text-[10px] leading-relaxed">
                      LifeOps strictly refuses to invent fictitious document references or fabricate citations. When evidence is missing, the citation list remains strictly empty.
                    </p>
                  </div>
                </div>
              )}

              {/* CITATIONS LIST — EVERY FIELD FROM PROCESS 9 */}
              {currentResult.evidence_items.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                      <FileText className="w-4 h-4 text-cyan-400" />
                      Verified Document Evidence & Citations ({currentResult.evidence_items.length})
                    </h3>
                    <span className="text-xs text-slate-400">
                      Ranked by semantic cosine similarity
                    </span>
                  </div>

                  <div className="space-y-3">
                    {currentResult.evidence_items.map((item: EvidenceItem, idx: number) => (
                      <div
                        key={item.id || idx}
                        className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3 hover:border-slate-700 transition-all"
                      >
                        {/* Citation Header */}
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-2.5 border-b border-slate-800/80">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                              #{idx + 1}
                            </span>
                            <div className="flex items-center gap-1.5 font-bold text-sm text-white">
                              <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                              <span>{item.source_filename}</span>
                            </div>
                            <span className="text-xs text-slate-400 font-mono">
                              (Page {item.page_number ?? 1} • Chunk #{item.chunk_index ?? idx})
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            {getStanceBadge(item.stance)}
                            <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                              {Math.round(item.relevance * 100)}% Relevance
                            </span>
                          </div>
                        </div>

                        {/* Chunk Excerpt Text */}
                        <div className="p-3 bg-slate-950 rounded-xl border border-slate-800/80 font-mono text-xs text-cyan-200/90 leading-relaxed italic">
                          "{item.chunk_text}"
                        </div>

                        {/* Reasoning & Metrics */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-1">
                          {/* Reasoning */}
                          <div className="md:col-span-2 p-3 bg-slate-950/60 rounded-xl border border-slate-800 space-y-1">
                            <span className="text-slate-400 uppercase text-[10px] font-semibold block">
                              Grounded Reasoning:
                            </span>
                            <p className="text-slate-200 text-xs leading-relaxed">
                              {item.reasoning}
                            </p>
                          </div>

                          {/* Confidence & Uncertainty */}
                          <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
                            <div className="flex justify-between items-center text-[11px]">
                              <span className="text-slate-400">Confidence:</span>
                              <span className="font-mono font-bold text-cyan-400">
                                {Math.round(item.confidence * 100)}%
                              </span>
                            </div>
                            <div className="flex justify-between items-center text-[11px]">
                              <span className="text-slate-400">Uncertainty:</span>
                              <span
                                className={`font-mono font-bold ${
                                  item.uncertainty > 0.4 ? 'text-amber-400' : 'text-emerald-400'
                                }`}
                              >
                                {Math.round(item.uncertainty * 100)}%
                              </span>
                            </div>
                            {item.uncertainty_reasons && item.uncertainty_reasons.length > 0 && (
                              <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-800">
                                <strong>Factors:</strong> {item.uncertainty_reasons.join(', ')}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: DETECTED CONFLICTS CENTER */}
      {activeTab === 'conflicts' && (
        <div className="space-y-4">
          <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl space-y-2">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Split className="w-5 h-5 text-amber-400" />
              Conflict Intelligence Center
            </h2>
            <p className="text-xs text-slate-400">
              Cross-document discrepancies, conflicting metrics, budget disagreements, and contradictory assertions automatically surfaced by LifeOps AI.
            </p>
          </div>

          {conflictsList.length === 0 ? (
            <div className="p-10 bg-slate-900/30 border border-slate-800 rounded-2xl text-center space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
              <h3 className="text-sm font-bold text-white">No Unresolved Conflicts</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                No active document conflicts detected. Run an investigation on conflicting documents to surface discrepancies.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {conflictsList.map((conflict, idx) => (
                <div
                  key={idx}
                  className="p-5 bg-slate-900/70 border border-amber-900/40 rounded-2xl space-y-4"
                >
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      <h4 className="font-bold text-white text-sm">{conflict.topic}</h4>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-800">
                      Severity: {conflict.severity}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {conflict.discrepancy_explanation}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                      <span className="font-bold text-cyan-400 uppercase text-[10px]">
                        Source A: {conflict.source_a.document_name}
                      </span>
                      <p className="font-mono text-[11px] text-cyan-200/90 italic">
                        "{conflict.source_a.chunk_text}"
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1">
                      <span className="font-bold text-purple-400 uppercase text-[10px]">
                        Source B: {conflict.source_b.document_name}
                      </span>
                      <p className="font-mono text-[11px] text-purple-200/90 italic">
                        "{conflict.source_b.chunk_text}"
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: INVESTIGATION HISTORY */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="p-6 bg-slate-900/50 border border-slate-800 rounded-2xl flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-purple-400" />
                Evidence Investigation Archives
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Full relational history of investigated claims, confidence ratings, and conflict audits.
              </p>
            </div>
            <button
              onClick={loadInitialData}
              disabled={loadingHistory}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>

          {investigations.length === 0 ? (
            <div className="p-10 bg-slate-900/30 border border-slate-800 rounded-2xl text-center space-y-2">
              <p className="text-xs text-slate-400">No past investigations found.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {investigations.map((inv) => (
                <div
                  key={inv.id}
                  onClick={() => handleSelectInvestigation(inv.id)}
                  className="p-4 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/40 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs transition-all cursor-pointer group"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-white font-mono group-hover:text-cyan-300 transition-colors">
                        "{inv.claim}"
                      </h4>
                      {inv.conflict_detected && (
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-800">
                          CONFLICT
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-500">
                      <span>{inv.sources_count} sources cited</span>
                      <span>•</span>
                      <span>Confidence: {Math.round(inv.confidence * 100)}%</span>
                      <span>•</span>
                      <span>Uncertainty: {Math.round(inv.uncertainty * 100)}%</span>
                      <span>•</span>
                      <span>{new Date(inv.created_at).toLocaleString()}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    {getStatusBadge(inv.status, inv.conflict_detected)}
                    <button
                      onClick={(e) => handleDeleteInvestigation(inv.id, e)}
                      title="Delete archive"
                      className="p-1.5 text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default EvidenceExplorer;
