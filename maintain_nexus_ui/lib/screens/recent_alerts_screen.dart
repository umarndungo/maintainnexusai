/// Recent alerts screen for MaintainNexus.
///
/// Shows the latest alerts fetched from the backend and supports manual refresh.
import 'package:flutter/material.dart';

import '../models/alert.dart';
import '../services/api_service.dart';

/// Displays the most recent maintenance alerts retrieved from the API.
///
/// The screen includes a refresh button to retrieve updated alert data
/// on demand without leaving the view.
class RecentAlertsScreen extends StatefulWidget {
  final ApiService apiService;

  const RecentAlertsScreen({super.key, required this.apiService});

  @override
  State<RecentAlertsScreen> createState() => _RecentAlertsScreenState();
}

class _RecentAlertsScreenState extends State<RecentAlertsScreen> {
  bool isLoading = false;
  List<AlertRecord> _alerts = [];
  String _statusMessage = 'Loading alerts...';

  @override
  void initState() {
    super.initState();
    _loadAlerts();
  }

  /// Fetch recent alerts from the API and update the local list state.
  Future<void> _loadAlerts() async {
    setState(() {
      isLoading = true;
      _statusMessage = 'Loading alerts...';
    });

    try {
      final alerts = await widget.apiService.fetchRecentAlerts();
      setState(() {
        _alerts = alerts;
        _statusMessage = 'Loaded ${alerts.length} alerts.';
      });
    } catch (e) {
      setState(() {
        _statusMessage = 'Failed to load alerts: $e';
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    // Recent alerts view: top-level refresh and alert list display.
    return Scaffold(
      appBar: AppBar(
        title: const Text('Recent Alerts'),
        backgroundColor: const Color(0xFF0F172A),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: isLoading ? null : _loadAlerts,
            tooltip: 'Refresh alerts',
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_statusMessage, style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 12),
            Expanded(
              child: _alerts.isEmpty
                  ? Center(
                      child: isLoading
                          ? const CircularProgressIndicator()
                          : const Text('No alerts found.'),
                    )
                  : ListView.separated(
                      itemCount: _alerts.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final alert = _alerts[index];
                        return Card(
                          elevation: 2,
                          child: ListTile(
                            title: Text(alert.equipmentId),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Part: ${alert.partNumber}'),
                                Text('Severity: ${alert.severity}'),
                                Text('Failure: ${alert.failureCode}'),
                                Text('Received: ${alert.receivedAt}'),
                              ],
                            ),
                            trailing: alert.taskId != null
                                ? Text(alert.taskId!)
                                : null,
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
