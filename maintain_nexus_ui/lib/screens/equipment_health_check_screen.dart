import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/dashboard_summary.dart';
import '../services/api_service.dart';

/// Equipment health screen showing the latest telemetry checks.
///
/// Includes a pull-to-refresh gesture and a refresh toolbar icon.
class EquipmentHealthCheckScreen extends StatefulWidget {
  final ApiService apiService;

  const EquipmentHealthCheckScreen({super.key, required this.apiService});

  @override
  State<EquipmentHealthCheckScreen> createState() => _EquipmentHealthCheckScreenState();
}

class _EquipmentHealthCheckScreenState extends State<EquipmentHealthCheckScreen> {
  bool isLoading = false;
  String statusMessage = 'Loading equipment health data...';
  List<HealthCheck> healthChecks = [];

  @override
  void initState() {
    super.initState();
    _loadHealthChecks();
  }

  Future<void> _loadHealthChecks() async {
    setState(() {
      isLoading = true;
      statusMessage = 'Refreshing equipment health...';
    });

    try {
      final checks = await widget.apiService.fetchRecentHealthChecks();
      setState(() {
        healthChecks = checks;
        statusMessage = 'Loaded ${checks.length} recent health checks.';
      });
    } catch (e) {
      setState(() {
        statusMessage = 'Failed to refresh health data: $e';
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Widget _buildHealthSummary() {
    if (healthChecks.isEmpty) {
      return const SizedBox.shrink();
    }

    final averageTemp = healthChecks
            .map((check) => check.temperature)
            .reduce((a, b) => a + b) /
        healthChecks.length;
    final highestRisk = healthChecks
        .map((check) => check.riskProbability ?? 0.0)
        .reduce((a, b) => a > b ? a : b);
    final worstAsset = healthChecks
        .reduce((a, b) => (a.riskProbability ?? 0.0) > (b.riskProbability ?? 0.0) ? a : b);

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Health Summary',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Checks', style: TextStyle(color: Colors.grey)),
                      const SizedBox(height: 4),
                      Text('${healthChecks.length}',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Avg Temp', style: TextStyle(color: Colors.grey)),
                      const SizedBox(height: 4),
                      Text('${averageTemp.toStringAsFixed(1)}°F',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Worst Risk', style: TextStyle(color: Colors.grey)),
                      const SizedBox(height: 4),
                      Text('${(highestRisk * 100).toStringAsFixed(0)}%',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: highestRisk >= 0.75 ? const Color(0xFFEF4444) : const Color(0xFF2563EB),
                          )),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text('Highest risk asset: ${worstAsset.equipmentId}'),
          ],
        ),
      ),
    );
  }


  Widget _buildHealthCard(HealthCheck check) {
    final riskPercent = ((check.riskProbability ?? 0.0) * 100).toStringAsFixed(0);
    final riskColor = (check.riskProbability ?? 0.0) >= 0.75
        ? const Color(0xFFEF4444)
        : const Color(0xFF2563EB);

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    check.equipmentId,
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
                Chip(
                  backgroundColor: riskColor.withAlpha(40),
                  label: Text(
                    '$riskPercent%',
                    style: TextStyle(color: riskColor, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text('Temperature: ${check.temperature.toStringAsFixed(1)}°F'),
            Text('Vibration: ${check.vibration.toStringAsFixed(2)}'),
            Text('Age: ${check.installationAgeHours}h'),
            const SizedBox(height: 8),
            Text('Health status: ${check.healthStatus ?? 'Unknown'}'),
            const SizedBox(height: 8),
            Text(
              'Checked at: ${check.checkedAt.toLocal()}',
              style: const TextStyle(color: Colors.grey, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Equipment Health Check'),
        backgroundColor: const Color(0xFF0F172A),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh health checks',
            onPressed: isLoading ? null : _loadHealthChecks,
          ),
        ],
      ),
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadHealthChecks,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16.0),
            children: [
              Text(
                statusMessage,
                style: const TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 16),
              if (isLoading && healthChecks.isEmpty)
                const Center(child: CircularProgressIndicator())
              else if (healthChecks.isEmpty)
                const Center(child: Text('No health checks available.'))
              else ...[
                _buildHealthSummary(),
                const SizedBox(height: 16),
                ...healthChecks.map(_buildHealthCard),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
