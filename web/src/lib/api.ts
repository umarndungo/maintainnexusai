// Backend configuration may use the versioned root; web paths include /api/v1.
export const apiOrigin = () => (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/api\/v1\/?$/, "").replace(/\/$/, "");

export type ApiResult<T> = {
  data: T | null;
  available: boolean;
  status?: number;
  error?: string;
};

export type UserRole = "engineer" | "supervisor" | "executive" | "technician";
export type CurrentUser = { id: string; name?: string; role: UserRole; station_ids: string[]; must_change_password?: boolean };
export type Prediction = { failure_probability: number; failure_predicted: boolean; risk_level: string; threshold: number; prediction_horizon_hours: number; target?: string; model_version?: string; prediction_id?: string; timestamp?: string; top_features?: string[] };
export type Thresholds = { failure_probability: number; warning_probability: number | null; prediction_horizon_hours: number; source: string; target?: string; sensor_limits: null };
export type EquipmentReading = { id: number; equipment_id: string; station_id?: string; telemetry: Record<string, string | number | null>; prediction: Prediction | null; state: string; evaluation_reason?: string; received_at: string };
export type Monitoring = { equipment: EquipmentReading[]; thresholds: Thresholds; source: string };
export type Technician = { id: string; name: string; certs: string[]; on_shift: boolean; active_work_orders: number };
export type RecentAlert = { task_id?: string; equipment_id: string; station_id?: string; part_number?: string; severity?: string; failure_code?: string; received_at?: string; required_cert?: string; telemetry?: Record<string, string | number | null>; prediction?: Prediction | null; model_version?: string; triggered_by_model?: boolean; threshold?: number; risk_probability?: number; pipeline?: { status: string; reason?: string } };
export type LifecycleEvent = { id: number; from_status?: string; to_status: string; actor_id: string; actor_role: string; note?: string; timestamp: string; event_hash?: string; previous_event_hash?: string };
export type DowntimeWindow = { id: number; work_order_id?: string; started_at: string; ended_at?: string | null; duration_seconds?: number; estimated_cost?: number; cause_alert_id?: string | null };

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
  alert_task_id?: string;
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

export type LoadingSlot = { id: number; truck_code: string; status: string; scheduled_arrival: string };
export type LoadingPoint = { id: number; bay_code: string; equipment_id?: string; station_id?: string; supported_product?: string; capacity_status: string };
export type LoadingPointDetail = LoadingPoint & { slots: LoadingSlot[] };
export type OperationalAction = { id: number; action_type: string; truck_code: string; status: string; idempotency_key: string };
export type OperationalOutcome = { action_success: boolean; actual_failure?: boolean | null; actual_delay_minutes?: number | null; alternate_bay_completed?: boolean | null };
export type Decision = {
  id: number;
  reading_id?: number | null;
  decision_type: string;
  reason: string;
  affected_equipment_id?: string;
  requires_human_approval: boolean;
  created_at: string;
};
export type DecisionDetail = Decision & { policy_version?: string | null; action: OperationalAction | null; outcome: OperationalOutcome | null };

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
    const response = await fetch(`${apiOrigin()}${path}`, {
      headers: { Accept: "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body?.detail;
      return { data: null, available: false, status: response.status, error: typeof detail === "string" ? detail : undefined };
    }

    return { data: (await response.json()) as T, available: true, status: response.status };
  } catch {
    return { data: null, available: false, error: "The API could not be reached or did not return a readable response." };
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
  return request<DowntimeWindow[]>(`/api/v1/dashboard/equipment/${encodeURIComponent(equipmentId)}/downtime`, token);
}

export function getReportSources(token: string) {
  return Promise.all([getExecutiveSummary(token), getMonitoring(token), request<WorkOrder[]>("/api/v1/maintenance/work-orders", token), request<RecentAlert[]>("/api/v1/alerts/recent", token)]);
}

// The current backend contract has no audit verification endpoint.
export async function getAuditVerification(): Promise<ApiResult<{ chain_integrity: boolean; checked_events: number; chain: string; verified_at: string }>> {
  return { data: null, available: false, error: "Audit verification is not supported by the current backend contract." };
}

export async function getCurrentUser(token: string): Promise<ApiResult<CurrentUser>> {
  let result = await request<CurrentUser>("/api/v1/auth/me", token);
  // Retry transient failures, never invalid credentials or authorization denials.
  if (!result.available && (result.status === undefined || result.status >= 500)) {
    result = await request<CurrentUser>("/api/v1/auth/me", token);
  }
  const user = result.data;
  if (user && (typeof user.id !== "string" || !["engineer", "supervisor", "executive", "technician"].includes(user.role) || !Array.isArray(user.station_ids) || !user.station_ids.every(station => typeof station === "string"))) {
    return { data: null, available: false, status: 502 };
  }
  return result;
}

export function getAuditLogs(token: string) {
  return request<AuditLog[]>("/api/v1/dashboard/audit-logs", token);
}

export function getMonitoring(token: string) {
  return request<Monitoring>("/api/v1/monitoring/equipment", token);
}

export function getEquipmentHistory(id: string, token: string) {
  return request<{ readings: EquipmentReading[]; thresholds: Thresholds }>(`/api/v1/monitoring/equipment/${encodeURIComponent(id)}/history`, token);
}

export function getMaintenanceData(token: string) {
  return Promise.all([
    request<WorkOrder[]>("/api/v1/maintenance/work-orders", token),
    request<RecentAlert[]>("/api/v1/alerts/recent", token),
    request<{ available_technicians: Technician[]; source: string }>("/api/v1/hr/technicians/available", token),
  ]);
}

// Decision engine (Predict -> Decide -> Act loading-point rerouting). See
// api/operations.py — read-only operations views for engineer/supervisor/executive.
export function getOperationsData(token: string) {
  return Promise.all([
    request<{ decisions: Decision[] }>("/api/v1/operations/decisions", token),
    request<{ loading_points: LoadingPoint[] }>("/api/v1/operations/loading-points", token),
  ]);
}

export function getDecision(decisionId: number, token: string) {
  return request<DecisionDetail>(`/api/v1/operations/decisions/${decisionId}`, token);
}

export function getLoadingPoint(loadingPointId: number, token: string) {
  return request<LoadingPointDetail>(`/api/v1/operations/loading-points/${loadingPointId}`, token);
}
