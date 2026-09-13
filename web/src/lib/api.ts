const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000";

type ApiResult<T> = {
  data: T | null;
  available: boolean;
};

export type DashboardSummary = {
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
  uptime_trend?: Array<{ date: string; uptime: number }>;
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
      next: { revalidate: 10 },
    });

    if (!response.ok) {
      return { data: null, available: false };
    }

    return { data: (await response.json()) as T, available: true };
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
  ]);
}

export function getExecutiveSummary(token: string) {
  return request<ExecutiveSummary>("/api/v1/dashboard/executive-summary", token);
}

export function getLifecycle(workOrderId: string, token: string) {
  return request<Array<{ id: number; from_status?: string; to_status: string; actor_id: string; actor_role: string; note?: string; timestamp: string }>>(`/api/v1/maintenance/work-orders/${encodeURIComponent(workOrderId)}/lifecycle`, token);
}

export function getDowntime(equipmentId: string, token: string) {
  return request<Array<{ id: number; work_order_id?: string; started_at: string; ended_at?: string; estimated_cost?: number }>>(`/api/v1/dashboard/equipment/${encodeURIComponent(equipmentId)}/downtime`, token);
}

export function getAuditVerification(token: string) {
  return request<{ chain_integrity: boolean; checked_events: number; chain: string; verified_at: string }>("/api/v1/dashboard/audit-logs/verify", token);
}
