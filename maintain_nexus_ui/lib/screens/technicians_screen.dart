import 'package:flutter/material.dart';

import '../models/dashboard_summary.dart';

/// Screen that displays the current list of available technicians.
class TechniciansScreen extends StatelessWidget {
  final List<Technician> technicians;

  const TechniciansScreen({super.key, required this.technicians});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Available Technicians'),
        backgroundColor: const Color(0xFF0F172A),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: technicians.isEmpty
            ? const Center(
                child: Text('No technicians currently on shift.'),
              )
            : ListView.separated(
                itemCount: technicians.length,
                separatorBuilder: (context, index) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final tech = technicians[index];
                  return Card(
                    elevation: 2,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            tech.name,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text('ID: ${tech.id}'),
                          const SizedBox(height: 6),
                          Text('Certifications: ${tech.certs.join(', ')}'),
                        ],
                      ),
                    ),
                  );
                },
              ),
      ),
    );
  }
}
