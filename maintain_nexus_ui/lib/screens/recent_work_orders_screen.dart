// Recent work orders screen for MaintainNexus.
//
// Lists all work orders retrieved from the backend and includes a refresh action.
import 'package:flutter/material.dart';

import '../models/work_order.dart';
import '../services/api_service.dart';

/// Displays all recent work orders fetched from the backend.
///
/// Includes a refresh action so users can re-query the latest persisted
/// orders after creating or dispatching new jobs.
class RecentWorkOrdersScreen extends StatefulWidget {
  final ApiService apiService;

  const RecentWorkOrdersScreen({super.key, required this.apiService});

  @override
  State<RecentWorkOrdersScreen> createState() => _RecentWorkOrdersScreenState();
}

class _RecentWorkOrdersScreenState extends State<RecentWorkOrdersScreen> {
  bool isLoading = false;
  List<WorkOrder> _orders = [];
  String _statusMessage = 'Loading work orders...';

  @override
  void initState() {
    super.initState();
    _loadWorkOrders();
  }

  /// Fetch recent work orders from the backend and refresh the screen data.
  Future<void> _loadWorkOrders() async {
    setState(() {
      isLoading = true;
      _statusMessage = 'Loading work orders...';
    });

    try {
      final orders = await widget.apiService.fetchWorkOrders();
      setState(() {
        _orders = orders;
        _statusMessage = 'Loaded ${orders.length} work orders.';
      });
    } catch (e) {
      setState(() {
        _statusMessage = 'Failed to load work orders: $e';
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Widget _buildStatusChip(String status) {
    final statusLower = status.toLowerCase();
    Color background;
    Color textColor;

    if (statusLower == 'dispatched') {
      background = const Color(0xFFD1E8FF);
      textColor = const Color(0xFF0B79D0);
    } else if (statusLower == 'processing') {
      background = const Color(0xFFFFF2CC);
      textColor = const Color(0xFFB7791F);
    } else if (statusLower == 'executed') {
      background = const Color(0xFFD1F7E4);
      textColor = const Color(0xFF047C5F);
    } else {
      background = const Color(0xFFE2E8F0);
      textColor = const Color(0xFF334155);
    }

    return Chip(
      backgroundColor: background,
      label: Text(
        status,
        style: TextStyle(color: textColor, fontWeight: FontWeight.bold),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Recent work orders view: refresh button and paginated order list.
    return Scaffold(
      appBar: AppBar(
        title: const Text('Recent Work Orders'),
        backgroundColor: const Color(0xFF0F172A),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: isLoading ? null : _loadWorkOrders,
            tooltip: 'Refresh work orders',
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
              child: _orders.isEmpty
                  ? Center(
                      child: isLoading
                          ? const CircularProgressIndicator()
                          : const Text('No work orders found.'),
                    )
                  : ListView.separated(
                      itemCount: _orders.length,
                      separatorBuilder: (context, index) =>
                          const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final order = _orders[index];
                        return Card(
                          elevation: 2,
                          child: ListTile(
                            title: Text(order.id),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Equipment: ${order.equipmentId}'),
                                Text('Technician: ${order.technicianId}'),
                                Text('Part: ${order.partNumber}'),
                                const SizedBox(height: 8),
                                Text(
                                  'Elapsed: ${order.elapsedSeconds}s',
                                  style: const TextStyle(fontSize: 13),
                                ),
                              ],
                            ),
                            trailing: _buildStatusChip(order.status),
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
