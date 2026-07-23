// API client service for MaintainNexus Flutter app.
//
// Encapsulates REST calls for alerts, work orders, and technician lookups.
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/alert.dart';
import '../models/dashboard_summary.dart';
import '../models/work_order.dart';

/// Client service for MaintainNexus REST API calls.
class ApiService {
  static const String baseUrl = apiBaseUrl;

  /// Fetches available technicians for a given certification requirement.
  ///
  /// This method calls the HR technicians endpoint and returns the parsed
  /// `available_technicians` list from the JSON response.
  Future<List<dynamic>> fetchAvailableTechnicians(String requiredCert) async {
    final response = await http.get(
      Uri.parse(
        '$baseUrl/hr/technicians/available?required_cert=$requiredCert',
      ),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['available_technicians'] as List<dynamic>;
    }

    throw Exception('Failed to load technicians: ${response.statusCode}');
  }

  /// Dispatches a new work order to the backend API.
  ///
  /// Sends the work order payload as JSON and returns the created record
  /// parsed from the backend response.
  Future<WorkOrder> dispatchWorkOrder(WorkOrder workOrder) async {
    final response = await http.post(
      Uri.parse('$baseUrl/maintenance/work-orders'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(workOrder.toJson()),
    );

    if (response.statusCode == 201) {
      return WorkOrder.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    }

    throw Exception('Failed to dispatch work order: ${response.statusCode}');
  }

  /// Sends a maintenance alert payload to the backend alert ingestion endpoint.
  ///
  /// Returns the queued task metadata for the enqueued alert. This endpoint is
  /// expected to return HTTP 202 when the alert is accepted for asynchronous
  /// processing.
  Future<Map<String, dynamic>> sendAlert(Map<String, dynamic> alert) async {
    final response = await http.post(
      Uri.parse('$baseUrl/alerts/maintenance'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(alert),
    );

    if (response.statusCode == 202) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception('Failed to send alert: ${response.statusCode}');
  }

  /// Fetches the list of recent work orders from the backend.
  ///
  /// Parses the JSON array response into a list of [WorkOrder] model objects.
  Future<List<WorkOrder>> fetchWorkOrders() async {
    final response = await http.get(
      Uri.parse('$baseUrl/maintenance/work-orders'),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List<dynamic>;
      return data
          .map((item) => WorkOrder.fromJson(item as Map<String, dynamic>))
          .toList();
    }

    throw Exception('Failed to load work orders: ${response.statusCode}');
  }

  /// Fetches the list of recent alerts from the backend.
  ///
  /// Parses the JSON array response into a list of [AlertRecord] objects for
  /// display in the UI.
  Future<List<AlertRecord>> fetchRecentAlerts() async {
    final response = await http.get(Uri.parse('$baseUrl/alerts/recent'));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List<dynamic>;
      final uniqueAlerts = <String, AlertRecord>{};
      for (final item in data) {
        final alert = AlertRecord.fromJson(item as Map<String, dynamic>);
        final dedupeKey =
            alert.taskId ??
            '${alert.equipmentId}:${alert.partNumber}:${alert.failureCode}:${alert.receivedAt}';
        uniqueAlerts.putIfAbsent(dedupeKey, () => alert);
      }
      return uniqueAlerts.values.toList();
    }

    throw Exception('Failed to load alerts: ${response.statusCode}');
  }

  /// Fetches a single dashboard summary from the backend.
  ///
  /// The summary contains counts, available technicians, and inventory
  /// information that the dashboard displays in one request.
  Future<DashboardSummary> fetchDashboardSummary() async {
    final response = await http.get(Uri.parse('$baseUrl/dashboard/summary'));

    if (response.statusCode == 200) {
      return DashboardSummary.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    }

    throw Exception('Failed to load dashboard summary: ${response.statusCode}');
  }
}
