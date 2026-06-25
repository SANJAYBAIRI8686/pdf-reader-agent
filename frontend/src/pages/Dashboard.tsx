import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "../contexts/AuthContext";
import { api, queryRAGStream } from "../services/api";
import { 
  LogOut, Plus, MessageSquare, Trash2, FileText, Upload, 
  Search, CheckCircle2, AlertCircle, Loader2, Send, 
  ExternalLink, FileSpreadsheet, FileCode, Sparkles 
} from "lucide-react";

interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  summary: string | null;
  keywords: string | null;
  created_at: string;
}

interface ChatSessionItem {
  id: number;
  title: string;
}

interface MessageItem {
  id?: number;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{
    filename: string;
    document_id: number;
    chunk_index: number | null;
  }>;
}

export const Dashboard: React.FC = () => {
  const { user, token, logout } = useAuth();
  
  // States
  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  
  // UI Inputs & Controls
  const [prompt, setPrompt] = useState("");
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<any[]>([]);
  const [isQuerying, setIsQuerying] = useState(false);
  
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  
  // Scroll Anchor
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeToken = token || "";

  // 1. Fetch initial Sessions and Documents list
  useEffect(() => {
    loadSessions();
    loadDocuments();
  }, [activeToken]);

  // 2. Poll document statuses if any file is in 'processing' status
  useEffect(() => {
    const hasProcessing = documents.some(doc => doc.status === "processing");
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      loadDocuments();
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [documents]);

  // 3. Load message history when active session modifies
  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId);
    } else {
      setMessages([]);
    }
    setStreamingAnswer("");
    setStreamingCitations([]);
  }, [activeSessionId]);

  // 4. Scroll chat thread to bottom on updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingAnswer]);

  // --- API Actions ---

  const loadSessions = async () => {
    try {
      const data = await api.listSessions(activeToken);
      setSessions(data);
      if (data.length > 0 && activeSessionId === null) {
        setActiveSessionId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load sessions", err);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await api.listDocuments(activeToken);
      setDocuments(data);
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  };

  const loadMessages = async (sid: number) => {
    try {
      const data = await api.listMessages(sid, activeToken);
      setMessages(data);
    } catch (err) {
      console.error("Failed to load messages", err);
    }
  };

  const handleCreateSession = async () => {
    try {
      const newSession = await api.createSession(null, activeToken);
      setSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
    } catch (err) {
      console.error("Failed to create chat session", err);
    }
  };

  const handleDeleteSession = async (sid: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteSession(sid, activeToken);
      setSessions(prev => prev.filter(s => s.id !== sid));
      if (activeSessionId === sid) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  // --- Document Upload Actions ---

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    setUploading(true);
    setUploadError(null);
    try {
      const response = await api.uploadDocument(file, activeToken);
      setDocuments(prev => [response.document, ...prev]);
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload document.");
    } finally {
      setUploading(false);
      if (e.target) e.target.value = ""; // Reset file selector
    }
  };

  const handleDeleteDoc = async (docId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteDocument(docId, activeToken);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      if (selectedDoc?.id === docId) {
        setSelectedDoc(null);
      }
    } catch (err) {
      console.error("Failed to delete document", err);
    }
  };

  // --- Semantic Search Actions ---

  const handleSemanticSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setSearching(true);
    try {
      const results = await api.semanticSearch(searchQuery.trim(), activeToken);
      setSearchResults(results);
    } catch (err) {
      console.error("Semantic search failed", err);
    } finally {
      setSearching(false);
    }
  };

  // --- Streaming Chat Query ---

  const handleSendQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isQuerying || !activeSessionId) return;

    const userText = prompt.trim();
    setPrompt("");
    setIsQuerying(true);
    setStreamingAnswer("");
    setStreamingCitations([]);

    // Optimistically log user prompt in the UI history thread
    const userMsg: MessageItem = { role: "user", content: userText };
    setMessages(prev => [...prev, userMsg]);

    // Query stream reader
    await queryRAGStream(activeSessionId, userText, activeToken, {
      onCitations: (citations) => {
        setStreamingCitations(citations);
      },
      onToken: (token) => {
        setStreamingAnswer(prev => prev + token);
      },
      onDone: () => {
        setIsQuerying(false);
        // Refresh local session lists (in case title got renamed dynamically)
        loadSessions();
        // Load clean database messages history including the new record
        loadMessages(activeSessionId);
      },
      onError: (err) => {
        setIsQuerying(false);
        const errAnswer = `Error: ${err}`;
        setMessages(prev => [...prev, { role: "assistant", content: errAnswer }]);
        setStreamingAnswer("");
      }
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (fileType: string) => {
    const type = fileType.toLowerCase();
    if (type === "pdf") return <FileText className="w-5 h-5 text-red-400" />;
    if (type === "docx") return <FileSpreadsheet className="w-5 h-5 text-blue-400" />;
    return <FileCode className="w-5 h-5 text-purple-400" />;
  };

  return (
    <div className="flex h-screen w-full bg-[#060911] text-slate-100 overflow-hidden font-sans">
      
      {/* 1. LEFT SIDEBAR: Conversational Sessions List */}
      <div className="w-72 border-r border-slate-800 bg-[#0a0f1d] flex flex-col justify-between shrink-0">
        
        {/* Sidebar Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <span className="font-bold text-sm tracking-tight text-white">Research Agent</span>
          </div>
          <button 
            onClick={handleCreateSession}
            className="p-1.5 rounded-lg bg-purple-600/10 hover:bg-purple-600/20 border border-purple-600/25 text-purple-300 hover:text-white transition-colors cursor-pointer"
            title="Start New Chat"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>

        {/* Sessions Sidebar List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {sessions.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs text-slate-500">No chat sessions yet.</p>
              <button 
                onClick={handleCreateSession}
                className="mt-3 text-xs text-purple-400 font-semibold hover:underline bg-transparent border-0 cursor-pointer"
              >
                Create session
              </button>
            </div>
          ) : (
            sessions.map(s => (
              <div 
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                className={`group flex items-center justify-between p-3 rounded-lg text-sm cursor-pointer transition-all duration-150 ${
                  activeSessionId === s.id 
                    ? "bg-purple-500/10 border border-purple-500/20 text-white font-medium" 
                    : "border border-transparent hover:bg-slate-800/40 text-slate-400 hover:text-slate-200"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <MessageSquare className={`w-4 h-4 shrink-0 ${activeSessionId === s.id ? "text-purple-400" : "text-slate-500"}`} />
                  <span className="truncate block pr-2 text-xs">{s.title}</span>
                </div>
                <button 
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-slate-500 hover:text-red-400 transition-all cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Sidebar Footer User Details */}
        <div className="p-4 border-t border-slate-800 bg-[#070b13] flex items-center justify-between">
          <div className="flex flex-col min-w-0 pr-2">
            <span className="text-xs font-bold text-white truncate">{user?.full_name || "Research Scholar"}</span>
            <span className="text-[10px] text-slate-500 truncate">{user?.email}</span>
          </div>
          <button 
            onClick={logout}
            className="p-2 rounded-lg bg-slate-800 hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors cursor-pointer border border-slate-700/50 hover:border-red-500/20"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. CHAT PANEL (LEFT SIDE OF DETAILS PANE) */}
      <div className="flex-1 flex flex-col bg-[#070a13] relative border-r border-slate-800">
        
        {/* Chat Header */}
        <div className="h-14 border-b border-slate-800/80 px-6 flex items-center justify-between bg-[#0a0f1d]/50">
          <h2 className="text-sm font-bold text-white">
            {activeSessionId 
              ? sessions.find(s => s.id === activeSessionId)?.title || "Chat Console"
              : "Chat Console"
            }
          </h2>
        </div>

        {/* Message scrolling thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {!activeSessionId ? (
            <div className="h-full flex items-center justify-center flex-col text-center">
              <div className="p-4 rounded-full bg-slate-800/30 text-slate-500 border border-slate-800/50 mb-4">
                <MessageSquare className="w-8 h-8" />
              </div>
              <h3 className="text-white font-semibold text-sm">Select a Conversation</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">
                Click an existing thread in the sidebar or start a new chat session to query documents.
              </p>
            </div>
          ) : messages.length === 0 && !streamingAnswer ? (
            <div className="h-full flex items-center justify-center flex-col text-center">
              <div className="p-4 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/10 mb-4 animate-bounce">
                <Sparkles className="w-8 h-8" />
              </div>
              <h3 className="text-white font-semibold text-sm">Ask your Documents</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">
                Type your question below. The RAG agent will search your documents and cite source paragraphs.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((m, idx) => (
                <div 
                  key={idx}
                  className={`flex gap-4 p-4 rounded-xl ${
                    m.role === "user" 
                      ? "bg-slate-800/25 border border-slate-800/40 ml-12" 
                      : "bg-[#0b1021]/80 border border-purple-950/20 mr-12"
                  }`}
                >
                  <div className="flex-1 space-y-2.5 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">
                        {m.role === "user" ? "You" : "Assistant"}
                      </span>
                    </div>
                    <p className="text-slate-300 text-xs leading-relaxed whitespace-pre-line">{m.content}</p>
                    
                    {/* Citations Card */}
                    {m.role === "assistant" && m.citations && m.citations.length > 0 && (
                      <div className="pt-3 border-t border-slate-800/80 mt-3">
                        <span className="text-[10px] font-semibold text-slate-400 block mb-1.5">Sources Cited:</span>
                        <div className="flex flex-wrap gap-2">
                          {m.citations.map((c, cIdx) => (
                            <button
                              key={cIdx}
                              onClick={() => {
                                const matchedDoc = documents.find(d => d.id === c.document_id);
                                if (matchedDoc) setSelectedDoc(matchedDoc);
                              }}
                              className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700/80 border border-slate-700/60 hover:border-slate-600/60 text-[10px] text-purple-300 hover:text-purple-200 transition-all cursor-pointer"
                            >
                              <FileText className="w-3 h-3" />
                              <span className="max-w-[120px] truncate">{c.filename}</span>
                              <ExternalLink className="w-2.5 h-2.5 text-slate-500" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Streaming Answer Section */}
              {streamingAnswer && (
                <div className="flex gap-4 p-4 rounded-xl bg-[#0b1021]/80 border border-purple-950/20 mr-12">
                  <div className="flex-1 space-y-2.5 min-w-0">
                    <span className="text-[10px] uppercase tracking-wider font-bold text-purple-400 animate-pulse">
                      Assistant Generating...
                    </span>
                    <p className="text-slate-300 text-xs leading-relaxed whitespace-pre-line">{streamingAnswer}</p>

                    {/* Yield Streaming citations early */}
                    {streamingCitations.length > 0 && (
                      <div className="pt-3 border-t border-slate-800/80 mt-3">
                        <span className="text-[10px] font-semibold text-slate-400 block mb-1.5">Sources Cited:</span>
                        <div className="flex flex-wrap gap-2">
                          {streamingCitations.map((c, cIdx) => (
                            <div
                              key={cIdx}
                              className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800/50 border border-slate-800/80 text-[10px] text-slate-400"
                            >
                              <FileText className="w-3 h-3" />
                              <span className="max-w-[120px] truncate">{c.filename}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input prompt text fields */}
        {activeSessionId && (
          <div className="p-4 border-t border-slate-800/80 bg-[#0a0f1d]/30">
            <form onSubmit={handleSendQuery} className="relative">
              <input
                type="text"
                required
                disabled={isQuerying}
                placeholder={isQuerying ? "Waiting for response..." : "Query your indexed documents..."}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full py-3.5 pl-4 pr-12 rounded-xl glass-input text-xs transition-all duration-200"
              />
              <button
                type="submit"
                disabled={isQuerying || !prompt.trim()}
                className="absolute right-2 top-2 p-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                {isQuerying ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </form>
          </div>
        )}
      </div>

      {/* 3. DOCUMENT HUB (RIGHT SIDE PANELS) */}
      <div className="w-96 border-l border-slate-800 bg-[#0a0f1d] flex flex-col overflow-hidden shrink-0">
        
        {/* Document Pane Header */}
        <div className="p-4 border-b border-slate-800 bg-[#0a0f1d]/50 flex items-center justify-between">
          <h2 className="text-sm font-bold text-white">Document Hub</h2>
        </div>

        {/* Semantic Search Area */}
        <div className="p-4 border-b border-slate-800">
          <form onSubmit={handleSemanticSearch} className="relative">
            <input
              type="text"
              required
              placeholder="Search concepts across files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full py-2.5 pl-3 pr-10 rounded-lg glass-input text-xs"
            />
            <button 
              type="submit"
              disabled={searching || !searchQuery.trim()}
              className="absolute right-2 top-2 p-1 text-slate-400 hover:text-purple-400 transition-colors cursor-pointer"
            >
              {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            </button>
          </form>

          {/* Search Results Pane */}
          {searchResults.length > 0 && (
            <div className="mt-3 bg-slate-900/60 border border-slate-800 rounded-lg p-3 max-h-48 overflow-y-auto space-y-2">
              <div className="flex items-center justify-between text-[9px] text-slate-500 font-semibold mb-1">
                <span>Semantic Matches</span>
                <button 
                  onClick={() => setSearchResults([])}
                  className="hover:underline hover:text-slate-300 bg-transparent border-0 cursor-pointer"
                >
                  Clear
                </button>
              </div>
              {searchResults.map((hit, hitIdx) => (
                <div key={hitIdx} className="p-2 bg-slate-950/40 rounded border border-slate-800/50 text-[10px] space-y-1">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="truncate max-w-[150px] font-medium">{hit.filename}</span>
                    <span className="text-[9px] text-slate-500">dist: {hit.score.toFixed(3)}</span>
                  </div>
                  <p className="text-slate-300 leading-normal italic">"{hit.text.substring(0, 100)}..."</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Drag and Drop File Uploader Panel */}
        <div className="p-4 border-b border-slate-800 bg-[#070b13]/40">
          <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-800 hover:border-purple-500/50 rounded-xl cursor-pointer transition-all duration-200 text-center hover:bg-purple-600/5 group">
            {uploading ? (
              <div className="space-y-2 text-purple-400">
                <Loader2 className="w-8 h-8 animate-spin mx-auto" />
                <span className="text-xs font-semibold block">Uploading file payload...</span>
              </div>
            ) : (
              <div className="space-y-2 text-slate-400 group-hover:text-purple-300">
                <Upload className="w-8 h-8 mx-auto text-slate-500 group-hover:text-purple-400 transition-colors" />
                <div>
                  <span className="text-xs font-semibold block text-slate-300">Upload document</span>
                  <span className="text-[10px] text-slate-500 mt-1 block">PDF, DOCX, Markdown up to 50MB</span>
                </div>
              </div>
            )}
            <input 
              type="file"
              accept=".pdf,.docx,.md,.markdown,.txt"
              className="hidden"
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </label>

          {uploadError && (
            <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-200 text-[10px] flex items-start gap-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 text-red-400 mt-0.5" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>

        {/* List of Files Panel */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          <span className="text-[10px] font-semibold tracking-wider text-slate-500 uppercase block mb-1">Indexed Files</span>
          
          {documents.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-xs text-slate-500">No documents uploaded yet.</p>
            </div>
          ) : (
            documents.map(doc => (
              <div 
                key={doc.id}
                onClick={() => setSelectedDoc(doc)}
                className="group flex items-center justify-between p-3 rounded-xl border border-slate-800 hover:border-slate-700 bg-slate-900/35 hover:bg-slate-900/60 transition-all cursor-pointer"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {getFileIcon(doc.file_type)}
                  <div className="min-w-0">
                    <span className="text-xs text-white font-medium truncate block pr-2">{doc.filename}</span>
                    <span className="text-[9px] text-slate-500 mt-0.5 block">{formatFileSize(doc.file_size)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Status Badges */}
                  {doc.status === "processing" && (
                    <span title="Parsing document">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-400" />
                    </span>
                  )}
                  {doc.status === "processed" && (
                    <span title="Indexed successfully">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    </span>
                  )}
                  {doc.status === "failed" && (
                    <span title="Parsing failed">
                      <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                    </span>
                  )}

                  <button 
                    onClick={(e) => handleDeleteDoc(doc.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-slate-500 hover:text-red-400 transition-all cursor-pointer"
                    title="Delete document"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 4. SELECTION DOCUMENT DETAIL MODAL (SUMMARY / KEYWORDS POPUP) */}
      {selectedDoc && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg glass-panel rounded-2xl p-6 shadow-2xl space-y-5">
            
            {/* Modal Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                {getFileIcon(selectedDoc.file_type)}
                <div>
                  <h3 className="font-bold text-white text-sm">{selectedDoc.filename}</h3>
                  <span className="text-[10px] text-slate-500 block mt-0.5">Status: {selectedDoc.status}</span>
                </div>
              </div>
              <button 
                onClick={() => setSelectedDoc(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700/50 cursor-pointer"
              >
                Close
              </button>
            </div>

            {/* Modal Body Info */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 p-3 bg-slate-900/50 border border-slate-800/80 rounded-xl text-[10px]">
                <div>
                  <span className="text-slate-500 block">File Size:</span>
                  <span className="text-slate-300 font-semibold mt-0.5 block">{formatFileSize(selectedDoc.file_size)}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Upload Date:</span>
                  <span className="text-slate-300 font-semibold mt-0.5 block">
                    {new Date(selectedDoc.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {/* Document Summary Block */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase block">Extracted Summary:</span>
                <div className="p-3.5 bg-slate-900/30 border border-slate-800/50 rounded-xl">
                  <p className="text-slate-300 text-xs leading-relaxed italic">
                    {selectedDoc.summary || "Generating summary in background..."}
                  </p>
                </div>
              </div>

              {/* Keywords chips */}
              {selectedDoc.keywords && (
                <div className="space-y-2">
                  <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase block">Target Keywords:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedDoc.keywords.split(",").map((kw, kwIdx) => (
                      <span 
                        key={kwIdx}
                        className="px-2 py-1 rounded bg-purple-500/10 border border-purple-500/20 text-[9px] text-purple-300 font-medium uppercase tracking-wider"
                      >
                        {kw.trim()}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            {/* Modal Footer Delete Action */}
            <div className="pt-4 border-t border-slate-800/80 flex justify-end">
              <button 
                onClick={(e) => {
                  handleDeleteDoc(selectedDoc.id, e);
                }}
                className="px-4 py-2 rounded-lg bg-red-600/10 hover:bg-red-600 hover:text-white border border-red-600/30 text-red-400 text-xs font-semibold transition-all cursor-pointer"
              >
                Delete File Index
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
