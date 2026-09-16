import 'dart:convert';

import 'package:http/http.dart' as http;

/// Thin wrapper over the real MaintainNexus API — every method here maps
/// to one endpoint already built and tested on the backend
/// (api/auth.py, api/workorders.py, api/maintenance.py's /alerts/recent).
/// No mock data, no local database: this is the only place in the app
/// that talks to the network.
///
/// Base URL is a compile-time constant so it can be overridden per
/// target without touching code:
///   - Android emulator (default): the host machine's Docker backend is
///     reachable at 10.0.2.2, not localhost (the emulator's own loopback).
///   - iOS simulator / desktop / web: pass
///     `--dart-define=API_BASE_URL=http://localhost:8000`.
///   - A real device: pass the dev machine's LAN IP, e.g.
///     `--dart-define=API_BASE_URL=http://192.168.1.23:8000`.
class ApiException implements Exception {
  ApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'ApiException($statusCode): $message';
}

/// The `user` object POST /api/v1/auth/login returns alongside the token.
/// [technicianId] is null for non-technician roles (engineer, executive,
/// supervisor) — see api/auth.py's `_lookup_user`, which only sets
/// `technician_id` for technician logins.
class LoginResult {
  const LoginResult({required this.accessToken, required this.name, this.technicianId});

  final String accessToken;
  final String name;
  final String? technicianId;
}

class ApiClient {
  ApiClient({http.Client? httpClient, String? baseUrl})
      : _http = httpClient ?? http.Client(),
        baseUrl = baseUrl ?? const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');

  final http.Client _http;
  final String baseUrl;

  /// Set by [AppController] right after a successful [login] (or loaded
  /// from shared_preferences on app start) — every other call needs it.
  String? accessToken;

  Map<String, String> get _authHeaders => {
        'Content-Type': 'application/json',
        if (accessToken != null) 'Authorization': 'Bearer $accessToken',
      };

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  /// POST /api/v1/auth/login — no password, matching every demo login in
  /// this system (api/auth.py's USERS dict, keyed by ids like
  /// "tech-demo") as well as a raw roster id like "TECH-105" (see
  /// api/auth.py's `_lookup_user`). Returns the token plus the resolved
  /// user on success; throws [ApiException] (401 "Unknown user")
  /// otherwise.
  Future<LoginResult> login(String employeeId) async {
    final response = await _http.post(
      _uri('/api/v1/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'user_id': employeeId}),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _errorDetail(response.body));
    }
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    accessToken = body['access_token'] as String;
    final user = body['user'] as Map<String, dynamic>? ?? const {};
    return LoginResult(
      accessToken: accessToken!,
      name: user['name'] as String? ?? employeeId,
      technicianId: user['technician_id'] as String?,
    );
  }

  /// GET /api/v1/maintenance/work-orders — returns *every* work order in
  /// the system (there's no per-technician filter on the backend);
  /// AppController filters client-side.
  Future<List<Map<String, dynamic>>> getWorkOrders() async {
    final response = await _get('/api/v1/maintenance/work-orders');
    return (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
  }

  /// GET /api/v1/alerts/recent — best-effort risk enrichment; a work
  /// order's alert_task_id may not appear here if it's aged out of the
  /// recent window, which callers should treat as "no risk data", not
  /// an error.
  Future<List<Map<String, dynamic>>> getRecentAlerts() async {
    final response = await _get('/api/v1/alerts/recent');
    return (jsonDecode(response.body) as List).cast<Map<String, dynamic>>();
  }

  /// PATCH /api/v1/maintenance/work-orders/{id}/start — DISPATCHED ->
  /// IN_PROGRESS (the Part B endpoint added this session).
  Future<Map<String, dynamic>> startWorkOrder(String workOrderId) async {
    final response = await _patch('/api/v1/maintenance/work-orders/$workOrderId/start');
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// PATCH /api/v1/maintenance/work-orders/{id}/complete — IN_PROGRESS ->
  /// COMPLETED. photo_object_path is intentionally omitted: real photo
  /// capture/upload isn't wired up in this pass (see the app's plan
  /// notes) — the close-out screen's photo toggle stays UI-only.
  Future<Map<String, dynamic>> completeWorkOrder(
    String workOrderId, {
    String? notes,
    List<String> partsUsed = const [],
  }) async {
    final response = await _patch(
      '/api/v1/maintenance/work-orders/$workOrderId/complete',
      body: {
        'notes': ?notes,
        'parts_used': partsUsed,
      },
    );
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<http.Response> _get(String path) async {
    final response = await _http.get(_uri(path), headers: _authHeaders);
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _errorDetail(response.body));
    }
    return response;
  }

  Future<http.Response> _patch(String path, {Map<String, dynamic>? body}) async {
    final response = await _http.patch(
      _uri(path),
      headers: _authHeaders,
      body: body != null ? jsonEncode(body) : null,
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(response.statusCode, _errorDetail(response.body));
    }
    return response;
  }

  String _errorDetail(String responseBody) {
    try {
      final decoded = jsonDecode(responseBody);
      if (decoded is Map && decoded['detail'] != null) return decoded['detail'].toString();
    } catch (_) {
      // Not JSON, or no "detail" key — fall through to the raw body.
    }
    return responseBody;
  }
}
