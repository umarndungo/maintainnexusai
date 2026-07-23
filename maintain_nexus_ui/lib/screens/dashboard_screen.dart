// Dashboard screen for MaintainNexus.
//
// Displays high-level application status, quick actions, and navigation to
// recent work orders and alerts.
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';

import '../models/dashboard_summary.dart';
import '../models/work_order.dart';
import '../services/api_service.dart';
import 'create_order_screen.dart';
import 'recent_alerts_screen.dart';
import 'recent_work_orders_screen.dart';

/// Dashboard home screen for the MaintainNexus app.
///
/// Shows live summary counts and quick actions for work orders and alerts.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService apiService = ApiService();
  bool isLoading = false;
  String statusMessage = 'System Ready';
  int workOrderCount = 0;
  int alertCount = 0;
  List<Technician> availableTechnicians = [];
  List<InventoryItem> inventory = [];

  @override
  void initState() {
    super.initState();
    _loadDashboardCounts();
  }

  /// Refresh both alert and work order counts from the backend.
  ///
  /// This refresh is triggered on startup, when returning from child
  /// screens, and when the dashboard refresh action is tapped.
  Future<void> _loadDashboardCounts() async {
    setState(() {
      statusMessage = 'Refreshing dashboard summary...';
    });

    try {
      final summary = await apiService.fetchDashboardSummary();

      setState(() {
        workOrderCount = summary.workOrderCount;
        alertCount = summary.alertCount;
        availableTechnicians = summary.availableTechnicians;
        inventory = summary.inventory;
        statusMessage = 'Loaded $workOrderCount orders, $alertCount alerts.';
      });
    } catch (e) {
      setState(() {
        statusMessage = 'Dashboard refresh failed: $e';
      });
    }
  }

  /// Dispatches a sample work order through the API and updates the
  /// dashboard status text.
  Future<void> _triggerSampleDispatch() async {
    setState(() {
      isLoading = true;
      statusMessage = 'Dispatching sample work order...';
    });

    try {
      final orderIndex = Random().nextInt(9000) + 1000;
      final partIndex = Random().nextInt(90) + 10;
      final techIndex = Random().nextInt(900) + 100;

      final sample = WorkOrder(
        id: '',
        equipmentId: 'PUMP-$orderIndex',
        technicianId: 'TECH-$techIndex',
        partNumber: 'Pump Seal Kit #A$partIndex',
        status: 'PENDING',
        createdAt: DateTime.now().toUtc(),
        durationSeconds: 0,
      );

      final result = await apiService.dispatchWorkOrder(sample);
      setState(() {
        statusMessage = 'Dispatched: ${result.id} (${result.status})';
      });
      await _loadDashboardCounts();
    } catch (e) {
      setState(() {
        statusMessage = 'Dispatch failed: $e';
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  /// Sends a sample alert payload to the backend alert ingestion API.
  ///
  /// Once the alert is queued, the dashboard counts are refreshed after a
  /// small delay to give the async worker time to persist the alert.
  Future<void> _triggerSampleAlert() async {
    setState(() {
      isLoading = true;
      statusMessage = 'Sending sample alert...';
    });

    final alert = {
      'equipment_id': 'EQ-${Random().nextInt(9000) + 1000}',
      'part_number':
          'PART-${Random().nextInt(9999).toString().padLeft(4, '0')}-A',
      'severity': 'HIGH',
      'failure_code': 'ERR_SEAL_LEAK',
    };

    try {
      final response = await apiService.sendAlert(alert);
      setState(() {
        statusMessage = 'Alert queued: ${response['task_id'] ?? 'unknown'}';
      });

      final oldAlertCount = alertCount;
      const retryDelay = Duration(seconds: 2);
      const maxAttempts = 3;

      // Poll for the new alert count after the async ingestion pipeline runs.
      for (var attempt = 0; attempt < maxAttempts; attempt++) {
        await Future.delayed(retryDelay);
        await _loadDashboardCounts();
        if (alertCount > oldAlertCount) {
          break;
        }
      }
    } catch (e) {
      setState(() {
        statusMessage = 'Alert failed: $e';
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Widget _buildStatusCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 20,
          vertical: 18,
        ),
        leading: const Icon(
          Icons.analytics,
          color: Color(0xFF0284C7),
          size: 32,
        ),
        title: const Text(
          'System Status',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        subtitle: Text(statusMessage),
        trailing: isLoading
            ? const SizedBox(
                height: 28,
                width: 28,
                child: SpinKitCircle(color: Color(0xFF0284C7), size: 28),
              )
            : null,
      ),
    );
  }

  Widget _buildQuickActions() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF0284C7),
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
          onPressed: isLoading ? null : _triggerSampleDispatch,
          icon: const Icon(Icons.send),
          label: const Text('Trigger Work Order Dispatch'),
        ),
        const SizedBox(height: 12),
        ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF0B79D0),
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
          onPressed: isLoading ? null : _triggerSampleAlert,
          icon: const Icon(Icons.notification_add),
          label: const Text('Send Sample Alert'),
        ),
      ],
    );
  }

  Widget _buildSummaryCard(
    String title,
    IconData icon,
    Color iconColor,
    List<Widget> children,
  ) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: iconColor, size: 28),
                const SizedBox(width: 12),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _buildNavigationCards() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: _buildCardLink(
            title: 'Recent Work Orders',
            icon: Icons.assignment_turned_in,
            iconColor: const Color(0xFF0284C7),
            count: workOrderCount,
            countColor: const Color(0xFF0284C7),
            subtitle: 'View the latest dispatched orders and status details.',
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) =>
                      RecentWorkOrdersScreen(apiService: apiService),
                ),
              ).then((_) {
                _loadDashboardCounts();
              });
            },
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildCardLink(
            title: 'Recent Alerts',
            icon: Icons.notifications_active,
            iconColor: const Color(0xFF0B79D0),
            count: alertCount,
            countColor: const Color(0xFF0B79D0),
            subtitle: 'Open the latest received alerts queued for processing.',
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => RecentAlertsScreen(apiService: apiService),
                ),
              ).then((_) {
                _loadDashboardCounts();
              });
            },
          ),
        ),
      ],
    );
  }

  Widget _buildCardLink({
    required String title,
    required IconData icon,
    required Color iconColor,
    required int count,
    required Color countColor,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Card(
        elevation: 3,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: iconColor, size: 32),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  Chip(
                    backgroundColor: countColor.withAlpha(41),
                    label: Text(
                      '$count',
                      style: TextStyle(
                        color: countColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(subtitle),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MaintainNexus Control Center'),
        backgroundColor: const Color(0xFF0F172A),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh counts',
            onPressed: isLoading ? null : _loadDashboardCounts,
          ),
        ],
      ),
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadDashboardCounts,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildStatusCard(),
                const SizedBox(height: 20),
                _buildQuickActions(),
                const SizedBox(height: 24),
                _buildSummaryCard(
                  'Available Technicians',
                  Icons.engineering,
                  const Color(0xFF0F172A),
                  availableTechnicians.isEmpty
                      ? [const Text('No technicians currently on shift.')]
                      : availableTechnicians
                            .map(
                              (tech) => Padding(
                                padding: const EdgeInsets.only(bottom: 10.0),
                                child: Text(
                                  '${tech.name} (${tech.id}) • ${tech.certs.join(', ')}',
                                ),
                              ),
                            )
                            .toList(),
                ),
                const SizedBox(height: 16),
                _buildSummaryCard(
                  'Inventory Status',
                  Icons.inventory_2,
                  const Color(0xFF1F2937),
                  inventory.isEmpty
                      ? [const Text('No inventory data available.')]
                      : inventory
                            .map(
                              (item) => Padding(
                                padding: const EdgeInsets.only(bottom: 10.0),
                                child: Text(
                                  '${item.partNumber}: ${item.quantityAvailable} available ${item.inStock ? '(In stock)' : '(Out of stock)'}',
                                ),
                              ),
                            )
                            .toList(),
                ),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF0F172A),
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) =>
                            CreateOrderScreen(apiService: apiService),
                      ),
                    ).then((_) => _loadDashboardCounts());
                  },
                  icon: const Icon(Icons.add_box),
                  label: const Text('Create Manual Work Order'),
                ),
                const SizedBox(height: 24),
                _buildNavigationCards(),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
