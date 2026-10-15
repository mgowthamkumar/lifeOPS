import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Search,
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Sliders,
  ChevronDown,
  Layers,
  ShieldCheck,
  RefreshCw,
  Clock,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type {
  Collection,
  RAGQueryResponse,
  RAGConfig,
} from '../../types';

export const RAGInterface: React.FC = () => {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedColId, setSelectedColId] = useState<string>('');
  const [question, setQuestion] = useState<string>('');
  const [topK, setTopK] = useState<number>(5);
  const [relevanceThreshold, setRelevanceThreshold] = useState<number>(0.30);
  const [showConfig, setShowConfig] = useState<boolean>(false);

  // Results & Loading
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<RAGQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ragConfig, setRagConfig] = useState<RAGConfig | null>(null);
  const [recentEvidence, setRecentEvidence] = useState<any[]>([]);

  // Load Collections & Config on mount
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setError(null);
      const [cols, cfg, ev] = await Promise.all([
        apiService.getCollections(),
        apiService.getRAGConfig(),
        apiService.getRAGRecentEvidence(5),
      ]);
      setCollections(cols);
      setRagConfig(cfg);
      setRecentEvidence(ev);
      if (cols.length > 0 && !selectedColId) {
        setSelectedColId(cols[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to initialize RAG system.');
    }
  };

  const handleRunQuery = async (queryText?: string) => {
    const q = (queryText !== undefined ? queryText : question).trim();
    if (!q) {
      setError('Please enter a question.');
      return;
    }
    if (!selectedColId) {
      setError('Please select a knowledge base collection.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await apiService.queryRAG(
        selectedColId,
        q,
        topK,
        relevanceThreshold
      );
      setResult(res);
      // Refresh recent evidence feed
      const ev = await apiService.getRAGRecentEvidence(5);
      setRecentEvidence(ev);
    } catch (err: any) {
      setError(err.message || 'Failed to execute RAG query.');
    } finally {
      setLoading(false);
    }
  };

  const activeCol = collections.find((c) => c.id === selectedColId);

  // Preset queries for quick verification
  const presetQueries = [
    {
      label: 'Candidate Qualifications (With Evidence)',
      query: 'What are the required qualifications, skills, and experience for the role?',
    },
    {
      label: 'Policy & Deadlines (With Evidence)',
      query: 'What are the key project deadlines, budget constraints, and requirements?',
    },
    {
      label: 'Cardiac Medication (Without Evidence Test)',
      query: 'What is the recommended dosage of medication for cardiac arrhythmia?',
    },
    {
      label: 'Interplanetary Teleportation (Without Evidence Test)',
      query: 'What is the cost and schedule for planetary space flights to Neptune?',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Sparkles className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Real-Time RAG Decision Intelligence
            </h1>
          </div>
          <p className="text-slate-400 text-sm">
            Ground decisions with real document vectors. Strictly prevents hallucination with automated evidence thresholding.
          </p>
        </div>

        {/* Runtime config badges */}
        <div className="flex items-center gap-3">
          {ragConfig && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1 bg-slate-800 border border-slate-700 text-xs font-medium text-slate-300 rounded-full flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                {ragConfig.llm_model}
              </span>
              <span className="px-3 py-1 bg-slate-800 border border-slate-700 text-xs font-medium text-slate-300 rounded-full flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                Backend: {ragConfig.embedding_backend}
              </span>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-red-400" />
          <div className="flex-1">
            <p className="font-semibold">Error</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Main Grid: Query & Controls on Left, Knowledge Details on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Question & Response */}
        <div className="lg:col-span-2 space-y-6">
          {/* Query Box */}
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-lg space-y-4">
            {/* Collection Selection */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen className="w-4 h-4 text-indigo-400" />
                Target Knowledge Collection
              </label>

              {collections.length > 0 ? (
                <div className="relative inline-block w-full sm:w-72">
                  <select
                    value={selectedColId}
                    onChange={(e) => setSelectedColId(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-indigo-500 appearance-none font-medium"
                  >
                    {collections.map((col) => (
                      <option key={col.id} value={col.id}>
                        {col.name} ({col.document_count} docs, {col.chunk_count} chunks)
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-3 pointer-events-none" />
                </div>
              ) : (
                <span className="text-amber-400 text-xs">
                  No collections available. Please create one in Knowledge Base first.
                </span>
              )}
            </div>

            {/* Question Textarea */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Decision Question / Inquiry
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask anything grounded in your documents (e.g. 'What are the required qualifications?', 'What is the budget ceiling?')..."
                rows={3}
                className="w-full bg-slate-950/70 border border-slate-800 text-white placeholder-slate-500 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none font-sans"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    handleRunQuery();
                  }
                }}
              />
            </div>

            {/* Preset Test Chips */}
            <div className="space-y-1.5">
              <span className="text-xs text-slate-500 font-medium">Quick Test Scenarios:</span>
              <div className="flex flex-wrap gap-2">
                {presetQueries.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setQuestion(p.query);
                      handleRunQuery(p.query);
                    }}
                    className="text-xs bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700/60 transition-colors text-left"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Retrieval Tuning Parameters Toggle */}
            <div>
              <button
                type="button"
                onClick={() => setShowConfig(!showConfig)}
                className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium transition-colors"
              >
                <Sliders className="w-3.5 h-3.5" />
                {showConfig ? 'Hide' : 'Tune'} Retrieval Thresholds
              </button>

              {showConfig && (
                <div className="mt-3 p-4 bg-slate-950/50 border border-slate-800 rounded-xl grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Top K Chunks:</span>
                      <span className="font-semibold text-indigo-400">{topK}</span>
                    </div>
                    <input
                      type="range"
                      min={1}
                      max={10}
                      value={topK}
                      onChange={(e) => setTopK(parseInt(e.target.value))}
                      className="w-full accent-indigo-500"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-xs text-slate-300 mb-1">
                      <span>Relevance Threshold:</span>
                      <span className="font-semibold text-indigo-400">
                        {(relevanceThreshold * 100).toFixed(0)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min={0.1}
                      max={0.9}
                      step={0.05}
                      value={relevanceThreshold}
                      onChange={(e) => setRelevanceThreshold(parseFloat(e.target.value))}
                      className="w-full accent-indigo-500"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Action Button */}
            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => handleRunQuery()}
                disabled={loading || !question.trim() || collections.length === 0}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium px-5 py-2.5 rounded-xl shadow-lg transition-all"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Querying Vectors & LLM...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    Run Evidence Grounding
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Response Container */}
          {result && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl overflow-hidden transition-all">
              {/* Evidence Sufficiency Status Banner */}
              <div
                className={`p-4 border-b flex items-center justify-between ${
                  result.has_sufficient_evidence
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                    : 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  {result.has_sufficient_evidence ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
                  )}
                  <div>
                    <p className="font-bold text-sm">
                      {result.has_sufficient_evidence
                        ? 'Evidence-Grounded Recommendation'
                        : 'INSUFFICIENT EVIDENCE DETECTED'}
                    </p>
                    <p className="text-xs opacity-80">
                      {result.has_sufficient_evidence
                        ? `Grounding verified against ${result.sources.length} document chunk(s).`
                        : 'No relevant evidence found above the threshold. Hallucination prevention active.'}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-900/60 border border-white/10">
                    Confidence: {(result.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Synthesized Answer Body */}
              <div className="p-6 space-y-6">
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                    Synthesized Intelligence
                  </h3>
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 text-slate-200 text-sm leading-relaxed whitespace-pre-line font-sans">
                    {result.answer}
                  </div>
                </div>

                {/* Verified Citations Drawer */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <FileText className="w-4 h-4 text-indigo-400" />
                      Verified Source Evidence ({result.sources.length})
                    </h3>
                    <span className="text-xs text-slate-500">
                      Evaluated {result.retrieval_count} candidates
                    </span>
                  </div>

                  {result.sources.length > 0 ? (
                    <div className="space-y-3">
                      {result.sources.map((src, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 bg-slate-950/50 border border-slate-800 rounded-xl space-y-2 hover:border-slate-700 transition-colors"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                            <span className="font-semibold text-white flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5 text-indigo-400" />
                              {src.document_name}
                            </span>
                            <div className="flex items-center gap-2">
                              {src.page_number && (
                                <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-[11px]">
                                  Page {src.page_number}
                                </span>
                              )}
                              <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-[11px]">
                                Chunk #{src.chunk_index}
                              </span>
                              <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-mono text-[11px]">
                                {(src.similarity_score * 100).toFixed(1)}% match
                              </span>
                            </div>
                          </div>
                          <p className="text-xs text-slate-300 italic bg-slate-900/60 p-2.5 rounded border border-slate-800/50 leading-normal font-sans">
                            "{src.content_snippet}"
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 bg-slate-950/30 border border-dashed border-slate-800 rounded-xl text-center text-xs text-slate-500">
                      No source citations available because no chunks met the evidence criteria.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right 1 Col: Collection Status & Audit Trail */}
        <div className="space-y-6">
          {/* Active Collection Summary */}
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-3">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-indigo-400" />
              Active Knowledge Scope
            </h3>

            {activeCol ? (
              <div className="space-y-3 text-sm">
                <div>
                  <p className="font-bold text-white text-base">{activeCol.name}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {activeCol.description || 'No description provided.'}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-xs">
                  <div className="p-2 bg-slate-950/50 rounded-lg">
                    <span className="text-slate-500 block">Documents:</span>
                    <span className="font-semibold text-white">{activeCol.document_count}</span>
                  </div>
                  <div className="p-2 bg-slate-950/50 rounded-lg">
                    <span className="text-slate-500 block">Vector Chunks:</span>
                    <span className="font-semibold text-white">{activeCol.chunk_count}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No collection selected.</p>
            )}
          </div>

          {/* Evidence Persistence Feed */}
          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-lg space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-indigo-400" />
                Persistent Evidence Log
              </h3>
              <span className="text-[10px] text-slate-500">SQLite Logged</span>
            </div>

            {recentEvidence.length > 0 ? (
              <div className="space-y-2.5">
                {recentEvidence.map((ev, i) => (
                  <div
                    key={i}
                    className="p-2.5 bg-slate-950/40 border border-slate-800 rounded-lg space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-300 truncate max-w-[140px]">
                        {ev.source_filename}
                      </span>
                      {ev.relevance_score && (
                        <span className="text-[10px] text-emerald-400 font-mono">
                          {(ev.relevance_score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p className="text-slate-400 line-clamp-2 text-[11px]">
                      {ev.extracted_text}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-3 text-center">
                No evidence items recorded yet. Run queries to populate the evidence store.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
