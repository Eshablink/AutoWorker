import { FormEvent, StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ActionStatus,
  createTask,
  DocumentItem,
  getDocuments,
  login,
  register,
  uploadDocument,
  getSystemStatus,
  decideApproval,
  getTaskDetail,
  listPendingApprovals,
  listTaskEvents,
  listTasks,
  PendingApproval,
  TaskDetail,
  TaskEvent,
  TaskStatus,
  TaskSummary,
  SystemStatus,
} from "./api";
import "./styles.css";

type View = "overview" | "documents" | "tasks" | "approvals" | "evidence" | "workers";

const STATUS_META: Record<TaskStatus, {label: string; tone: string; step: number}> = {
  CREATED: {label: "Queued", tone: "neutral", step: 0},
  PLANNING: {label: "Planning", tone: "info", step: 1},
  READY: {label: "Ready", tone: "info", step: 2},
  RUNNING: {label: "Executing", tone: "accent", step: 3},
  WAITING_APPROVAL: {label: "Needs approval", tone: "warning", step: 3},
  RECOVERING: {label: "Recovering", tone: "warning", step: 4},
  VERIFYING: {label: "Verifying", tone: "accent", step: 5},
  COMPLETED: {label: "Completed", tone: "success", step: 6},
  FAILED: {label: "Failed", tone: "danger", step: 6},
  CANCELLED: {label: "Cancelled", tone: "muted", step: 6},
};

const ACTION_META: Record<ActionStatus, {tone: string}> = {
  PENDING: {tone: "neutral"},
  RUNNING: {tone: "accent"},
  WAITING_APPROVAL: {tone: "warning"},
  APPROVED: {tone: "info"},
  REJECTED: {tone: "danger"},
  COMPLETED: {tone: "success"},
  FAILED: {tone: "danger"},
  SKIPPED: {tone: "muted"},
};

const NAV_ITEMS: Array<{id: View; label: string; icon: string}> = [
  {id: "overview", label: "Overview", icon: "◈"},
  {id: "documents", label: "Documents", icon: "▤"},
  {id: "tasks", label: "Tasks", icon: "▦"},
  {id: "approvals", label: "Approvals", icon: "✓"},
  {id: "evidence", label: "Evidence", icon: "◇"},
  {id: "workers", label: "Workers", icon: "◉"},
];

function AuthScreen({onAuthenticated}: {onAuthenticated: (token: string) => void}) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      setBusy(true); setError("");
      const response = mode === "register" ? await register(email, password) : await login(email, password);
      onAuthenticated(response.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally { setBusy(false); }
  }
  return <main className="appShell" style={{display:"grid",placeItems:"center",minHeight:"100vh"}}>
    <form className="panel" onSubmit={submit} style={{width:"min(460px,92vw)",padding:"32px"}}>
      <div className="microLabel">AUTOWORKER</div><h1>{mode === "register" ? "Create your workspace" : "Welcome back"}</h1>
      <p>Upload your own documents and run isolated worker tasks.</p>
      <input className="textInput" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
      <input className="textInput" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password (8+ characters)" />
      {error && <div className="errorBanner">{error}</div>}
      <button className="primaryButton" disabled={busy}>{busy ? "Working…" : mode === "register" ? "Create account" : "Sign in"}</button>
      <button type="button" className="ghostButton" onClick={() => setMode(mode === "register" ? "login" : "register")}>{mode === "register" ? "I already have an account" : "Create a new account"}</button>
    </form>
  </main>;
}

function DocumentsView({documents, onUpload, selectedId, onSelect}: {documents: DocumentItem[]; onUpload: (file: File) => void; selectedId: string; onSelect: (id: string) => void}) {
  return <div className="pageStack">
    <section className="panel" style={{padding:"24px"}}>
      <div className="panelHeader"><div><h2>Your documents</h2><p>Private to your account. Supported: PDF, TXT, Markdown, DOCX.</p></div><label className="primaryButton">Upload document<input type="file" hidden accept=".pdf,.txt,.md,.docx,application/pdf,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(e) => { const file=e.target.files?.[0]; if(file) onUpload(file); e.currentTarget.value=""; }} /></label></div>
      {!documents.length ? <EmptyState text="No documents yet. Upload one to give AutoWorker real context." /> : <div className="taskList">{documents.map((document) => <button className={document.document_id === selectedId ? "taskListItem selected" : "taskListItem"} key={document.document_id} onClick={() => onSelect(document.document_id)}><div className="taskListTop"><span>{document.media_type}</span><small>{Math.ceil(document.size_bytes/1024)} KB</small></div><strong>{document.filename}</strong><small>SHA-256 {document.sha256.slice(0,16)}…</small><p>{document.extracted_text_preview || "No text could be extracted from this document."}</p></button>)}</div>}
    </section>
  </div>;
}

function StatusPill({status}: {status: TaskStatus}) {
  const meta = STATUS_META[status];
  return <span className={`pill ${meta.tone}`}><i />{meta.label}</span>;
}

function ActionPill({status}: {status: ActionStatus}) {
  return <span className={`pill compact ${ACTION_META[status].tone}`}><i />{status.replaceAll("_", " ")}</span>;
}

function prettyTime(value?: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
}

function timeAgo(value?: string | null): string {
  if (!value) return "—";
  const delta = Math.max(0, Date.now() - new Date(value).getTime());
  const seconds = Math.floor(delta / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ago`;
}

function formatEventType(eventType: string): string {
  return eventType
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function valuePreview(value: Record<string, unknown>): string {
  const entries = Object.entries(value);
  if (!entries.length) return "No payload";
  return entries
    .slice(0, 3)
    .map(([key, item]) => `${key}: ${typeof item === "object" ? JSON.stringify(item) : String(item)}`)
    .join(" · ");
}

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("autoworker_token"));
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>("");
  const [view, setView] = useState<View>("overview");
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TaskDetail | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [goal, setGoal] = useState("");
  const [approvalComment, setApprovalComment] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [actingOnApproval, setActingOnApproval] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);

  const selectedTask = detail ?? tasks.find((task) => task.task_id === selectedId) ?? tasks[0] ?? null;

  const load = async (preserveError = false) => {
    try {
      if (!preserveError) setError(null);
      if (!token) return;
      const [nextTasks, nextApprovals, nextSystemStatus, nextDocuments] = await Promise.all([listTasks(), listPendingApprovals(), getSystemStatus(), getDocuments()]);
      // A successful poll clears any transient connection error from an earlier cold-start/request failure.
      setError(null);
      setTasks(nextTasks);
      setApprovals(nextApprovals);
      setSystemStatus(nextSystemStatus);
      setDocuments(nextDocuments);

      const id = selectedId ?? nextTasks[0]?.task_id;
      if (id) {
        setSelectedId(id);
        const [nextDetail, nextEvents] = await Promise.all([getTaskDetail(id), listTaskEvents(id)]);
        setDetail(nextDetail);
        setEvents(nextEvents);
      } else {
        setDetail(null);
        setEvents([]);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unable to reach AutoWorker API.";
      const isConnectionFailure = /failed to fetch|networkerror|load failed|unable to reach/i.test(message);
      setError(isConnectionFailure ? "The API is waking up or temporarily unavailable. Retrying automatically…" : message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(true), 3500);
    return () => window.clearInterval(timer);
  }, [selectedId, token]);

  const metrics = useMemo(() => {
    const running = tasks.filter((task) => ["RUNNING", "PLANNING", "VERIFYING", "RECOVERING"].includes(task.status)).length;
    const completed = tasks.filter((task) => task.status === "COMPLETED").length;
    const failed = tasks.filter((task) => task.status === "FAILED").length;
    return {total: tasks.length, running, completed, failed, approvals: approvals.length};
  }, [tasks, approvals]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    const value = goal.trim();
    if (value.length < 5) {
      setError("Give the worker a goal with at least 5 characters.");
      return;
    }
    try {
      setCreating(true);
      setError(null);
      const created = await createTask(value, selectedDocumentId || undefined);
      setGoal("");
      setSelectedId(created.task_id);
      setView("tasks");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Task creation failed.");
    } finally {
      setCreating(false);
    }
  }

  async function handleUpload(file: File) {
    try { setError(null); const uploaded = await uploadDocument(file); setDocuments((current) => [uploaded, ...current]); setSelectedDocumentId(uploaded.document_id); setView("documents"); }
    catch (err) { setError(err instanceof Error ? err.message : "Document upload failed."); }
  }

  async function handleApproval(approval: PendingApproval, status: "APPROVED" | "REJECTED") {
    try {
      setActingOnApproval(approval.approval_id);
      setError(null);
      await decideApproval(approval.approval_id, status, approvalComment);
      setApprovalComment("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval action failed.");
    } finally {
      setActingOnApproval(null);
    }
  }

  if (!token) return <AuthScreen onAuthenticated={(nextToken) => { localStorage.setItem("autoworker_token", nextToken); setToken(nextToken); }} />;

  if (!token) return <AuthScreen onAuthenticated={(nextToken) => { localStorage.setItem("autoworker_token", nextToken); setToken(nextToken); }} />;

  const title = view === "overview" ? "Operations overview"
    : view === "documents" ? "Your documents"
    : view === "tasks" ? "Task control"
    : view === "approvals" ? "Approval center"
    : view === "evidence" ? "Evidence & verification"
    : "Worker fleet";

  return (
    <main className="appShell">
      <aside className="sidebar">
        <div className="brandRow">
          <div className="logoMark"><span>AW</span><b>+</b></div>
          <div><strong>AutoWorker</strong><small>Autonomous control plane</small></div>
        </div>

        <div className="workspaceCard">
          <span>WORKSPACE</span>
          <strong>Operator Lab</strong>
          <small>{systemStatus ? `${systemStatus.database} · ${systemStatus.execution === "enabled" ? "execution enabled" : "execution disabled"}` : "Runtime status loading…"}</small>
        </div>

        <nav className="sideNav" aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={view === item.id ? "navItem active" : "navItem"}
              onClick={() => setView(item.id)}
            >
              <span>{item.icon}</span>
              {item.label}
              {item.id === "approvals" && approvals.length > 0 && <em>{approvals.length}</em>}
            </button>
          ))}
        </nav>

        <div className="sidebarBottom">
          <div className="runtimeCard">
            <div className="onlineDot" />
            <div><strong>API connected</strong><small>Runtime status refreshed with polling</small></div>
          </div>
          <small className="version">AUTOWORKER / OPERATOR CONSOLE</small>
        </div>
      </aside>

      <section className="mainCanvas">
        <header className="topbar">
          <div>
            <div className="breadcrumb">AUTOWORKER <span>/</span> {view.toUpperCase()}</div>
            <h1>{title}</h1>
            <p>Observe execution, review risk, and verify outcomes before calling work complete.</p>
          </div>
          <form className="createBar" onSubmit={handleCreate}>
            <span className="commandIcon">⌘</span>
            <input
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
              placeholder="Tell a worker what to do…"
              aria-label="Task goal"
            />
            <button className="primaryButton" disabled={creating}>
              {creating ? "Starting…" : "Run task"}
            </button>
          </form>
        </header>

        {error && (
          <div className="errorBanner" role="alert">
            <span>!</span>
            <div className="errorCopy">{error}</div>
            <button type="button" className="retryButton" onClick={() => void load()} disabled={loading}>Retry</button>
          </div>
        )}

        {view === "documents" && <DocumentsView documents={documents} onUpload={handleUpload} selectedId={selectedDocumentId} onSelect={setSelectedDocumentId} />}

        {view === "overview" && (
          <Overview
            tasks={tasks}
            approvals={approvals}
            selected={selectedTask}
            detail={detail}
            events={events}
            metrics={metrics}
            loading={loading}
            onSelect={(id) => { setSelectedId(id); setView("tasks"); }}
            onOpenApprovals={() => setView("approvals")}
          />
        )}

        {view === "tasks" && (
          <TasksView
            tasks={tasks}
            selectedId={selectedTask?.task_id ?? null}
            detail={detail}
            events={events}
            loading={loading}
            onSelect={setSelectedId}
          />
        )}

        {view === "approvals" && (
          <ApprovalsView
            approvals={approvals}
            comment={approvalComment}
            onCommentChange={setApprovalComment}
            actingId={actingOnApproval}
            onDecision={handleApproval}
            onOpenTask={(id) => { setSelectedId(id); setView("tasks"); }}
          />
        )}

        {view === "evidence" && <EvidenceView detail={detail} />}
        {view === "workers" && <WorkersView metrics={metrics} systemStatus={systemStatus} />}
      </section>
    </main>
  );
}

function Overview({
  tasks, approvals, selected, detail, events, metrics, loading, onSelect, onOpenApprovals,
}: {
  tasks: TaskSummary[];
  approvals: PendingApproval[];
  selected: TaskSummary | null;
  detail: TaskDetail | null;
  events: TaskEvent[];
  metrics: {total: number; running: number; completed: number; failed: number; approvals: number};
  loading: boolean;
  onSelect: (id: string) => void;
  onOpenApprovals: () => void;
}) {
  return (
    <div className="pageStack">
      <section className="metricGrid">
        <MetricCard label="Tasks tracked" value={metrics.total} helper="Persisted task records" icon="▦" />
        <MetricCard label="In flight" value={metrics.running} helper="Planning · execution · recovery" icon="↻" accent />
        <MetricCard label="Completed" value={metrics.completed} helper="Verified outcomes" icon="✓" success />
        <MetricCard label="Needs approval" value={metrics.approvals} helper="Human decision queue" icon="!" warning />
      </section>

      <section className="heroCard">
        <div className="heroCopy">
          <div className="liveLabel"><span className="pulseDot" /> CONTROL PLANE LIVE</div>
          <div className="heroTitleRow">
            <div>
              <span className="microLabel">CURRENT WORK</span>
              <h2>{selected?.goal ?? "No active work yet"}</h2>
              <p>{selected ? `Task ${selected.task_id.slice(0, 8)} · version ${selected.version}` : "Launch a task above to see the full execution lifecycle."}</p>
            </div>
            {selected && <StatusPill status={selected.status} />}
          </div>
          {selected && <LifecycleProgress status={selected.status} />}
        </div>
        <div className="heroOrb">
          <div className="orbRing ringOne" />
          <div className="orbRing ringTwo" />
          <div className="orbCore"><span>AI</span><strong>WORKER</strong></div>
        </div>
      </section>

      <div className="contentGrid">
        <section className="panel">
          <PanelHeader title="Execution timeline" meta={loading ? "SYNCING" : `${events.length} EVENTS`} />
          {events.length === 0 ? <EmptyState text="No persisted events for the selected task." /> : (
            <div className="timeline">
              {events.slice().reverse().slice(0, 8).map((event, index) => (
                <div className="timelineItem" key={event.event_id}>
                  <div className={index === 0 ? "timelineDot current" : "timelineDot"} />
                  <div className="timelineBody">
                    <div><strong>{formatEventType(event.event_type)}</strong><span>{prettyTime(event.timestamp)}</span></div>
                    <small>{event.actor}{event.action_id ? ` · action ${event.action_id.slice(0, 8)}` : ""}</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <PanelHeader title="Approval queue" meta={approvals.length ? "ACTION NEEDED" : "CLEAR"} />
          {approvals.length === 0 ? (
            <EmptyState text="No pending high-risk approvals. The queue is clear." />
          ) : (
            <>
              {approvals.slice(0, 3).map((approval) => <ApprovalMini key={approval.approval_id} approval={approval} onOpen={onOpenApprovals} />)}
              {approvals.length > 3 && <button className="textButton" onClick={onOpenApprovals}>View all {approvals.length} approvals →</button>}
            </>
          )}
        </section>
      </div>

      <section className="panel">
        <PanelHeader title="Recent tasks" meta="PERSISTED" />
        {tasks.length === 0 ? <EmptyState text="No tasks yet. Create your first operational goal above." /> : (
          <div className="taskTable">
            {tasks.slice(0, 6).map((task) => (
              <button className="taskRow" key={task.task_id} onClick={() => onSelect(task.task_id)}>
                <div className="taskId">{task.task_id.slice(0, 8)}</div>
                <div className="taskGoal">{task.goal}</div>
                <StatusPill status={task.status} />
                <div className="taskVersion">v{task.version}</div>
                <div className="chevron">→</div>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function TasksView({tasks, selectedId, detail, events, loading, onSelect}: {
  tasks: TaskSummary[]; selectedId: string | null; detail: TaskDetail | null; events: TaskEvent[]; loading: boolean; onSelect: (id: string) => void;
}) {
  return (
    <div className="splitView">
      <section className="panel taskListPanel">
        <PanelHeader title="Task queue" meta={`${tasks.length} TOTAL`} />
        <div className="taskList">
          {tasks.length === 0 ? <EmptyState text="No tasks have been created yet." /> : tasks.map((task) => (
            <button className={task.task_id === selectedId ? "taskListItem selected" : "taskListItem"} key={task.task_id} onClick={() => onSelect(task.task_id)}>
              <div className="taskListTop"><span>{task.task_id.slice(0, 8)}</span><StatusPill status={task.status} /></div>
              <strong>{task.goal}</strong>
              <small>Version {task.version}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="detailColumn">
        {detail ? (
          <>
            <section className="panel detailHero">
              <div className="detailHeading">
                <div className="microLabel">TASK {detail.task_id.slice(0, 8)}</div>
                <h2>{detail.goal}</h2>
                <div className="detailMeta"><StatusPill status={detail.status} /><span>Version {detail.version}</span><span>Step {detail.current_step_index + 1}</span></div>
              </div>
              <LifecycleProgress status={detail.status} />
              {detail.error_message && <div className="inlineError">{detail.error_message}</div>}
            </section>

            <section className="panel">
              <PanelHeader title="Action plan" meta={`${detail.actions.length} ACTIONS`} />
              <div className="actionStack">
                {detail.actions.map((action) => (
                  <div className={`actionCard ${action.status === "COMPLETED" ? "complete" : ""}`} key={action.action_id}>
                    <div className="actionIndex">{String(action.step_number).padStart(2, "0")}</div>
                    <div className="actionMain">
                      <div className="actionTop"><strong>{action.decision_summary}</strong><ActionPill status={action.status} /></div>
                      <div className="actionTool">{action.tool_id}{action.is_side_effecting ? <span className="riskTag">SIDE EFFECT</span> : null}</div>
                      {action.policy_decision && (
                        <div className="detailChips">
                          <span>Policy: {action.policy_decision.outcome}</span>
                          <span>Risk: {action.policy_decision.risk_level}</span>
                          <span>Rule set: {action.policy_decision.policy_version}</span>
                        </div>
                      )}
                      {action.approval_request && (
                        <div className="approvalInline"><span>Approval {action.approval_request.status}</span><small>{action.approval_request.reason_required}</small></div>
                      )}
                      {action.error_message && <small className="dangerText">{action.error_message}</small>}
                      {action.observation && <small className="observation">{action.observation}</small>}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="detailGrid">
              <section className="panel">
                <PanelHeader title="Verification" meta={detail.verification_result ? (detail.verification_result.success ? "PASSED" : "FAILED") : "PENDING"} />
                {detail.verification_result ? (
                  <div className="verificationBox">
                    <div className={detail.verification_result.success ? "verificationIcon success" : "verificationIcon danger"}>{detail.verification_result.success ? "✓" : "!"}</div>
                    <div><strong>{detail.verification_result.verification_type}</strong><p>{detail.verification_result.query_or_check}</p><small>Confidence {(detail.verification_result.confidence_score * 100).toFixed(0)}% · {prettyTime(detail.verification_result.evaluated_at)}</small></div>
                  </div>
                ) : <EmptyState text="Verification has not been recorded yet." />}
              </section>

              <section className="panel">
                <PanelHeader title="Audit trail" meta={`${events.length} EVENTS`} />
                <div className="compactTimeline">
                  {events.slice().reverse().slice(0, 5).map((event) => (
                    <div className="compactEvent" key={event.event_id}><span>{formatEventType(event.event_type)}</span><small>{event.actor} · {prettyTime(event.timestamp)}</small></div>
                  ))}
                  {!events.length && <EmptyState text="No audit events." />}
                </div>
              </section>
            </section>
          </>
        ) : <EmptyState text={loading ? "Loading task detail…" : "Select a task to inspect its lifecycle."} />}
      </section>
    </div>
  );
}

function ApprovalsView({approvals, comment, onCommentChange, actingId, onDecision, onOpenTask}: {
  approvals: PendingApproval[]; comment: string; onCommentChange: (value: string) => void; actingId: string | null;
  onDecision: (approval: PendingApproval, status: "APPROVED" | "REJECTED") => void; onOpenTask: (id: string) => void;
}) {
  return (
    <div className="pageStack">
      <section className="approvalBanner"><div><span className="microLabel">HUMAN-IN-THE-LOOP</span><h2>{approvals.length ? `${approvals.length} decision${approvals.length === 1 ? "" : "s"} need attention` : "Approval queue is clear"}</h2><p>High-risk actions stay paused until an explicit operator decision is recorded.</p></div><div className="shield">✓</div></section>
      {approvals.length === 0 ? <section className="panel"><EmptyState text="No pending approvals. Safe to keep the worker moving." /></section> : (
        <div className="approvalGrid">
          {approvals.map((approval) => (
            <article className="approvalCard" key={approval.approval_id}>
              <div className="approvalCardTop"><span className="riskTag high">{approval.risk_level} RISK</span><span>{timeAgo(approval.created_at)}</span></div>
              <h3>{approval.requested_action_name}</h3>
              <p className="approvalGoal" onClick={() => onOpenTask(approval.task_id)}>{approval.goal}</p>
              <div className="approvalReason"><span>WHY</span>{approval.reason_required}</div>
              <div className="approvalPayload"><span>PROPOSED INPUT</span><code>{valuePreview(approval.payload_summary)}</code></div>
              <div className="approvalExpiry">{approval.expired ? "Expired" : `Expires ${prettyTime(approval.expires_at)}`} · {approval.tool_id}</div>
              {!approval.expired && (
                <div className="approvalActions">
                  <textarea value={comment} onChange={(event) => onCommentChange(event.target.value)} placeholder="Optional decision note…" />
                  <div><button className="ghostButton" disabled={actingId === approval.approval_id} onClick={() => onDecision(approval, "REJECTED")}>Reject</button><button className="approveButton" disabled={actingId === approval.approval_id} onClick={() => onDecision(approval, "APPROVED")}>{actingId === approval.approval_id ? "Saving…" : "Approve action"}</button></div>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function EvidenceView({detail}: {detail: TaskDetail | null}) {
  const evidence = detail?.actions.flatMap((action) => action.evidence_refs.map((item) => ({...item, actionId: action.action_id, action: action.decision_summary}))) ?? [];
  const verificationEvidence = detail?.verification_result?.evidence_refs ?? [];
  return (
    <div className="pageStack">
      <section className="panel">
        <PanelHeader title="Evidence & verification" meta={detail ? `TASK ${detail.task_id.slice(0, 8)}` : "NO TASK"} />
        {!detail ? <EmptyState text="Select a task from the Tasks view to inspect evidence." /> : (
          <div className="evidenceLayout">
            <div className="evidenceSummary">
              <div className={detail.verification_result?.success ? "bigCheck success" : "bigCheck"}>{detail.verification_result?.success ? "✓" : "?"}</div>
              <div><span className="microLabel">VERIFICATION</span><h2>{detail.verification_result ? (detail.verification_result.success ? "Outcome verified" : "Verification failed") : "Awaiting verification"}</h2><p>{detail.verification_result?.query_or_check ?? "This task has not produced a verification result yet."}</p></div>
            </div>
            <div className="evidenceGrid">
              {[...evidence.map((item) => ({...item, source: "action"})), ...verificationEvidence.map((item) => ({...item, source: "verification", action: "Verification evidence"}))].map((item) => (
                <div className="evidenceItem" key={item.evidence_id}><div className="evidenceIcon">{item.source === "verification" ? "✓" : "◇"}</div><div><strong>{item.kind}</strong><small>{item.action}</small><code>{item.uri_or_path}</code>{item.hash_checksum && <small>SHA: {item.hash_checksum.slice(0, 16)}…</small>}</div></div>
              ))}
              {!evidence.length && !verificationEvidence.length && <EmptyState text="No evidence references attached to this task yet." />}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function WorkersView({metrics, systemStatus}: {metrics: {total: number; running: number; completed: number; failed: number; approvals: number}; systemStatus: SystemStatus | null}) {
  return (
    <div className="pageStack">
      <section className="metricGrid">
        <MetricCard label="Control plane" value="ONLINE" helper="FastAPI health path" icon="◉" success />
        <MetricCard label="Worker runtime" value={systemStatus?.execution === "enabled" ? "ENABLED" : "DISABLED"} helper={systemStatus?.worker_mode ?? "Status unavailable"} icon="↻" accent />
        <MetricCard label="Durable coordination" value="ON" helper="Idempotency + outbox" icon="◇" />
        <MetricCard label="Tracked outcomes" value={metrics.completed} helper={`${metrics.failed} failed tasks`} icon="✓" />
      </section>
      <section className="workerHero">
        <div className="workerGraphic"><div className="workerPulse" /><span>AW</span></div>
        <div><span className="microLabel">WORKER RUNTIME</span><h2>{systemStatus?.execution === "enabled" ? "Execution is enabled." : "No worker execution is attached."}</h2><p>Runtime state is reported by the API instead of being hard-coded in the console.</p><div className="detailChips"><span>{systemStatus?.database ?? "Database unknown"}</span><span>Leases</span><span>Queue</span><span>Verification</span></div></div>
      </section>
      <section className="contentGrid"><section className="panel"><PanelHeader title="Runtime guardrails" meta="ENFORCED" /><div className="guardrailList">{["Atomic side-effect idempotency","Database-backed worker leases","Heartbeat renewal","Approval expiry","Optimistic task concurrency","Independent verification"].map(item => <div key={item}><span>✓</span><strong>{item}</strong></div>)}</div></section><section className="panel"><PanelHeader title="Operational posture" meta="LIVE DATA" /><div className="postureStats"><div><strong>{metrics.total}</strong><span>tasks</span></div><div><strong>{metrics.running}</strong><span>in flight</span></div><div><strong>{metrics.approvals}</strong><span>approvals</span></div><div><strong>{metrics.failed}</strong><span>failed</span></div></div></section></section>
    </div>
  );
}

function LifecycleProgress({status}: {status: TaskStatus}) {
  const current = STATUS_META[status].step;
  const labels = ["Plan", "Policy", "Execute", "Recover", "Verify", "Done"];
  return <div className="lifecycle"><div className="line"><span style={{width: `${Math.min(100, Math.max(8, (current / 5) * 100))}%`}} /></div><div className="lifecycleLabels">{labels.map((label, index) => <div key={label} className={index <= current ? "reached" : ""}><i />{label}</div>)}</div></div>;
}

function MetricCard({label, value, helper, icon, accent, success, warning}: {label: string; value: number | string; helper: string; icon: string; accent?: boolean; success?: boolean; warning?: boolean}) {
  return <article className="metricCard"><div className={`metricIcon ${accent ? "accent" : success ? "success" : warning ? "warning" : ""}`}>{icon}</div><div><span>{label}</span><strong>{value}</strong><small>{helper}</small></div></article>;
}

function PanelHeader({title, meta}: {title: string; meta: string}) {
  return <div className="panelHeader"><div><h2>{title}</h2></div><span>{meta}</span></div>;
}

function EmptyState({text}: {text: string}) {
  return <div className="emptyState"><span>◇</span><p>{text}</p></div>;
}

function ApprovalMini({approval, onOpen}: {approval: PendingApproval; onOpen: () => void}) {
  return <button className="approvalMini" onClick={onOpen}><span className="riskTag high">{approval.risk_level}</span><div><strong>{approval.requested_action_name}</strong><small>{approval.tool_id} · {timeAgo(approval.created_at)}</small></div><b>→</b></button>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
