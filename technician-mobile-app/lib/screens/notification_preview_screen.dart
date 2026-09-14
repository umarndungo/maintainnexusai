import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Mockup 8 — the lock-screen SMS fallback notification. Shown as a
/// standalone preview (from Settings) since a real lock-screen
/// notification can't be staged inside the app itself.
class NotificationPreviewScreen extends StatefulWidget {
  const NotificationPreviewScreen({super.key});

  @override
  State<NotificationPreviewScreen> createState() => _NotificationPreviewScreenState();
}

class _NotificationPreviewScreenState extends State<NotificationPreviewScreen> {
  late Timer _timer;
  DateTime _now = DateTime.now();

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) => setState(() => _now = DateTime.now()));
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF14171B),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
        title: const Text('SMS fallback preview', style: TextStyle(color: Colors.white)),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            children: [
              const SizedBox(height: 48),
              Text(
                DateFormat('h:mm').format(_now),
                style: const TextStyle(color: Colors.white, fontSize: 64, fontWeight: FontWeight.w300),
              ),
              const SizedBox(height: 8),
              Text(
                DateFormat('EEEE, MMMM d').format(_now),
                style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 15),
              ),
              const SizedBox(height: 32),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'MAINTAINNEXUS',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.55), fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.8),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'New work order · Pump P-14, Station B',
                      style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'High risk · approved by station engineer · tap to open',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.75), fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Delivered by SMS fallback — app was offline',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 12),
              ),
              const Spacer(),
              Padding(
                padding: const EdgeInsets.only(bottom: 24),
                child: Text(
                  'When the app itself can\'t reach the network, the dispatch notice\nstill arrives by SMS with a deep link, so a technician\'s first sign\nof a job never depends on data signal.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.45), fontSize: 12, height: 1.5),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
