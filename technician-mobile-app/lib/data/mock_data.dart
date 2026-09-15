import '../models/checklist_step.dart';
import '../models/work_order.dart';

/// Demo data standing in for the backend described in the spec's system
/// architecture diagram (Part 1 · Mobile · 02) — no network calls are
/// made yet. Every value here (equipment IDs, risk drivers, part
/// numbers) is taken directly from the spec's own worked example so the
/// screens read exactly like the mockups they implement.
class MockData {
  MockData._();

  static List<WorkOrder> workOrders() => [
        WorkOrder(
          id: 'WO-3391',
          equipmentType: 'PUMP',
          equipmentCode: 'P-14',
          station: 'STN-B',
          title: 'Bearing vibration exceeds threshold',
          riskLevel: 'HIGH',
          riskScore: 0.87,
          status: WorkOrderStatus.dispatched,
          statusNote: 'Dispatched 6 min ago · Approved by station engineer',
          approvedBy: 'Station engineer',
          riskDrivers: const [
            RiskDriver(label: 'Vibration', value: '3.2× baseline'),
            RiskDriver(label: 'Pressure trend (6 hr)', value: 'Rising'),
            RiskDriver(label: 'Time since last service', value: '118 days'),
          ],
          reservedPart: 'Seal kit SK-14B · Bay 3 shelf 6',
          startedNote: 'Started 14 min ago',
          checklist: [
            ChecklistStep(label: 'Isolate & lock out pump P-14', complete: true),
            ChecklistStep(label: 'Remove drive coupling guard', complete: true),
            ChecklistStep(label: 'Inspect bearing housing for play'),
            ChecklistStep(label: 'Replace seal kit SK-14B'),
            ChecklistStep(label: 'Reassemble & verify vibration < 1.1×'),
          ],
        ),
        WorkOrder(
          id: 'WO-3387',
          equipmentType: 'ARM',
          equipmentCode: 'LA-07',
          station: 'STN-A',
          title: 'Pressure drift on load cycle',
          riskLevel: 'MEDIUM',
          riskScore: 0.54,
          status: WorkOrderStatus.dispatched,
          statusNote: 'Dispatched 22 min ago',
          riskDrivers: const [
            RiskDriver(label: 'Pressure variance', value: '+18% vs baseline'),
            RiskDriver(label: 'Load cycles today', value: '212'),
          ],
          reservedPart: 'Hydraulic hose kit HK-07 · Bay 1 shelf 2',
          checklist: [
            ChecklistStep(label: 'Isolate & lock out loading arm LA-07'),
            ChecklistStep(label: 'Inspect hydraulic hose for wear'),
            ChecklistStep(label: 'Replace hose kit HK-07'),
            ChecklistStep(label: 'Cycle test & verify pressure holds'),
          ],
        ),
        WorkOrder(
          id: 'WO-3402',
          equipmentType: 'VALVE',
          equipmentCode: 'V-22',
          station: 'STN-A',
          title: 'Routine inspection due',
          riskLevel: 'LOW',
          riskScore: 0.08,
          status: WorkOrderStatus.scheduled,
          statusNote: 'Scheduled · not yet started',
          checklist: [
            ChecklistStep(label: 'Visual inspection of valve body'),
            ChecklistStep(label: 'Check actuator response time'),
            ChecklistStep(label: 'Log inspection result'),
          ],
        ),
      ];
}
