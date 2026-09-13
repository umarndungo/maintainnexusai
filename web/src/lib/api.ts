const apiBaseUrl = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type ApiResult<T> = {
  data: T | null;
  available: boolean;
  status?: number;
};

export type UserRole = "engineer" | "supervisor" | "executive" | "technician";
export type CurrentUser = { id: string; name?: string; role: UserRole; station_ids: string[] };
export type RecentAlert = { task_id?: string; equipment_id: string; severity?: string; failure_code?: string; received_at?: string };
export type LifecycleEvent = { id: number; from_status?: string; to_status: string; actor_id: string; actor_role: string; note?: string; timestamp: string; risk_drivers?: WorkOrder["risk_drivers"]; top_features?: string[] };

export type DashboardSummary = {
  available_technicians?: Array<{ id: string; name: string; certs?: string[] }>;
  inventory?: Array<{ part_number: string; quantity_available: number; in_stock: boolean }>;
  work_order_count?: number;
  alert_count?: number;
  incident_count?: number;
  open_work_orders?: number;
  downtime_minutes?: number;
  mean_repair_time_minutes?: number;
  uptime_percentage?: number;
  recent_health_checks?: Array<{
    equipment_id?: string;
    temperature?: number;
    vibration?: number;
    risk_probability?: number;
    health_status?: string;
    checked_at?: string;
  }>;
};

export type WorkOrder = {
  work_order_id: string;
  equipment_id: string;
  assigned_technician_id?: string;
  reserved_part?: string;
  status?: string;
  created_at?: string;
  risk_drivers?: Array<{ feature: string; value: number; reason: string }>;
};

export type ExecutiveSummary = {
  downtime_avoided_minutes?: number;
  cost_saved?: number;
  downtime_minutes?: number;
  downtime_windows?: number;
  completed_windows?: number;
  open_windows?: number;
  uptime_trend?: Array<{ date: string; uptime: number }> | string;
  station_comparison?: Array<{ station_id: string; uptime: number }>;
};

export type AuditLog = {
  id: number;
  event_name: string;
  payload: string;
  timestamp: string;
};

export type HseOverview = {
  tank_id: string;
  level_percent: number;
  safe_level_percent: number;
  flow_rate_lpm: number;
  max_flow_rate_lpm: number;
  minutes_to_safe_limit: number | null;
  severity: string;
  recommended_action: string;
  drivers: string[];
  source: string;
  checked_at: string;
};

async function request<T>(path: string, token?: string): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      headers: { Accept: "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      return { data: null, available: false, status: response.status };
    }

    return { data: (await response.json()) as T, available: true, status: response.status };
  } catch {
    return { data: null, available: false };
  }
}

export function getDashboardData(token?: string) {
  return Promise.all([
    request<DashboardSummary>("/api/v1/dashboard/summary", token),
    request<WorkOrder[]>("/api/v1/maintenance/work-orders", token),
    request<AuditLog[]>("/api/v1/dashboard/audit-logs", token),
    request<HseOverview>("/api/v1/hse/overview", token),
    request<RecentAlert[]>("/api/v1/alerts/recent", token),
  ]);
}

export function getExecutiveSummary(token: string) {
  return request<ExecutiveSummary>("/api/v1/dashboard/executive-summary", token);
}

export function getLifecycle(workOrderId: string, token: string) {
  return request<LifecycleEvent[]>(`/api/v1/maintenance/work-orders/${encodeURIComponent(workOrderId)}/lifecycle`, token);
}

export function getDowntime(equipmentId: string, token: string) {
  return request<Array<{ id: number; work_order_id?: string; started_at: string; ended_at?: string; duration_seconds?: number; estimated_cost?: number }>>(`/api/v1/dashboard/equipment/${encodeURIComponent(equipmentId)}/downtime`, token);
}

export function getAuditVerification(token: string) {
  return request<{ chain_integrity: boolean; checked_events: number; chain: string; verified_at: string }>("/api/v1/dashboard/audit-logs/verify", token);
}

export async function getCurrentUser(token: string): Promise<ApiResult<CurrentUser>> {
  const result = await request<CurrentUser>("/api/v1/auth/me", token);
  const user = result.data;
  if (user && (typeof user.id !== "string" || !["engineer", "supervisor", "executive", "technician"].includes(user.role) || !Array.isArray(user.station_ids) || !user.station_ids.every(station => typeof station === "string"))) {
    return { data: null, available: false, status: 502 };
  }
  return result;
}

export function getAuditLogs(token: string) {
  return request<AuditLog[]>("/api/v1/dashboard/audit-logs", token);
}
