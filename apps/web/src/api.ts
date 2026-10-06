export type TaskStatus =
  | "CREATED"
  | "PLANNING"
  | "READY"
  | "RUNNING"
  | "WAITING_APPROVAL"
  | "RECOVERING"
  | "VERIFYING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export interface TaskSummary {
  task_id: string;
  goal: string;
  status: TaskStatus;
  version: number;
}

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, {
    ...init,
    headers: {"Content-Type": "application/json", ...(init?.headers ?? {})},
  });
  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function listTasks(limit = 20): Promise<TaskSummary[]> {
  return request<TaskSummary[]>(`/tasks?limit=${limit}`);
}

export function createTask(goal: string): Promise<TaskSummary> {
  return request<TaskSummary>("/tasks", {
    method: "POST",
    body: JSON.stringify({goal}),
  });
}
