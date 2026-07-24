import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

/// WebSocket helper service that maintains a connection to the backend
/// and exposes a stream of received JSON messages as Dart Maps.
///
/// Also implements automatic reconnection with simple exponential backoff
/// and a polling fallback (provided as a callback) while disconnected.
class WsService {
  final String url;
  final Future<void> Function() pollCallback;

  WebSocketChannel? _channel;
  final StreamController<Map<String, dynamic>> _controller = StreamController.broadcast();
  StreamSubscription? _wsSub;
  Timer? _reconnectTimer;
  Timer? _pollTimer;

  int _reconnectAttempt = 0;

  WsService({required this.url, required this.pollCallback});

  Stream<Map<String, dynamic>> get stream => _controller.stream;

  void connect() {
    _stopPoll();

    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _wsSub = _channel!.stream.listen(
        (message) {
          try {
            final decoded = jsonDecode(message as String) as Map<String, dynamic>;
            _controller.add(decoded);
          } catch (_) {}
        },
        onError: (err) {
          _scheduleReconnect();
        },
        onDone: () {
          _scheduleReconnect();
        },
        cancelOnError: true,
      );
      _reconnectAttempt = 0;
    } catch (e) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    _wsSub?.cancel();
    _channel = null;
    _reconnectAttempt += 1;
    final backoffSeconds = (_reconnectAttempt < 6) ? (1 << (_reconnectAttempt - 1)) : 32;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(seconds: backoffSeconds), () {
      connect();
    });

    // Start polling fallback while disconnected
    _startPoll();
  }

  void _startPoll() {
    _pollTimer?.cancel();
    // Poll every 10 seconds while disconnected
    _pollTimer = Timer.periodic(const Duration(seconds: 10), (_) async {
      try {
        await pollCallback();
      } catch (_) {}
    });
  }

  void _stopPoll() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  void dispose() {
    _reconnectTimer?.cancel();
    _wsSub?.cancel();
    _channel?.sink.close();
    _controller.close();
    _stopPoll();
  }
}
