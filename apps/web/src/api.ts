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

export type ActionStatus =
  | "PENDING"
  | "RUNNING"
  | "WAITING_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED";

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";

export interface TaskSummary {
  task_id: string;
  goal: string;
  status: TaskStatus;
  version: number;
}

export interface TaskAction {
  action_id: string;
  task_id: string;
  step_number: number;
  tool_id: string;
  tool_input: Record<string, unknown>;
  tool_output?: Record<string, unknown> | null;
  is_side_effecting: boolean;
  idempotency_key?: string | null;
  status: ActionStatus;
  decision_summary: string;
  reason_code?: string | null;
  observation?: string | null;
  error_message?: string | null;
  retry_count: number;
  max_retries: number;
  policy_decision?: {
    decision_id: string;
    outcome: "ALLOW" | "DENY" | "REQUIRE_APPROVAL";
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    reason: string;
    policy_version: string;
    created_at: string;
  } | null;
  approval_request?: {
    approval_id: string;
    status: ApprovalStatus;
    requested_action_name: string;
    tool_id: string;
    payload_summary: Record<string, unknown>;
    risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    reason_required: string;
    created_at: string;
    expires_at?: string | null;
    decided_at?: string | null;
  } | null;
  evidence_refs: Array<{
    evidence_id: string;
    kind: string;
    uri_or_path: string;
    hash_checksum?: string | null;
  }>;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface VerificationResult {
  verification_id: string;
  task_id: string;
  action_id?: string | null;
  success: boolean;
  verification_type: string;
  query_or_check: string;
  expected_state: Record<string, unknown>;
  actual_state: Record<string, unknown>;
  confidence_score: number;
  evidence_refs: Array<{
    evidence_id: string;
    kind: string;
    uri_or_path: string;
    hash_checksum?: string | null;
  }>;
  evaluated_at: string;
}

export interface TaskDetail extends TaskSummary {
  current_step_index: number;
  error_message?: string | null;
  actions: TaskAction[];
  verification_result?: VerificationResult | null;
}

export interface TaskEvent {
  event_id: string;
  task_id: string;
  action_id?: string | null;
  event_type: string;
  actor: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface PendingApproval {
  approval_id: string;
  task_id: string;
  action_id: string;
  goal: string;
  requested_action_name: string;
  tool_id: string;
  payload_summary: Record<string, unknown>;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  reason_required: string;
  status: ApprovalStatus;
  created_at: string;
  expires_at?: string | null;
  expired: boolean;
}

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "/api";
const API_TOKEN = import.meta.env.VITE_API_TOKEN as string | undefined;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API_BASE + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(API_TOKEN ? {"Authorization": "Bearer " + API_TOKEN} : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const fallback = `Request failed: ${response.status} ${response.statusText}`.trim();
    const rawBody = await response.text();

    if (rawBody) {
      try {
        const body = JSON.parse(rawBody) as { detail?: string; message?: string };
        const detail =
          typeof body.detail === "string"
            ? body.detail
            : typeof body.message === "string"
              ? body.message
              : undefined;

        throw new Error(detail ?? fallback);
      } catch (error) {
        if (error instanceof Error && error.message !== "Unexpected end of JSON input") {
          throw error;
        }
      }

      throw new Error(rawBody);
    }

    throw new Error(fallback);
  }

  return response.json() as Promise<T>;
}

export function listTasks(limit = 50): Promise<TaskSummary[]> {
  return request<TaskSummary[]>(`/tasks?limit=${limit}`);
}

export function getTaskDetail(taskId: string): Promise<TaskDetail> {
  return request<TaskDetail>(`/tasks/${taskId}/detail`);
}

export function createTask(goal: string): Promise<TaskSummary> {
  return request<TaskSummary>("/tasks", {
    method: "POST",
    body: JSON.stringify({goal}),
  });
}

export function listTaskEvents(taskId: string, limit = 100): Promise<TaskEvent[]> {
  return request<{task_id: string; events: TaskEvent[]}>(`/tasks/${taskId}/events?limit=${limit}`).then(
    (response) => response.events,
  );
}

export function listPendingApprovals(limit = 50): Promise<PendingApproval[]> {
  return request<PendingApproval[]>(`/approvals?limit=${limit}`);
}

export function decideApproval(
  approvalId: string,
  status: Exclude<ApprovalStatus, "PENDING" | "EXPIRED">,
  comment?: string,
  approverId = "operator-console",
): Promise<{
  approval_id: string;
  task_id: string;
  status: ApprovalStatus;
  task_status: TaskStatus;
}> {
  return request(`/approvals/${approvalId}`, {
    method: "POST",
    body: JSON.stringify({status, comment: comment || null, approver_id: approverId}),
  });
}
