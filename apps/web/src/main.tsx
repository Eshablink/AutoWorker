import { FormEvent, StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { createTask, listTaskEvents, listTasks, TaskEvent, TaskStatus, TaskSummary } from "./api";

const stages = [
  ["01", "Planning", "Turning the goal into safe executable actions."],
  ["02", "Execution", "Worker is interacting with the environment."],
  ["03", "Recovery", "Handling exceptions without losing state."],
  ["04", "Verification", "Proving the result before completion."],
];

const ACTIVE_STATUSES: TaskStatus[] = [
  "RUNNING",
  "PLANNING",
  "VERIFYING",
  "RECOVERING",
  "WAITING_APPROVAL",
];

const PROGRESS_BY_STATUS: Record<TaskStatus, number> = {
  CREATED: 8,
  PLANNING: 25,
  READY: 35,
  RUNNING: 60,
  WAITING_APPROVAL: 48,
  RECOVERING: 68,
  VERIFYING: 84,
  COMPLETED: 100,
  FAILED: 100,
  CANCELLED: 100,
};

function selectActiveTask(tasks: TaskSummary[]): TaskSummary | undefined {
  return tasks.find((task) => ACTIVE_STATUSES.includes(task.status)) ?? tasks[0];
}

function formatEventType(eventType: string): string {
  return eventType
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function App() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setError(null);
      const nextTasks = await listTasks();
      setTasks(nextTasks);
      const activeTask = selectActiveTask(nextTasks);
      if (activeTask) {
        setEvents(await listTaskEvents(activeTask.task_id));
      } else {
        setEvents([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach AutoWorker API.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(timer);
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = goal.trim();
    if (value.length < 5) return;
    try {
      setCreating(true);
      setError(null);
      await createTask(value);
      setGoal("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Task creation failed.");
    } finally {
      setCreating(false);
    }
  }

  const active = selectActiveTask(tasks);
  const statusLabel = active?.status?.replaceAll("_", " ") ?? "READY";
  const progress = active ? PROGRESS_BY_STATUS[active.status] : 0;

  return (
    <main className="shell">
      <aside className="rail">
        <div className="brand"><span>AW</span><div><b>AutoWorker</b><small>Autonomous operations</small></div></div>
        <nav><a className="active">Overview</a><a>Tasks</a><a>Approvals</a><a>Evidence</a><a>Workers</a></nav>
        <div className="worker"><i />Control plane <strong>Online</strong></div>
      </aside>

      <section className="content">
        <header>
          <div>
            <p className="eyebrow">AUTONOMOUS CONTROL CENTER</p>
            <h1>Good afternoon. <em>Your workers are ready.</em></h1>
            <p className="sub">Observe, approve and verify autonomous computer work from one place.</p>
          </div>
          <form onSubmit={submit} className="newTask">
            <input value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Tell a worker what to do…" aria-label="Task goal" />
            <button className="primary" disabled={creating}>{creating ? "Starting…" : "+ New task"}</button>
          </form>
        </header>

        {error && <div className="errorBanner" role="alert">{error}</div>}

        <section className="hero">
          <div>
            <div className="live"><i /> CONTROL PLANE</div>
            <h2>{active?.goal ?? "Ready for your first task"}</h2>
            <p>{active ? `Task ${active.task_id.slice(0, 8)} · current state: ${statusLabel}` : "Create a task to inspect its lifecycle and persisted audit trail."}</p>
            <div className="progress" aria-label={`Lifecycle progress ${progress}%`}><span style={{ width: `${progress}%` }} /></div>
            <small>{active ? `Version ${active.version} · ${statusLabel}` : "Waiting for first task"}</small>
          </div>
          <div className="orb"><div>AI<br /><b>WORKER</b></div></div>
        </section>

        <div className="grid">
          {stages.map(([n, t, d]) => <article key={n} className="stage"><span>{n}</span><h3>{t}</h3><p>{d}</p></article>)}
        </div>

        <section className="lower">
          <div className="panel">
            <div className="panelHead"><h2>Execution timeline</h2><span>{loading ? "SYNCING" : `${events.length} EVENTS`}</span></div>
            {events.length === 0 && <p>{active ? "No persisted events yet for this task." : "Create a task to start the live audit trail."}</p>}
            {events.slice().reverse().map((event) => (
              <div className="event" key={event.event_id}>
                <i className={event.event_type === "VERIFICATION_COMPLETED" ? "pulse" : ""} />
                <div>
                  <b>{formatEventType(event.event_type)}</b>
                  <small>{event.actor} · {new Date(event.timestamp).toLocaleTimeString()}</small>
                </div>
              </div>
            ))}
          </div>
          <div className="panel approval">
            <div className="panelHead"><h2>Task stream</h2><span>{tasks.length} TASKS</span></div>
            {tasks.length === 0 && <p>No tasks yet. Start one above and this view will update automatically.</p>}
            {tasks.slice(0, 4).map((task) => (
              <div className="event" key={task.task_id}>
                <i />
                <div><b>{task.goal}</b><small>{task.status.replaceAll("_", " ")} · v{task.version}</small></div>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
