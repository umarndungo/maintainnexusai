// Dashboard screen for MaintainNexus.
//
// Displays high-level application status, quick actions, and navigation to
// recent work orders and alerts.
import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/dashboard_summary.dart';
import '../models/work_order.dart';
import '../services/api_service.dart';
import 'audit_logs_screen.dart';
import 'create_order_screen.dart';
import 'equipment_health_check_screen.dart';
import 'inventory_status_screen.dart';
import 'recent_alerts_screen.dart';
import 'recent_work_orders_screen.dart';
import 'technicians_screen.dart';

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
  int incidentCount = 0;
  int openWorkOrders = 0;
  double downtimeMinutes = 0.0;
  double meanRepairTimeMinutes = 0.0;
  double uptimePercentage = 0.0;
  List<Technician> availableTechnicians = [];
  List<InventoryItem> inventory = [];
  List<HealthCheck> recentHealthChecks = [];

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
        incidentCount = summary.incidentCount;
        openWorkOrders = summary.openWorkOrders;
        downtimeMinutes = summary.downtimeMinutes;
        meanRepairTimeMinutes = summary.meanRepairTimeMinutes;
        uptimePercentage = summary.uptimePercentage;
        availableTechnicians = summary.availableTechnicians;
        inventory = summary.inventory;
        recentHealthChecks = summary.recentHealthChecks;
        statusMessage = summary.backendStatus == 'ok'
            ? 'Loaded $workOrderCount orders, $alertCount alerts.'
            : 'Backend status: ${summary.backendStatus}. Loaded $workOrderCount orders, $alertCount alerts.';
      });
    } catch (e) {
      setState(() {
        statusMessage = 'Connecting ...';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Unable to refresh dashboard data. Retrying connection...',
          ),
          action: SnackBarAction(
            label: 'Retry',
            onPressed: _loadDashboardCounts,
          ),
          duration: const Duration(seconds: 5),
        ),
      );
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

  Widget _buildQuickActions() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Manual operational simulation',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildSmallSimulationButton(
                    icon: Icons.send,
                    label: 'Repair Assignment',
                    color: const Color(0xFFC8102E),
                    onPressed: isLoading ? null : _triggerSampleDispatch,
                  ),
                  const SizedBox(width: 12),
                  _buildSmallSimulationButton(
                    icon: Icons.notification_add,
                    label: 'Equipment Issue',
                    color: const Color(0xFF111111),
                    onPressed: isLoading ? null : _triggerSampleAlert,
                  ),
                  const SizedBox(width: 12),
                  _buildSmallSimulationButton(
                    icon: Icons.health_and_safety,
                    label: 'Health Check',
                    color: const Color(0xFF111111),
                    onPressed: isLoading ? null : _triggerSampleHealthCheck,
                  ),
                  const SizedBox(width: 12),
                  _buildSmallSimulationButton(
                    icon: Icons.add_box,
                    label: 'Create Order',
                    color: const Color(0xFF111111),
                    onPressed: isLoading ? null : _navigateToCreateOrderScreen,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSmallSimulationButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback? onPressed,
  }) {
    return ElevatedButton.icon(
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
        minimumSize: const Size(150, 48),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
        ),
      ),
      onPressed: onPressed,
      icon: Icon(icon, size: 20),
      label: Text(label),
    );
  }

  Future<void> _triggerSampleHealthCheck() async {
    setState(() {
      isLoading = true;
      statusMessage = 'Simulating health check...';
    });

    try {
      await _loadDashboardCounts();
      setState(() {
        statusMessage = 'Health check simulated successfully.';
      });
    } catch (e) {
      setState(() {
        statusMessage = 'Health check failed: $e';
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Future<void> _navigateToCreateOrderScreen() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CreateOrderScreen(apiService: apiService),
      ),
    );
    await _loadDashboardCounts();
  }

  Future<void> _navigateToEquipmentHealthScreen() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => EquipmentHealthCheckScreen(apiService: apiService),
      ),
    );
  }

  Future<void> _navigateToTechniciansScreen() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => TechniciansScreen(technicians: availableTechnicians),
      ),
    );
  }

  Future<void> _navigateToInventoryStatusScreen() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => InventoryStatusScreen(inventory: inventory),
      ),
    );
  }

  Future<void> _navigateToAuditLogsScreen() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AuditLogsScreen(apiService: apiService),
      ),
    );
  }

  Widget _buildKpiCards() {
    final inStockCount = inventory.where((item) => item.inStock).length;
    final totalParts = inventory.length;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: _buildKpiCard(
            title: 'Issues Seen',
            value: '$alertCount',
            subtitle: 'Total alerts received',
            color: const Color(0xFFC8102E),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildKpiCard(
            title: 'Active Tasks',
            value: '$openWorkOrders',
            subtitle: 'Repair tasks in progress',
            color: const Color(0xFF111111),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildKpiCard(
            title: 'Team Ready',
            value: '${availableTechnicians.length}',
            subtitle: 'Technicians currently on shift',
            color: const Color(0xFF111111),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildKpiCard(
            title: 'Parts In Stock',
            value: '$inStockCount / $totalParts',
            subtitle: 'Healthy inventory coverage',
            color: const Color(0xFF6B7280),
          ),
        ),
      ],
    );
  }

  Widget _buildKpiCard({
    required String title,
    required String value,
    required String subtitle,
    required Color color,
  }) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              value,
              style: const TextStyle(
                fontSize: 26,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(subtitle),
          ],
        ),
      ),
    );
  }

  // ignore: unused_element
  Widget _buildProcessFlow() {
    final steps = [
      {'label': 'Issue detected', 'icon': Icons.warning_amber, 'color': Color(0xFFF59E0B)},
      {'label': 'Stock checked', 'icon': Icons.inventory_2, 'color': Color(0xFFC8102E)},
      {'label': 'Technician assigned', 'icon': Icons.engineering, 'color': Color(0xFF111111)},
      {'label': 'Repair task created', 'icon': Icons.assignment_turned_in, 'color': Color(0xFF111111)},
    ];

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: steps
              .map(
                (step) => Expanded(
                  child: Column(
                    children: [
                      CircleAvatar(
                        radius: 22,
                        backgroundColor: step['color'] as Color,
                        child: Icon(
                          step['icon'] as IconData,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        step['label'] as String,
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              )
              .toList(),
        ),
      ),
    );
  }

  Widget _buildExecutiveSummaryCard() {
    return Card(
      elevation: 3,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      color: const Color(0xFF111111),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Executive Summary',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 20,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              statusMessage,
              style: const TextStyle(color: Colors.white70, fontSize: 16),
            ),
            const SizedBox(height: 14),
            Text(
              'Current state: $alertCount issues tracked, ${availableTechnicians.length} technicians ready, and $openWorkOrders active repair tasks.',
              style: const TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard(
    String title,
    IconData icon,
    Color iconColor,
    List<Widget> children, {
    Widget? action,
  }) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
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
                if (action != null) action,
              ],
            ),
            const SizedBox(height: 16),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _buildHealthChecksCard() {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: const [
                    Icon(Icons.thermostat, color: Color(0xFFC8102E), size: 28),
                    SizedBox(width: 12),
                    Text(
                      'Recent Equipment Health',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFC8102E),
                    padding: const EdgeInsets.symmetric(
                      vertical: 10,
                      horizontal: 14,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  onPressed: isLoading ? null : _navigateToEquipmentHealthScreen,
                  child: const Text('View equipment health'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (recentHealthChecks.isEmpty)
              const Text('No recent health checks available.')
            else
              Column(
                children: [
                  _buildHealthRiskBarChart(),
                  const SizedBox(height: 16),
                  ...recentHealthChecks.map((check) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 14.0),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  check.equipmentId,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 16,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Temp: ${check.temperature}°F • Vib: ${check.vibration} • Age: ${check.installationAgeHours}h',
                                  style: const TextStyle(fontSize: 14),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Risk: ${(check.riskProbability ?? 0.0).toStringAsFixed(2)} • Status: ${check.healthStatus ?? 'UNKNOWN'}',
                                  style: const TextStyle(fontSize: 14),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  'Checked at: ${check.checkedAt.toLocal()}',
                                  style: const TextStyle(color: Colors.grey, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPreviewCardsRow() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: _buildSummaryCard(
            'Available Technicians',
            Icons.engineering,
            const Color(0xFFC8102E),
            availableTechnicians.isEmpty
                ? [const Text('No technicians currently on shift.')]
                : [
                    Text(
                      '${availableTechnicians.length} technicians on shift',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 12),
                    ...availableTechnicians.take(5).map(
                          (tech) => Padding(
                            padding: const EdgeInsets.only(bottom: 10.0),
                            child: Text(
                              '${tech.name} (${tech.id}) • ${tech.certs.join(', ')}',
                            ),
                          ),
                        ),
                    if (availableTechnicians.length > 5)
                      Text(
                        '+ ${availableTechnicians.length - 5} more technicians',
                        style: const TextStyle(color: Colors.grey),
                      ),
                  ],
            action: TextButton(
              onPressed: isLoading ? null : _navigateToTechniciansScreen,
              child: const Text('See all'),
            ),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildSummaryCard(
            'Inventory Status',
            Icons.inventory_2,
            const Color(0xFF111111),
            inventory.isEmpty
                ? [const Text('No inventory data available.')]
                : [
                    ...inventory.take(5).map(
                          (item) => Padding(
                            padding: const EdgeInsets.only(bottom: 10.0),
                            child: Text(
                              '${item.partNumber}: ${item.quantityAvailable} available ${item.inStock ? '(In stock)' : '(Out of stock)'}',
                            ),
                          ),
                        ),
                    if (inventory.length > 5)
                      Text(
                        '+ ${inventory.length - 5} more inventory items',
                        style: const TextStyle(color: Colors.grey),
                      ),
                  ],
            action: TextButton(
              onPressed: isLoading ? null : _navigateToInventoryStatusScreen,
              child: const Text('See all'),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildHealthRiskBarChart() {
    final checks = recentHealthChecks.take(5).toList();

    if (checks.isEmpty) {
      return const SizedBox.shrink();
    }

    final barGroups = checks.asMap().entries.map(
      (entry) {
        final index = entry.key;
        final check = entry.value;
        final riskPercent = (check.riskProbability ?? 0.0) * 100.0;

        return BarChartGroupData(
          x: index,
          barRods: [
            BarChartRodData(
              toY: riskPercent,
              width: 18,
              borderRadius: BorderRadius.circular(8),
              color: riskPercent >= 75 ? const Color(0xFFC8102E) : const Color(0xFF111111),
            ),
          ],
          showingTooltipIndicators: [0],
        );
      },
    ).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Risk by Equipment (latest)',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        SizedBox(
          height: 220,
          child: BarChart(
            BarChartData(
              barTouchData: BarTouchData(
                enabled: true,
                touchTooltipData: BarTouchTooltipData(
                  getTooltipColor: (group) => Colors.black87,
                  getTooltipItem: (group, groupIndex, rod, rodIndex) {
                    final equipment = checks[group.x.toInt()].equipmentId;
                    return BarTooltipItem(
                      '$equipment\n',
                      const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                      children: [
                        TextSpan(
                          text: 'Risk: ${rod.toY.toStringAsFixed(0)}%',
                          style: const TextStyle(color: Colors.white70),
                        ),
                      ],
                    );
                  },
                ),
              ),
              titlesData: FlTitlesData(
                leftTitles: AxisTitles(
                  sideTitles: SideTitles(showTitles: true, reservedSize: 38),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(
                    showTitles: true,
                    reservedSize: 42,
                    getTitlesWidget: (value, meta) {
                      final index = value.toInt();
                      if (index < 0 || index >= checks.length) {
                        return const SizedBox.shrink();
                      }
                      final label = checks[index].equipmentId;
                      return SideTitleWidget(
                        meta: meta,
                        child: Text(label, style: const TextStyle(fontSize: 10)),
                      );
                    },
                  ),
                ),
              ),
              gridData: FlGridData(show: true, drawHorizontalLine: true),
              borderData: FlBorderData(show: false),
              barGroups: barGroups,
              maxY: 100,
            ),
          ),
        ),
      ],
    );
  }


  Widget _buildNavigationCards() {
    return Column(
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: _buildCardLink(
                title: 'Recent Work Orders',
                icon: Icons.assignment_turned_in,
                iconColor: const Color(0xFF111111),
                count: workOrderCount,
                countColor: const Color(0xFF111111),
                subtitle:
                    'View the latest dispatched work orders and the current repair status.',
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
                iconColor: const Color(0xFFC8102E),
                count: alertCount,
                countColor: const Color(0xFFC8102E),
                subtitle: 'Inspect the latest alert events received by the system.',
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
        ),
        const SizedBox(height: 16),
        _buildCardLink(
          title: 'Audit Logs',
          icon: Icons.list_alt,
          iconColor: const Color(0xFF6B7280),
          count: 50,
          countColor: const Color(0xFF6B7280),
          subtitle: 'Review recent audit events and the payloads behind them.',
          onTap: () {
            _navigateToAuditLogsScreen();
          },
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
                    backgroundColor:
                        countColor.withOpacity(0.12),
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
        backgroundColor: const Color(0xFF111111),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh counts',
            onPressed: isLoading ? null : _loadDashboardCounts,
          ),
        ],
      ),
      backgroundColor: const Color(0xFFF7F7F7),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadDashboardCounts,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildExecutiveSummaryCard(),
                const SizedBox(height: 20),
                _buildKpiCards(),
                const SizedBox(height: 20),
                // _buildProcessFlow(), // preserved for later use
                // const SizedBox(height: 24),
                _buildQuickActions(),
                const SizedBox(height: 24),
                _buildHealthChecksCard(),
                const SizedBox(height: 24),
                _buildPreviewCardsRow(),
                const SizedBox(height: 24),
                _buildSummaryCard(
                  'Performance Metrics',
                  Icons.speed,
                  const Color(0xFFC8102E),
                  [
                    Text('Incidents: $workOrderCount dispatched, $alertCount alerts'),
                    const SizedBox(height: 8),
                    Text('Open repair tasks: $openWorkOrders'),
                    Text('Active equipment issues: $incidentCount'),
                    Text('Estimated downtime: ${downtimeMinutes.toStringAsFixed(1)} min'),
                    Text('Mean repair time: ${meanRepairTimeMinutes.toStringAsFixed(1)} min'),
                    Text('Uptime estimate: ${uptimePercentage.toStringAsFixed(1)}%'),
                  ],
                ),
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
