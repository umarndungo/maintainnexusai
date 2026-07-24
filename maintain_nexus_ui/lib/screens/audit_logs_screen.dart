import 'package:flutter/material.dart';

import '../models/audit_log.dart';
import '../services/api_service.dart';

class AuditLogsScreen extends StatefulWidget {
  final ApiService apiService;

  const AuditLogsScreen({super.key, required this.apiService});

  @override
  State<AuditLogsScreen> createState() => _AuditLogsScreenState();
}

class _AuditLogsScreenState extends State<AuditLogsScreen> {
  bool isLoading = false;
  List<AuditLogEntry> _entries = [];
  String _statusMessage = 'Loading audit logs...';

  @override
  void initState() {
    super.initState();
    _loadLogs();
  }

  Future<void> _loadLogs() async {
    setState(() {
      isLoading = true;
      _statusMessage = 'Loading audit logs...';
    });

    try {
      final logs = await widget.apiService.fetchAuditLogs();
      setState(() {
        _entries = logs;
        _statusMessage = 'Loaded ${logs.length} audit events.';
      });
    } catch (e) {
      setState(() {
        _statusMessage = 'Failed to load audit logs: $e';
      });
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Audit Logs'),
        backgroundColor: const Color(0xFF111111),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: isLoading ? null : _loadLogs,
            tooltip: 'Refresh audit logs',
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_statusMessage, style: const TextStyle(fontSize: 16)),
            const SizedBox(height: 12),
            Expanded(
              child: _entries.isEmpty
                  ? Center(
                      child: isLoading
                          ? const CircularProgressIndicator()
                          : const Text('No audit logs found.'),
                    )
                  : ListView.separated(
                      itemCount: _entries.length,
                      separatorBuilder: (context, _) => const SizedBox(height: 12),
                      itemBuilder: (context, index) {
                        final entry = _entries[index];
                        return Card(
                          elevation: 2,
                          child: ExpansionTile(
                            title: Text(entry.eventName),
                            subtitle: Text(entry.timestamp),
                            children: [
                              Padding(
                                padding: const EdgeInsets.all(16),
                                child: SelectableText(entry.payload),
                              ),
                            ],
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
