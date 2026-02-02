import React, { useState, useEffect, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Database,
  Terminal,
  Cpu,
  Layers,
  CheckCircle2,
  AlertCircle,
  Loader2,
  MessageSquare,
  LayoutDashboard,
  Activity,
  Box,
  ChevronRight,
  Bell,
  SearchCode,
  Github,
  GitBranch,
  Zap,
  Settings,
  Globe,
  Code2,
  Copy,
  Check,
  Plus,
  X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Helper for tailwind classes
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// --- API Types & Helpers ---
const API_BASE = "http://localhost:8000";

interface IndexStatus {
  index_id: string;
  status: 'started' | 'completed' | 'failed' | 'pending';
  repo_url: string;
  branch: string;
  error?: string;
}

// --- Components ---

const Modal = ({ isOpen, onClose, title, children }: { isOpen: boolean, onClose: () => void, title: string, children: React.ReactNode }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <h3 className="font-bold text-slate-800">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded-full text-slate-500 transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  );
};

const Badge = ({ children, variant = 'info' }: { children: React.ReactNode, variant?: 'info' | 'success' | 'warning' | 'error' | 'neutral' }) => {
  // ... (Badge component content unchanged) ...
  const variants = {
    info: "bg-blue-50 text-blue-600 border-blue-100",
    success: "bg-emerald-50 text-emerald-600 border-emerald-100",
    warning: "bg-amber-50 text-amber-600 border-amber-100",
    error: "bg-rose-50 text-rose-600 border-rose-100",
    neutral: "bg-slate-50 text-slate-600 border-slate-100"
  };
  return (
    <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider", variants[variant])}>
      {children}
    </span>
  );
};

const Card = ({ children, className, title, icon }: { children: React.ReactNode, className?: string, title?: string, icon?: React.ReactNode }) => (
  // ... (Card component content unchanged) ...
  <div className={cn("bg-white border border-slate-200/60 rounded-xl overflow-hidden card-shadow", className)}>
    {title && (
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-sm font-bold flex items-center gap-2 text-slate-800">
          {icon && <span className="text-primary">{icon}</span>}
          {title}
        </h3>
      </div>
    )}
    <div className="p-5">{children}</div>
  </div>
);

const Button = ({
  // ... (Button component content unchanged) ...
  children,
  onClick,
  className,
  disabled,
  variant = 'primary',
  loading = false,
  icon
}: {
  children: React.ReactNode,
  onClick?: () => void,
  className?: string,
  disabled?: boolean,
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost',
  loading?: boolean,
  icon?: React.ReactNode
}) => {
  const variants = {
    primary: "bg-primary text-white hover:bg-primary-dark shadow-sm",
    secondary: "bg-slate-100 text-slate-700 hover:bg-slate-200",
    outline: "border border-slate-200 hover:border-slate-300 bg-white text-slate-600",
    ghost: "hover:bg-slate-50 text-slate-500"
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={cn(
        "px-4 py-2 rounded-lg font-semibold text-sm transition-all flex items-center justify-center gap-2 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        className
      )}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : icon}
      {children}
    </button>
  );
};

const Input = ({
  // ... (Input component content unchanged) ...
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  icon
}: {
  label?: string,
  value: string,
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void,
  placeholder?: string,
  type?: string,
  icon?: React.ReactNode
}) => (
  <div className="flex flex-col gap-1.5 w-full">
    {label && <label className="text-xs font-bold text-slate-500 px-1 uppercase tracking-tight">{label}</label>}
    <div className="relative group">
      {icon && <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors">{icon}</div>}
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className={cn(
          "w-full py-2.5 rounded-lg border border-slate-200 focus:border-primary/50 focus:ring-4 focus:ring-primary/5 focus:outline-none transition-all bg-slate-50/30 text-sm",
          icon ? "pl-10 pr-4" : "px-4"
        )}
      />
    </div>
  </div>
);

// --- Main Application ---

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'index' | 'execute' | 'status'>('dashboard');
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [namespace, setNamespace] = useState('default');
  const [indexingId, setIndexingId] = useState<string | null>(null);
  const [isIndexing, setIsIndexing] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const [instruction, setInstruction] = useState('');
  // ... (rest of state and effects unchanged) ...
  const [query, setQuery] = useState('');
  const [execRepo, setExecRepo] = useState('my-repo');
  const [execBranch, setExecBranch] = useState('main');
  const [executionResult, setExecutionResult] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  const [metrics, setMetrics] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [indexedRepos, setIndexedRepos] = useState<any[]>([]);

  // Fetch metrics, activity and indexed repos on mount or tab change, with polling for index tab
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [mRes, aRes, rRes] = await Promise.all([
          fetch(`${API_BASE}/metrics`),
          fetch(`${API_BASE}/activity`),
          fetch(`${API_BASE}/repos`)
        ]);
        setMetrics(await mRes.json());
        setActivity(await aRes.json());
        setIndexedRepos(await rRes.json());
      } catch (e) {
        console.error("Failed to fetch dashboard data", e);
      }
    };

    if (activeTab === 'dashboard' || activeTab === 'index') {
      fetchData();
    }

    let interval: any;
    if (activeTab === 'index') {
      interval = setInterval(fetchData, 3000);
    }
    return () => clearInterval(interval);
  }, [activeTab]);

  // Handle URL Query Params for Deep Linking
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const repoParam = params.get("repo");
    const branchParam = params.get("branch");

    if (repoParam) { // Clean repo value if needed, but assuming simple string
      setExecRepo(repoParam);
      setExecBranch(branchParam || "main");
      setActiveTab('execute');
      // Clean URL without refresh
      window.history.replaceState({}, document.title, "/");
    }
  }, []);

  // ... inside App component ...
  const [livePipelines, setLivePipelines] = useState<any[]>([]);

  // Polling for live pipelines
  useEffect(() => {
    let interval: any;
    if (activeTab === 'status' || isIndexing) {
      const fetchLive = async () => {
        try {
          const res = await fetch(`${API_BASE}/live`);
          const data = await res.json();
          setLivePipelines(data);

          // If we are locally tracking an indexId, check if it's still in the live list.
          // If not in live list, it might have finished.
          if (indexingId) {
            const stillRunning = data.find((p: any) => p.index_id === indexingId);
            if (!stillRunning) {
              // It finished (or failed), fetch final status once to updating local state if needed
              // But simply knowing it's not live is enough to stop spinner?
              // Actually better to keep polling status specifically if we want to show the specific result card?
              // Let's rely on /live for the list view.
              setIsIndexing(false);
            }
          }
        } catch (e) {
          console.error("Live fetch failed", e);
        }
      };

      fetchLive(); // Initial call
      interval = setInterval(fetchLive, 3000);
    }
    return () => clearInterval(interval);
  }, [activeTab, isIndexing, indexingId]);

  const handleIndex = async () => {
    setIsIndexing(true);
    setExecutionResult(null);
    try {
      const res = await fetch(`${API_BASE}/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl, branch, namespace })
      });
      const data = await res.json();
      setIndexingId(data.index_id);
      setIsModalOpen(false);
      setActiveTab('status');
    } catch (e) {
      setIsIndexing(false);
      alert("Failed to start indexing");
    }
  };

  const handleExecute = async () => {
    setIsExecuting(true);
    setExecutionResult(null);
    try {
      const res = await fetch(`${API_BASE}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant: "demo",
          repo: execRepo,
          branch: execBranch,
          instruction,
          context_query: query,
          constraints: { json: false }
        })
      });
      const data = await res.json();
      setExecutionResult(data.result);
    } catch (e) {
      alert("Execution failed");
    } finally {
      setIsExecuting(false);
    }
  };

  const breadcrumbs = useMemo(() => {
    const map = {
      dashboard: "Overview",
      index: "Registry / New Repository",
      execute: "Reasoning Lab / Code Intelligence",
      status: "Pipeline / Runner Logs"
    };
    return map[activeTab];
  }, [activeTab]);

  return (
    <div className="flex h-full w-full bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col z-20 overflow-y-auto shrink-0">
        <div className="p-6 flex items-center gap-3 mb-4">
          <div className="bg-primary p-2 rounded-lg primary-gradient shadow-blue-200 shadow-md">
            <Cpu className="text-white w-5 h-5" />
          </div>
          <h1 className="text-lg font-black tracking-tighter text-slate-800 uppercase">CodeMind</h1>
        </div>

        <nav className="flex-1 px-3 space-y-6">
          <div>
            <h2 className="px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">General</h2>
            <div className="space-y-1">
              <SidebarLink
                active={activeTab === 'dashboard'}
                onClick={() => setActiveTab('dashboard')}
                icon={<LayoutDashboard size={18} />}
                label="Overview"
              />
              <SidebarLink
                active={false}
                onClick={() => { }}
                icon={<Activity size={18} />}
                label="System Health"
                badge="Stable"
                badgeVariant="success"
              />
            </div>
          </div>

          <div>
            <h2 className="px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Code Tools</h2>
            <div className="space-y-1">
              <SidebarLink
                active={activeTab === 'index'}
                onClick={() => setActiveTab('index')}
                icon={<Layers size={18} />}
                label="Index Registry"
              />
              <SidebarLink
                active={activeTab === 'status'}
                onClick={() => setActiveTab('status')}
                icon={<CheckCircle2 size={18} />}
                label="Pipeline Status"
                badge={isIndexing ? "Live" : undefined}
                badgeVariant="info"
              />
              <SidebarLink
                active={activeTab === 'execute'}
                onClick={() => setActiveTab('execute')}
                icon={<Terminal size={18} />}
                label="Reasoning Lab"
              />
            </div>
          </div>

          <div>
            <h2 className="px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Enterprise</h2>
            <div className="space-y-1">
              <SidebarLink
                active={false}
                onClick={() => { }}
                icon={<Database size={18} />}
                label="Knowledge Base"
                disabled
              />
              <SidebarLink
                active={false}
                onClick={() => { }}
                icon={<Box size={18} />}
                label="API Integrations"
                disabled
              />
            </div>
          </div>
        </nav>

        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <SidebarLink
            active={false}
            onClick={() => { }}
            icon={<Settings size={18} />}
            label="Settings"
          />
        </div>
      </aside>

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-2 text-slate-400">
            <span className="text-xs font-bold uppercase tracking-widest">Platform</span>
            <ChevronRight size={14} />
            <span className="text-xs font-bold text-slate-800 uppercase tracking-widest">{breadcrumbs}</span>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3 px-3 py-1 bg-slate-100 rounded-full">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <span className="text-[10px] font-black text-slate-600 uppercase tracking-wider">Tenant: Demo</span>
            </div>
            <button className="text-slate-400 hover:text-slate-600 cursor-pointer transition-colors relative">
              <Bell size={18} />
              <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-rose-500 rounded-full"></div>
            </button>
            <div className="w-8 h-8 rounded-full bg-slate-200 border border-slate-300 flex items-center justify-center text-[10px] font-black text-slate-500">
              RP
            </div>
          </div>
        </header>

        {/* Content Container */}
        <main className="flex-1 overflow-y-auto p-8 relative">
          <AnimatePresence mode="wait">
            {activeTab === 'dashboard' && (
              <motion.div
                key="dashboard"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.2 }}
                className="space-y-8"
              >
                <header className="flex flex-col gap-1">
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight">System Overview</h2>
                  <p className="text-slate-500 text-sm">Real-time metrics and health of your code intelligence infrastructure.</p>
                </header>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <StatCard label="Indexed Assets" value={metrics?.indexed_assets || "0"} delta="+12%" icon={<Layers />} />
                  <StatCard label="Reasoning Calls" value={metrics?.reasoning_calls || "0"} delta="+4.5%" icon={<Terminal />} />
                  <StatCard label="Semantic Depth" value={metrics?.semantic_depth || "384-dim"} delta="Optimized" icon={<Cpu />} />
                  <StatCard label="Uptime" value={metrics?.uptime || "99.9%"} delta="Stable" icon={<Activity />} />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-6">
                    <Card title="Recent Indexing Activity" icon={<SearchCode />}>
                      <div className="space-y-4">
                        {activity.length > 0 ? activity.map((row, i) => (
                          <div key={i} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
                            <div className="flex items-center gap-4">
                              <div className="p-2 bg-slate-50 rounded-lg"><Github size={16} className="text-slate-400" /></div>
                              <div className="flex flex-col text-left">
                                <span className="text-sm font-bold text-slate-800">{row.repo}</span>
                                <span className="text-xs text-slate-400 flex items-center gap-1"><GitBranch size={10} /> {row.branch}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-6">
                              <Badge variant={row.status === 'completed' ? 'success' : row.status === 'failed' ? 'error' : 'info'}>{row.status}</Badge>
                              <span className="text-xs text-slate-400 font-medium">{new Date(row.date).toLocaleDateString()}</span>
                            </div>
                          </div>
                        )) : (
                          <div className="py-10 text-center text-slate-400 text-sm">No activity recorded yet.</div>
                        )}
                      </div>
                    </Card>

                    <div className="grid grid-cols-2 gap-6">
                      <Card title="Model Performance" icon={<Zap />}>
                        <div className="flex flex-col items-center justify-center py-6">
                          <div className="text-4xl font-black text-primary mb-1">94ms</div>
                          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Avg. Latency</div>
                        </div>
                      </Card>
                      <Card title="Database Status" icon={<Box />}>
                        <div className="flex flex-col items-center justify-center py-6">
                          <div className="text-4xl font-black text-emerald-500 mb-1">{metrics?.total_embeddings || "0"}</div>
                          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Total Embeddings</div>
                        </div>
                      </Card>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <Card title="System Notifications">
                      <div className="space-y-6">
                        <Notification
                          type="info"
                          title="Index Cleanup"
                          desc="Automatic garbage collection scheduled for 02:00 UTC."
                        />
                        <Notification
                          type="warning"
                          title="Driver Limitation"
                          desc="Local LLM driver is currently experimental in this instance."
                        />
                        <Notification
                          type="success"
                          title="Database Sync"
                          desc="PostgreSQL vector synchronization completed successfully."
                        />
                      </div>
                    </Card>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'index' && (
              <motion.div
                key="index"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-8 max-w-4xl mx-auto"
              >
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-black text-slate-900 tracking-tight">Index Registry</h2>
                    <p className="text-slate-500 text-sm">Manage your indexed codebases and view execution history.</p>
                  </div>
                  <Button onClick={() => setIsModalOpen(true)} icon={<Plus size={16} />}>New Index</Button>
                </div>

                <div className="space-y-8">
                  <Card title="Indexed Assets Registry" icon={<Layers size={16} />}>
                    <div className="space-y-4">
                      {indexedRepos.length > 0 ? indexedRepos.map((repo, i) => (
                        <div key={i} className="flex items-center justify-between p-4 bg-slate-50/50 rounded-xl border border-slate-100/50 hover:bg-white hover:border-primary/20 transition-all group">
                          <div className="flex items-center gap-4">
                            <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-slate-200 text-slate-400 group-hover:text-primary transition-colors focus-within:ring-2 focus-within:ring-primary/20">
                              <Github size={20} />
                            </div>
                            <div className="text-left">
                              <h4 className="text-sm font-black text-slate-800 uppercase tracking-tight">{repo.name}</h4>
                              <div className="flex items-center gap-2 mt-0.5">
                                <Badge variant="success">Indexed</Badge>
                                <span className="text-[10px] text-slate-400 font-mono">{repo.branch}</span>
                              </div>
                            </div>
                          </div>
                          <Button
                            variant="outline"
                            className="text-xs py-1.5 px-3 bg-white"
                            icon={<Terminal size={12} />}
                            onClick={() => {
                              setExecRepo(repo.name);
                              setExecBranch(repo.branch);
                              setActiveTab('execute');
                            }}
                          >
                            Open in Lab
                          </Button>
                        </div>
                      )) : (
                        <div className="py-12 border-2 border-dashed border-slate-100 rounded-2xl flex flex-col items-center gap-3">
                          <Layers className="text-slate-200" size={32} />
                          <p className="text-slate-400 text-xs font-bold uppercase tracking-widest">No assets indexed yet</p>
                        </div>
                      )}
                    </div>
                  </Card>

                  <Card title="Indexing History Log" icon={<Activity size={16} />}>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm text-slate-600">
                        <thead className="bg-slate-50 text-xs uppercase font-bold text-slate-400">
                          <tr>
                            <th className="px-4 py-3">Time</th>
                            <th className="px-4 py-3">Repo</th>
                            <th className="px-4 py-3">Branch</th>
                            <th className="px-4 py-3">Status</th>
                            <th className="px-4 py-3">ID</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {activity.map((row: any, i: number) => (
                            <tr key={i} className="hover:bg-slate-50/50 transition-colors">
                              <td className="px-4 py-3 font-mono text-xs whitespace-nowrap">{new Date(row.date).toLocaleString()}</td>
                              <td className="px-4 py-3 font-bold text-slate-800">{row.repo}</td>
                              <td className="px-4 py-3 text-slate-500">{row.branch}</td>
                              <td className="px-4 py-3"><Badge variant={row.status === 'completed' ? 'success' : row.status === 'failed' ? 'error' : 'info'}>{row.status.replace(/_/g, ' ')}</Badge></td>
                              <td className="px-4 py-3 font-mono text-[10px] text-slate-400" title={row.index_id}>{row.index_id?.substring(0, 8)}...</td>
                            </tr>
                          ))}
                          {activity.length === 0 && (
                            <tr>
                              <td colSpan={5} className="px-4 py-8 text-center text-slate-400 text-xs italic">No history available</td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                </div>

                <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Register New Repository">
                  <div className="space-y-6 text-left">
                    <Input
                      label="Tenant Namespace"
                      placeholder="default"
                      value={namespace}
                      onChange={(e) => setNamespace(e.target.value)}
                      icon={<Globe size={16} />}
                    />
                    <Input
                      label="Repository URI"
                      placeholder="https://github.com/username/repo.git"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      icon={<Github size={16} />}
                    />
                    <Input
                      label="Default Branch"
                      placeholder="main"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      icon={<GitBranch size={16} />}
                    />
                    <div className="bg-slate-50 p-4 rounded-xl flex gap-3 border border-slate-100">
                      <Layers className="text-primary w-5 h-5 shrink-0 mt-0.5" />
                      <p className="text-[11px] text-slate-500 leading-relaxed">
                        <strong className="text-slate-800">Pipeline Protocol:</strong> We'll perform a shallow clone, extract definitions using Tree-sitter,
                        and generate 384-dim semantic embeddings for context retrieval.
                      </p>
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                      <Button variant="ghost" onClick={() => setIsModalOpen(false)}>Cancel</Button>
                      <Button
                        loading={isIndexing}
                        onClick={handleIndex}
                        disabled={!repoUrl}
                        icon={<Terminal />}
                      >
                        Start Indexing Runner
                      </Button>
                    </div>
                  </div>
                </Modal>
              </motion.div>
            )}

            {activeTab === 'status' && (
              <motion.div
                key="status"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-8 max-w-4xl mx-auto"
              >
                <header>
                  <h2 className="text-2xl font-black text-slate-900 tracking-tight">Pipeline Logs</h2>
                  <p className="text-slate-500 text-sm">Monitor the progress of background code analysis tasks.</p>
                </header>

                {!livePipelines.length ? (
                  <div className="text-center py-20 bg-white border border-slate-200 border-dashed rounded-2xl flex flex-col items-center gap-4">
                    <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center text-slate-300">
                      <Activity size={24} />
                    </div>
                    <p className="text-slate-400 text-sm font-medium">No active pipeline runners found.</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {livePipelines.map((p) => (
                      <Card key={p.index_id}>
                        <div className="flex items-center justify-between mb-8 pb-8 border-b border-slate-100">
                          <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl flex items-center justify-center transition-all bg-blue-50 text-blue-500">
                              <Loader2 className="w-6 h-6 animate-spin" />
                            </div>
                            <div className="text-left">
                              <div className="flex items-center gap-3">
                                <h3 className="font-black text-lg text-slate-800 leading-none">RUNNING</h3>
                                <Badge variant="info">{p.status}</Badge>
                              </div>
                              <p className="text-[10px] font-mono text-slate-400 mt-1 uppercase tracking-wider">{p.index_id}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-bold text-slate-700">{p.repo_url}</p>
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1 underline decoration-primary/30 underline-offset-4">{p.branch}</p>
                          </div>
                        </div>

                        <div className="space-y-8 py-4 px-2">
                          <TimelineStep
                            label="Git Checkout & Clone"
                            completed={true}
                            active={false}
                            desc="Cloning target repository and checking out specified branch."
                            index={1}
                          />
                          <TimelineStep
                            label="AST Expression Mapping"
                            completed={false}
                            active={true}
                            desc="Extracting function definitions, class structures and call graphs."
                            index={2}
                          />
                          <TimelineStep
                            label="Vector Sync & Postgres Export"
                            completed={false}
                            active={false}
                            desc="Generating semantic embeddings and committing to primary storage."
                            index={3}
                            isLast
                          />
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {activeTab === 'execute' && (
              <motion.div
                key="execute"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="h-full flex flex-col gap-6"
              >
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
                  {/* Left Column: Config */}
                  <div className="lg:col-span-4 space-y-6 flex flex-col min-h-0 overflow-y-auto pr-2">
                    <Card title="Query Configuration" icon={<MessageSquare />}>
                      <div className="space-y-6">
                        <div className="grid grid-cols-1 gap-4">
                          <Input
                            label="Repository Name"
                            placeholder="e.g. my-repo"
                            value={execRepo}
                            onChange={(e) => setExecRepo(e.target.value)}
                          />
                          <Input
                            label="Target Branch"
                            placeholder="main"
                            value={execBranch}
                            onChange={(e) => setExecBranch(e.target.value)}
                          />
                        </div>

                        <div className="space-y-2">
                          <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Reasoning Goal</label>
                          <textarea
                            className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:border-primary/50 focus:ring-4 focus:ring-primary/5 focus:outline-none transition-all bg-slate-50/30 min-h-[120px] text-sm resize-none"
                            placeholder="Describe what you want to understand or find..."
                            value={instruction}
                            onChange={(e) => setInstruction(e.target.value)}
                          />
                        </div>

                        <div className="space-y-2">
                          <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest px-1">Semantic Keywords</label>
                          <Input
                            placeholder="auth, login, jwt..."
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                          />
                        </div>

                        <Button
                          className="w-full py-3"
                          loading={isExecuting}
                          onClick={handleExecute}
                          disabled={!instruction}
                          icon={<Zap size={16} />}
                        >
                          Run Reasoner
                        </Button>
                      </div>
                    </Card>

                    <Card className="bg-primary/5 border-primary/10 overflow-hidden relative">
                      <div className="relative z-10 space-y-3">
                        <div className="flex items-center gap-3 text-primary font-black uppercase tracking-tighter text-xs">
                          <Globe size={14} />
                          System Context
                        </div>
                        <p className="text-[11px] text-slate-500 leading-normal">
                          Reasoning is powered by the <strong className="text-primary italic">Unified LLM Driver</strong>.
                          Context windows are populated using a 0.85 similarity threshold.
                        </p>
                      </div>
                    </Card>
                  </div>

                  {/* Right Column: Results */}
                  <div className="lg:col-span-8 flex flex-col min-h-0">
                    <Card className="flex-1 flex flex-col min-h-0" title="Intelligence Output" icon={<Code2 />}>
                      <div className="p-0 flex flex-col h-full -mx-5 -my-5">
                        <div className="px-5 py-3 bg-slate-50/50 border-b border-slate-100 flex items-center justify-between shrink-0">
                          <div className="flex items-center gap-2">
                            {isExecuting && <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />}
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-tight">
                              {isExecuting ? "Generating response..." : "Query results"}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            {executionResult && (
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(executionResult);
                                }}
                                className="flex items-center gap-1.5 px-3 py-1 bg-white border border-slate-200 rounded-lg text-[10px] font-bold text-slate-500 hover:text-primary hover:border-primary/30 transition-all group"
                              >
                                <Copy size={12} />
                                <span>Copy Full Response</span>
                              </button>
                            )}
                            <Badge variant="neutral">GPT-4o Equivalent</Badge>
                          </div>
                        </div>

                        <div className="flex-1 overflow-y-auto p-6">
                          {isExecuting ? (
                            <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-6">
                              <div className="relative">
                                <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full animate-pulse"></div>
                                <div className="w-16 h-16 bg-white border-2 border-primary/20 rounded-2xl flex items-center justify-center relative">
                                  <Loader2 className="w-8 h-8 animate-spin text-primary" />
                                </div>
                              </div>
                              <div className="text-center space-y-1">
                                <p className="text-sm font-bold text-slate-700">Synthesizing Code Context</p>
                                <p className="text-xs text-slate-400">Mapping AST relations and resolving semantic fragments...</p>
                              </div>
                            </div>
                          ) : executionResult ? (
                            <div className="animate-slide-up text-left max-w-none">
                              <div className="intel-prose">
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    code(props) {
                                      const { children, className, ...rest } = props;
                                      const match = /language-(\w+)/.exec(className || '');
                                      const codeString = String(children).replace(/\n$/, '');

                                      if (match) {
                                        return (
                                          <div className="my-6 rounded-2xl overflow-hidden border border-slate-200 bg-slate-50 shadow-sm group/code">
                                            <div className="bg-slate-100/80 backdrop-blur-sm px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
                                              <div className="flex items-center gap-2">
                                                <div className="flex gap-1">
                                                  <div className="w-2.5 h-2.5 rounded-full bg-slate-300"></div>
                                                  <div className="w-2.5 h-2.5 rounded-full bg-slate-200"></div>
                                                  <div className="w-2.5 h-2.5 rounded-full bg-slate-100"></div>
                                                </div>
                                                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">{match[1]}</span>
                                              </div>
                                              <button
                                                onClick={() => navigator.clipboard.writeText(codeString)}
                                                className="p-1.5 hover:bg-white rounded-md text-slate-400 hover:text-primary transition-all active:scale-95"
                                                title="Copy Code"
                                              >
                                                <Copy size={14} />
                                              </button>
                                            </div>
                                            <div className="relative">
                                              <SyntaxHighlighter
                                                PreTag="div"
                                                children={codeString}
                                                language={match[1]}
                                                style={oneLight as any}
                                                customStyle={{
                                                  margin: 0,
                                                  padding: '1.5rem',
                                                  fontSize: '12px',
                                                  lineHeight: '1.7',
                                                  background: 'transparent',
                                                  fontFamily: '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
                                                }}
                                              />
                                            </div>
                                          </div>
                                        );
                                      }

                                      return (
                                        <code {...rest} className={cn("font-mono px-1.5 py-0.5 rounded bg-slate-100 text-primary-dark font-semibold text-[0.9em]", className)}>
                                          {children}
                                        </code>
                                      );
                                    },
                                    table(props) {
                                      return (
                                        <div className="overflow-x-auto my-6 rounded-xl border border-slate-200 shadow-sm">
                                          <table className="w-full text-sm text-left border-collapse" {...props} />
                                        </div>
                                      );
                                    }
                                  }}
                                >
                                  {executionResult}
                                </ReactMarkdown>
                              </div>
                            </div>
                          )
                            : (
                              <div className="h-full flex flex-col items-center justify-center text-slate-300 gap-4 border-2 border-dashed border-slate-100 rounded-3xl">
                                <div className="p-4 bg-slate-50 rounded-full">
                                  <SearchCode size={32} className="opacity-50" />
                                </div>
                                <div className="text-center">
                                  <p className="text-sm font-bold text-slate-500">Awaiting Instruction</p>
                                  <p className="text-xs text-slate-400">Specify details in the config panel to start execution.</p>
                                </div>
                              </div>
                            )}
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

// --- Specific UI Components ---

function SidebarLink({ icon, label, active, onClick, disabled, badge, badgeVariant = 'info' }: {
  icon: React.ReactNode,
  label: string,
  active: boolean,
  onClick: () => void,
  disabled?: boolean,
  badge?: string,
  badgeVariant?: 'info' | 'success' | 'warning' | 'error' | 'neutral'
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "w-full flex items-center justify-between px-4 py-2 rounded-lg transition-all group relative",
        active ? "bg-primary/5 text-primary border-l-2 border-primary rounded-l-none" : "hover:bg-slate-100 text-slate-500",
        disabled && "opacity-40 cursor-not-allowed"
      )}
    >
      <div className="flex items-center gap-3">
        <span className={cn("transition-colors", active ? "text-primary" : "text-slate-400 group-hover:text-slate-600")}>
          {icon}
        </span>
        <span className={cn("font-bold text-xs tracking-tight uppercase", active ? "text-primary" : "text-slate-600")}>{label}</span>
      </div>
      {badge && <Badge variant={badgeVariant}>{badge}</Badge>}
    </button>
  );
}

function StatCard({ label, value, delta, icon }: { label: string, value: string, delta: string, icon: React.ReactNode }) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <div className="space-y-4 flex-1">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-slate-50 rounded-lg text-slate-400">{icon}</div>
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">{label}</span>
          </div>
          <div className="flex items-end gap-3">
            <span className="text-2xl font-black text-slate-900 leading-none">{value}</span>
            <span className={cn(
              "text-[10px] font-black px-1.5 py-0.5 rounded-full mb-0.5",
              delta.includes('+') ? "bg-emerald-50 text-emerald-600" : "bg-slate-100 text-slate-600"
            )}>{delta}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

function Notification({ type, title, desc }: { type: 'info' | 'success' | 'warning', title: string, desc: string }) {
  const styles = {
    info: { color: 'text-blue-500', bg: 'bg-blue-50' },
    success: { color: 'text-emerald-500', bg: 'bg-emerald-50' },
    warning: { color: 'text-amber-500', bg: 'bg-amber-50' }
  };
  return (
    <div className="flex items-start gap-3">
      <div className={cn("w-1.5 h-1.5 rounded-full mt-2 ring-4 shrink-0", styles[type].color, styles[type].bg.slice(3) === '50' ? "ring-" + styles[type].color.slice(5) + "-100" : "")}></div>
      <div className="space-y-0.5">
        <p className="text-xs font-bold text-slate-800 tracking-tight">{title}</p>
        <p className="text-[10px] text-slate-500 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function TimelineStep({ label, desc, completed, active, index, isLast }: { label: string, desc: string, completed: boolean, active: boolean, index: number, isLast?: boolean }) {
  return (
    <div className="flex gap-4 group">
      <div className="flex flex-col items-center">
        <div className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center font-black text-xs transition-all relative z-10",
          completed ? "bg-emerald-500 text-white shadow-lg shadow-emerald-200" :
            active ? "bg-primary text-white animate-pulse" : "bg-slate-100 text-slate-400"
        )}>
          {completed ? <CheckCircle2 size={16} /> : index}
        </div>
        {!isLast && <div className={cn("w-0.5 flex-1 min-h-[40px] -my-1", completed ? "bg-emerald-500" : "bg-slate-100")}></div>}
      </div>
      <div className="pb-8 space-y-1">
        <div className="flex items-center gap-3">
          <h4 className={cn("text-xs font-black uppercase tracking-widest", completed ? "text-slate-800" : active ? "text-primary" : "text-slate-400")}>{label}</h4>
          {active && <Badge variant="info">In Progress</Badge>}
        </div>
        <p className="text-[11px] text-slate-500 leading-normal max-w-md">{desc}</p>
      </div>
    </div>
  );
}

const PlayIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-white">
    <path d="M5 3L19 12L5 21V3Z" stroke="none" />
  </svg>
);
