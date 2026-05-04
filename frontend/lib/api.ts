/**
 * API Client for Gateway Backend
 * Thin fetch wrapper that mirrors the mock-auth session shape
 * and provides typed methods for all gateway endpoints.
 *
 * Environment:
 *   NEXT_PUBLIC_GATEWAY_URL — base URL of the FastAPI backend
 *     default: http://localhost:8000
 */

const BASE_URL = process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("mock_auth_session");
  if (!raw) return null;
  try {
    const session = JSON.parse(raw);
    return session.access_token || null;
  } catch {
    return null;
  }
}

async function fetchJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export type GatewayUser = {
  id: string;
  email: string;
  user_metadata: {
    full_name: string;
    role: string;
    school: string;
    avatar_seed: string;
  };
};

export type GatewaySession = {
  user: GatewayUser;
  access_token: string;
  expires_at: number;
};

export async function login(email: string, password: string): Promise<{ session: GatewaySession; user: GatewayUser } | null> {
  const res = await fetchJson<{ data?: { session: GatewaySession; user: GatewayUser }; error?: { message: string } }>(
    "/gateway/v1/auth/login",
    {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }
  );
  if (res.error) return null;
  if (res.data?.session) {
    localStorage.setItem("mock_auth_session", JSON.stringify(res.data.session));
  }
  return res.data || null;
}

export async function register(
  email: string,
  password: string,
  full_name: string,
  role: string,
  school_name: string,
  district?: string,
  student_count_range?: string
): Promise<{ session: GatewaySession; user: GatewayUser } | null> {
  const res = await fetchJson<{
    data?: { session: GatewaySession; user: GatewayUser };
    error?: { message: string };
  }>("/gateway/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      full_name,
      role,
      school_name,
      district,
      student_count_range,
    }),
  });
  if (res.error) return null;
  if (res.data?.session) {
    localStorage.setItem("mock_auth_session", JSON.stringify(res.data.session));
  }
  return res.data || null;
}

export async function logout(): Promise<void> {
  const token = getToken();
  if (token) {
    await fetchJson("/gateway/v1/auth/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  }
  localStorage.removeItem("mock_auth_session");
}

export async function getSession(): Promise<GatewaySession | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetchJson<{ session: GatewaySession }>("/gateway/v1/auth/session", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return res.session;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export type DashboardKPIs = {
  total_calls: number;
  successful_contacts: number;
  failed_voicemail: number;
  active_agents: number;
};

export type DashboardResponse = {
  generated_at: string;
  kpis: DashboardKPIs;
  trends: Array<{ metric: string; value: string; direction: string; percentage?: string }>;
  recent_calls: Array<{
    id: string | number;
    student: string;
    type: string;
    status: string;
    time: string;
    duration: string;
  }>;
};

export async function fetchDashboard(): Promise<DashboardResponse> {
  return fetchJson<DashboardResponse>("/gateway/v1/analytics/dashboard");
}

export type SystemStatus = {
  gateway_status: string;
  ai_latency_ms: number;
  daily_quota_percent: number;
  active_calls: number;
  version: string;
};

export async function fetchSystemStatus(): Promise<SystemStatus> {
  return fetchJson<SystemStatus>("/gateway/v1/system/status");
}

// ---------------------------------------------------------------------------
// Students
// ---------------------------------------------------------------------------

export type Student = {
  id: number;
  tenant_id: string;
  name: string;
  grade: string;
  parent_name: string;
  parent_phone: string;
  attendance_status: string;
  recent_call_summary: string;
  created_at: string;
  updated_at: string;
};

export type StudentListResponse = {
  items: Student[];
  total: number;
  page: number;
  page_size: number;
};

export async function listStudents(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  grade?: string;
}): Promise<StudentListResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.search) qs.set("search", params.search);
  if (params?.grade) qs.set("grade", params.grade);
  return fetchJson<StudentListResponse>(`/gateway/v1/students?${qs.toString()}`);
}

export async function createStudent(student: Omit<Student, "id" | "tenant_id" | "created_at" | "updated_at">): Promise<Student> {
  return fetchJson<Student>("/gateway/v1/students", {
    method: "POST",
    body: JSON.stringify(student),
  });
}

export async function updateStudent(id: number, fields: Partial<Omit<Student, "id" | "tenant_id" | "created_at" | "updated_at">>): Promise<Student> {
  return fetchJson<Student>(`/gateway/v1/students/${id}`, {
    method: "PATCH",
    body: JSON.stringify(fields),
  });
}

export async function deleteStudent(id: number): Promise<void> {
  await fetchJson(`/gateway/v1/students/${id}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Calls
// ---------------------------------------------------------------------------

export type CallLog = {
  id: number;
  call_sid: string;
  tenant_id: string;
  student_id?: number;
  student_name?: string;
  domain?: string;
  direction?: string;
  phone_to?: string;
  phone_from?: string;
  status?: string;
  call_type?: string;
  duration_seconds: number;
  transcript_summary?: string;
  created_at: string;
  ended_at?: string;
};

export type CallListResponse = {
  items: CallLog[];
  total: number;
  page: number;
  page_size: number;
};

export type ActiveCall = {
  call_sid: string;
  student_name?: string;
  parent_name?: string;
  call_type: string;
  duration_seconds: number;
  status: string;
  transcript_count: number;
};

export async function listCalls(params?: { page?: number; page_size?: number; status?: string }): Promise<CallListResponse> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.status) qs.set("status", params.status);
  return fetchJson<CallListResponse>(`/gateway/v1/calls?${qs.toString()}`);
}

export async function listActiveCalls(): Promise<ActiveCall[]> {
  return fetchJson<ActiveCall[]>("/gateway/v1/calls/active");
}

export async function getTranscript(callSid: string): Promise<Array<{ speaker: string; text: string; timestamp_ms: number }>> {
  return fetchJson(`/gateway/v1/calls/${callSid}/transcript`);
}

export async function terminateCall(callSid: string): Promise<{ status: string }> {
  return fetchJson(`/gateway/v1/calls/${callSid}/terminate`, { method: "POST" });
}

// ---------------------------------------------------------------------------
// WebSocket (Live Calls)
// ---------------------------------------------------------------------------

export type WSMessage = {
  event: string;
  payload: Record<string, any>;
};

export function createCallsWebSocket(onMessage: (msg: WSMessage) => void, onOpen?: () => void, onClose?: () => void): WebSocket {
  const wsUrl = BASE_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws/gateway/calls";
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    onOpen?.();
  };

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      onMessage(msg);
    } catch {
      // ignore non-JSON
    }
  };

  ws.onclose = () => {
    onClose?.();
  };

  ws.onerror = (err) => {
    console.error("Gateway WebSocket error:", err);
  };

  return ws;
}
