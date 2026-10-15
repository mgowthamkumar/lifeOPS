import React, { useEffect, useState, useRef } from 'react';
import {
  FolderPlus,
  Upload,
  FileText,
  Trash2,
  RefreshCw,
  Layers,
  CheckCircle2,
  AlertCircle,
  FileUp,
  Database,
  Eye,
  X,
  FileCode,
  FileSpreadsheet,
} from 'lucide-react';
import { apiService } from '../../services/api';
import type { Collection, DocumentItem, DocumentDetail, Chunk } from '../../types';

export default function KnowledgeBase() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal states
  const [showCreateColModal, setShowCreateColModal] = useState<boolean>(false);
  const [newColName, setNewColName] = useState<string>('');
  const [newColDesc, setNewColDesc] = useState<string>('');
  
  // Inspect document chunks modal
  const [inspectDoc, setInspectDoc] = useState<DocumentDetail | null>(null);
  const [loadingInspect, setLoadingInspect] = useState<boolean>(false);

  // Update file input ref
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const updateFileInputRef = useRef<HTMLInputElement | null>(null);
  const [targetUpdateDocId, setTargetUpdateDocId] = useState<string | null>(null);

  // Load Collections
  const loadCollections = async () => {
    try {
      const data = await apiService.getCollections();
      setCollections(data);
      if (data.length === 0) {
        setActiveCollectionId(null);
        setDocuments([]);
      } else {
        setActiveCollectionId((prevId) => {
          if (prevId && data.some((col) => col.id === prevId)) {
            return prevId;
          }
          return data[0].id;
        });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load collections');
    }
  };

  // Load Documents for active collection
  const loadDocuments = async (colId: string) => {
    try {
      const docs = await apiService.getDocuments(colId);
      setDocuments(docs);
    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
    }
  };

  useEffect(() => {
    setLoading(true);
    loadCollections().finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (activeCollectionId) {
      loadDocuments(activeCollectionId);
    }
  }, [activeCollectionId]);

  // Create Collection
  const handleCreateCollection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newColName.trim()) return;

    try {
      setError(null);
      const col = await apiService.createCollection(newColName.trim(), newColDesc.trim());
      setNewColName('');
      setNewColDesc('');
      setShowCreateColModal(false);
      await loadCollections();
      setActiveCollectionId(col.id);
      setSuccessMsg(`Collection "${col.name}" created and synced with ChromaDB.`);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to create collection');
    }
  };

  // Delete Collection
  const handleDeleteCollection = async (colId: string, colName: string) => {
    if (!confirm(`Are you sure you want to delete "${colName}" and all its documents and vectors?`)) return;

    try {
      setError(null);
      await apiService.deleteCollection(colId);
      setSuccessMsg(`Collection "${colName}" and vector store deleted.`);
      setTimeout(() => setSuccessMsg(null), 4000);
      await loadCollections();
    } catch (err: any) {
      setError(err.message || 'Failed to delete collection');
    }
  };

  // Upload Document
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeCollectionId) return;

    setUploading(true);
    setError(null);
    try {
      const doc = await apiService.uploadDocument(activeCollectionId, file);
      setSuccessMsg(`"${doc.filename}" processed: ${doc.chunk_count} vector chunks indexed in ChromaDB.`);
      setTimeout(() => setSuccessMsg(null), 5000);
      await loadDocuments(activeCollectionId);
      await loadCollections(); // refresh counts
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Reprocess Document
  const handleReprocess = async (docId: string, docName: string) => {
    setActionLoadingId(docId);
    setError(null);
    try {
      const doc = await apiService.reprocessDocument(docId);
      setSuccessMsg(`"${docName}" reprocessed: ${doc.chunk_count} vector chunks updated in ChromaDB.`);
      setTimeout(() => setSuccessMsg(null), 4000);
      if (activeCollectionId) {
        await loadDocuments(activeCollectionId);
        await loadCollections();
      }
    } catch (err: any) {
      setError(err.message || 'Reprocessing failed');
    } finally {
      setActionLoadingId(null);
    }
  };

  // Trigger Update Version File Picker
  const triggerUpdateVersion = (docId: string) => {
    setTargetUpdateDocId(docId);
    if (updateFileInputRef.current) {
      updateFileInputRef.current.click();
    }
  };

  // Perform Update Version
  const handleUpdateFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !targetUpdateDocId || !activeCollectionId) return;

    setActionLoadingId(targetUpdateDocId);
    setError(null);
    try {
      const doc = await apiService.updateDocument(targetUpdateDocId, file);
      setSuccessMsg(`"${doc.filename}" updated to v${doc.current_version}: obsolete vectors replaced in ChromaDB.`);
      setTimeout(() => setSuccessMsg(null), 5000);
      await loadDocuments(activeCollectionId);
      await loadCollections();
    } catch (err: any) {
      setError(err.message || 'Update failed');
    } finally {
      setActionLoadingId(null);
      setTargetUpdateDocId(null);
      if (updateFileInputRef.current) updateFileInputRef.current.value = '';
    }
  };

  // Delete Document
  const handleDeleteDocument = async (docId: string, filename: string) => {
    if (!confirm(`Delete "${filename}"? All associated vectors will be purged from ChromaDB.`)) return;

    setActionLoadingId(docId);
    setError(null);
    try {
      await apiService.deleteDocument(docId);
      setSuccessMsg(`Document "${filename}" and its vector chunks deleted.`);
      setTimeout(() => setSuccessMsg(null), 4000);
      if (activeCollectionId) {
        await loadDocuments(activeCollectionId);
        await loadCollections();
      }
    } catch (err: any) {
      setError(err.message || 'Delete failed');
    } finally {
      setActionLoadingId(null);
    }
  };

  // Inspect Chunks
  const handleInspect = async (docId: string) => {
    setLoadingInspect(true);
    try {
      const detail = await apiService.getDocument(docId);
      setInspectDoc(detail);
    } catch (err: any) {
      setError(err.message || 'Failed to inspect document chunks');
    } finally {
      setLoadingInspect(false);
    }
  };

  const activeCol = collections.find((c) => c.id === activeCollectionId);

  const getFormatIcon = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case 'pdf':
        return <FileText className="w-4 h-4 text-rose-400" />;
      case 'docx':
        return <FileText className="w-4 h-4 text-blue-400" />;
      case 'csv':
        return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
      case 'md':
      case 'txt':
        return <FileCode className="w-4 h-4 text-cyan-400" />;
      default:
        return <FileText className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Hidden update file input */}
      <input
        type="file"
        ref={updateFileInputRef}
        onChange={handleUpdateFileSelected}
        accept=".pdf,.docx,.txt,.csv,.md"
        className="hidden"
      />

      {/* Notifications */}
      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-800/60 rounded-xl flex items-start space-x-3 text-rose-300">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-rose-200">Operation Error</h3>
            <p className="text-xs text-rose-300/80 mt-1">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-800/60 rounded-xl flex items-center space-x-3 text-emerald-300">
          <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-400" />
          <span className="text-xs font-medium text-emerald-200">{successMsg}</span>
        </div>
      )}

      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            Knowledge Collections
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Multi-format document ingestion, semantic chunking, and persistent ChromaDB vector storage.
          </p>
        </div>
        <button
          onClick={() => setShowCreateColModal(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-semibold shadow-md transition-all cursor-pointer"
        >
          <FolderPlus className="w-4 h-4" /> New Collection
        </button>
      </div>

      {/* Main Grid: Collections List on Left, Active Collection Documents on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Collections Selector Sidebar */}
        <div className="space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
            Collections ({collections.length})
          </div>

          {loading ? (
            <div className="p-4 bg-slate-900/50 rounded-xl border border-slate-800 text-xs text-slate-500 text-center animate-pulse">
              Loading collections...
            </div>
          ) : collections.length === 0 ? (
            <div className="p-6 bg-slate-900/50 rounded-xl border border-slate-800 text-center space-y-2">
              <Database className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400 font-medium">No collections yet</p>
              <button
                onClick={() => setShowCreateColModal(true)}
                className="text-xs text-cyan-400 hover:underline"
              >
                Create your first collection
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {collections.map((col) => {
                const active = col.id === activeCollectionId;
                return (
                  <div
                    key={col.id}
                    onClick={() => setActiveCollectionId(col.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all duration-150 ${
                      active
                        ? 'bg-cyan-950/30 border-cyan-500/40 shadow-sm shadow-cyan-500/10'
                        : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="font-semibold text-sm text-slate-200">{col.name}</div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteCollection(col.id, col.name);
                        }}
                        title="Delete collection"
                        className="text-slate-500 hover:text-rose-400 transition-colors p-0.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    {col.description && (
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">{col.description}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-500">
                      <span>{col.document_count} doc{col.document_count === 1 ? '' : 's'}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1 text-cyan-400/90 font-mono">
                        <Layers className="w-3 h-3" /> {col.chunk_count} vectors
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Documents Workspace in Active Collection */}
        <div className="lg:col-span-3 space-y-5">
          {activeCol ? (
            <>
              {/* Collection Banner and Upload Zone */}
              <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      {activeCol.name}
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800 text-cyan-300">
                        {activeCol.chunk_count} ChromaDB vectors
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {activeCol.description || 'Knowledge repository collection.'}
                    </p>
                  </div>

                  {/* Hidden file input triggered by button */}
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept=".pdf,.docx,.txt,.csv,.md"
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-md transition-all cursor-pointer disabled:cursor-not-allowed"
                  >
                    {uploading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Ingesting & Chunking...
                      </>
                    ) : (
                      <>
                        <Upload className="w-3.5 h-3.5" /> Upload Document
                      </>
                    )}
                  </button>
                </div>

                <div className="text-[11px] text-slate-500 flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80">
                  <span className="font-semibold text-slate-400">Supported Formats:</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">PDF</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">DOCX</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">TXT</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">CSV</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">MD</span>
                  <span className="text-slate-600">|</span>
                  <span>Max file size: 25MB</span>
                </div>
              </div>

              {/* Document List */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
                  <span>Documents ({documents.length})</span>
                  <span className="text-[11px] text-slate-500 normal-case font-normal">
                    Real-time status synced with SQLite & ChromaDB
                  </span>
                </div>

                {documents.length === 0 ? (
                  <div className="p-10 rounded-2xl bg-slate-900/30 border border-slate-800/80 text-center space-y-3">
                    <FileUp className="w-10 h-10 text-slate-600 mx-auto" />
                    <h4 className="text-sm font-semibold text-slate-300">No documents in this collection</h4>
                    <p className="text-xs text-slate-500 max-w-sm mx-auto">
                      Upload your syllabus, assignment rubrics, job descriptions, or personal notes to start vector grounding.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {documents.map((doc) => {
                      const isActing = actionLoadingId === doc.id;
                      return (
                        <div
                          key={doc.id}
                          className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/90 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:border-slate-700"
                        >
                          <div className="flex items-start space-x-3 min-w-0">
                            <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/60 shrink-0">
                              {getFormatIcon(doc.file_type)}
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-sm text-slate-100 truncate">
                                  {doc.filename}
                                </span>
                                <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700">
                                  v{doc.current_version}
                                </span>
                                <span
                                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                    doc.status === 'PROCESSED'
                                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                                      : doc.status === 'PROCESSING'
                                      ? 'bg-amber-950/80 text-amber-400 border border-amber-800/60 animate-pulse'
                                      : 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
                                  }`}
                                >
                                  {doc.status}
                                </span>
                              </div>
                              <div className="flex items-center gap-3 mt-1.5 text-[11px] text-slate-500">
                                <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                                <span>•</span>
                                <span className="flex items-center gap-1 text-cyan-400/90 font-mono">
                                  <Layers className="w-3 h-3" /> {doc.chunk_count} vector chunks
                                </span>
                                <span>•</span>
                                <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                            <button
                              onClick={() => handleInspect(doc.id)}
                              disabled={isActing || loadingInspect}
                              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                              title="Inspect extracted chunks & vector IDs"
                            >
                              <Eye className="w-3.5 h-3.5 text-cyan-400" /> Inspect
                            </button>
                            <button
                              onClick={() => handleReprocess(doc.id, doc.filename)}
                              disabled={isActing}
                              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                              title="Re-extract and re-embed chunks into ChromaDB"
                            >
                              <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${isActing ? 'animate-spin' : ''}`} /> Reprocess
                            </button>
                            <button
                              onClick={() => triggerUpdateVersion(doc.id)}
                              disabled={isActing}
                              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                              title="Upload newer version (replaces obsolete vectors)"
                            >
                              <Upload className="w-3.5 h-3.5 text-amber-400" /> Update
                            </button>
                            <button
                              onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                              disabled={isActing}
                              className="p-1.5 bg-slate-800 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                              title="Delete document and remove all vectors from ChromaDB"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800 text-center space-y-3">
              <Database className="w-12 h-12 text-slate-600 mx-auto" />
              <h3 className="text-base font-bold text-white">Select or Create a Collection</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Documents must belong to a knowledge collection to ensure scoped retrieval.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Create Collection */}
      {showCreateColModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FolderPlus className="w-5 h-5 text-cyan-400" /> Create Knowledge Collection
              </h3>
              <button
                onClick={() => setShowCreateColModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCollection} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Collection Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. AI Career Research, College Planning"
                  value={newColName}
                  onChange={(e) => setNewColName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-700/80 rounded-lg text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Description
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Job descriptions, syllabus, and assignment criteria"
                  value={newColDesc}
                  onChange={(e) => setNewColDesc(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-700/80 rounded-lg text-sm text-white focus:outline-none focus:border-cyan-500 resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateColModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-semibold shadow-md"
                >
                  Create Collection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Inspect Document Chunks & ChromaDB Vectors */}
      {inspectDoc && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0f172a] border border-slate-800 rounded-2xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Layers className="w-5 h-5 text-cyan-400" />
                  Chunk & Vector Inspector: {inspectDoc.filename}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Showing {inspectDoc.chunks.length} extracted semantic chunks stored in persistent ChromaDB.
                </p>
              </div>
              <button
                onClick={() => setInspectDoc(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              {inspectDoc.chunks.map((chunk: Chunk) => (
                <div
                  key={chunk.id}
                  className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="font-semibold text-slate-200">
                      Chunk #{chunk.chunk_index} {chunk.page_number && `(Page ${chunk.page_number})`}
                    </span>
                    <span className="font-mono text-[10px] bg-slate-800 text-cyan-400 px-2 py-0.5 rounded">
                      ID: {chunk.vector_id}
                    </span>
                  </div>
                  <div className="p-3 bg-slate-950/60 rounded-lg text-slate-300 font-mono text-[11px] leading-relaxed border border-slate-800/80">
                    {chunk.content}
                  </div>
                  <div className="text-[10px] text-slate-500 flex items-center justify-between">
                    <span>Token Count Estimate: {chunk.token_count || 'N/A'} words</span>
                    <span>Indexed: {new Date(chunk.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex justify-end">
              <button
                onClick={() => setInspectDoc(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
