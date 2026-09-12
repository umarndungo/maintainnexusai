# Data Requirements Matrix — Predict → Decide → Act → Learn

**Primary use case:** predict failure/disruption of pumps, loading arms and valves and automatically mitigate affected truck/loading operations.

**Provenance:** KPC-PUBLIC = verified public context; EXTERNAL-PUBLIC = public non-KPC dataset; INTERNAL = requires system access; SYNTHETIC = prototype-generated.

| Domain | Field | Equipment/process | Purpose | ML | Automation | Likely source |
|---|---|---|---|:---:|:---:|---|
| Asset | equipment_id | All | Stable identity | ✓ | ✓ | KPC-PUBLIC/INTERNAL/SYNTHETIC |
| Asset | equipment_type | All | Select model/features | ✓ | ✓ | KPC-PUBLIC/INTERNAL/SYNTHETIC |
| Asset | station_id | All | Station scope | ✓ | ✓ | KPC-PUBLIC/INTERNAL/SYNTHETIC |
| Asset | manufacturer/model | All | Equipment context | ✓ | ✓ | KPC-PUBLIC/INTERNAL/SYNTHETIC |
| Asset | installation_date | All | Age/degradation | ✓ | ✓ | KPC-PUBLIC/INTERNAL/SYNTHETIC |
| Asset | last_service_date | All | Maintenance features | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Asset | criticality | All | Decision priority | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Pump telemetry | vibration_rms | Pump | Mechanical degradation | ✓ | ✓ | INTERNAL/EXTERNAL-PUBLIC/SYNTHETIC |
| Pump telemetry | bearing_temperature | Pump | Thermal degradation | ✓ | ✓ | INTERNAL/EXTERNAL-PUBLIC/SYNTHETIC |
| Pump telemetry | motor_current | Pump | Motor/load anomaly | ✓ | ✓ | INTERNAL/EXTERNAL-PUBLIC/SYNTHETIC |
| Pump telemetry | suction_pressure | Pump | Hydraulic condition | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Pump telemetry | discharge_pressure | Pump | Hydraulic condition | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Pump telemetry | flow_rate | Pump | Performance anomaly | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Pump telemetry | rpm | Pump | Operating state | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Pump telemetry | running_hours | Pump | Wear exposure | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Arm telemetry | position | Loading arm | Position condition | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Arm telemetry | actuation_time_ms | Loading arm | Mechanical degradation | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Arm telemetry | actuator_pressure | Loading arm | Actuator condition | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Arm telemetry | vibration_rms | Loading arm | Mechanical degradation | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Arm telemetry | cycle_count | Loading arm | Wear exposure | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Valve telemetry | commanded_position | Valve | Command state | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Valve telemetry | actual_position | Valve | Actuation discrepancy | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Valve telemetry | opening_time_ms | Valve | Degradation | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Valve telemetry | closing_time_ms | Valve | Degradation | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Valve telemetry | actuator_pressure | Valve | Actuator condition | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Valve telemetry | upstream_pressure | Valve | Hydraulic condition | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Valve telemetry | downstream_pressure | Valve | Hydraulic condition | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Maintenance | failure_mode | All | Failure target/context | ✓ | ✓ | INTERNAL/EXTERNAL-PUBLIC/SYNTHETIC |
| Maintenance | failed_component | All | Failure diagnosis | ✓ | ✓ | INTERNAL/EXTERNAL-PUBLIC/SYNTHETIC |
| Maintenance | downtime_hours | All | Business impact | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Operations | truck_id | Truck | Affected operation | — | ✓ | INTERNAL/SYNTHETIC |
| Operations | scheduled_arrival | Truck | Scheduling | — | ✓ | INTERNAL/SYNTHETIC |
| Operations | loading_slot | Truck | Scheduling | — | ✓ | INTERNAL/SYNTHETIC |
| Operations | loading_point_id | Truck | Equipment dependency | — | ✓ | INTERNAL/SYNTHETIC |
| Operations | planned_volume | Truck | Capacity constraint | — | ✓ | INTERNAL/SYNTHETIC |
| Operations | priority | Truck | Decision policy | — | ✓ | INTERNAL/SYNTHETIC |
| Loading point | status/capacity | Loading point | Alternative capacity | — | ✓ | INTERNAL/SYNTHETIC |
| Loading point | supported_product | Loading point | Compatibility | — | ✓ | INTERNAL/SYNTHETIC |
| Spares | part_id/quantity | All | Intervention feasibility | — | ✓ | KPC-PUBLIC/INTERNAL/SYNTHETIC |
| Spares | lead_time_days | All | Business continuity | — | ✓ | KPC-PUBLIC/INTERNAL/SYNTHETIC |
| Prediction | risk_score | All | Risk decision | — | ✓ | ML-generated |
| Prediction | risk_level | All | Action policy | — | ✓ | ML-generated |
| Prediction | prediction_horizon_hours | All | Timing | — | ✓ | ML-generated |
| Prediction | top_features | All | Explainability | ✓ | ✓ | ML-generated |
| Decision | decision_type/reason | All | Action choice/audit | — | ✓ | Backend |
| Action | action_id/type/status | All | Trace automation | — | ✓ | Backend |
| Feedback | actual_failure | All | Model evaluation | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Feedback | actual_delay_minutes | Truck | Operational evaluation | ✓ | ✓ | INTERNAL/SYNTHETIC |
| Feedback | action_success | All | Automation evaluation | ✓ | ✓ | Backend |

## Baseline target
`failure_within_24h ∈ {0,1}`

Later targets (`failure_within_7d`, RUL, disruption prediction) are follow-ons, not prerequisites.

## Data separation
Historical/external training data stays in an offline training path. Live telemetry is for inference. Production history enters retraining only through an explicit reviewed export.
