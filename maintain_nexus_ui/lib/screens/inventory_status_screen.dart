import 'package:flutter/material.dart';

import '../models/dashboard_summary.dart';

/// Screen that displays the current inventory status.
class InventoryStatusScreen extends StatelessWidget {
  final List<InventoryItem> inventory;

  const InventoryStatusScreen({super.key, required this.inventory});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Inventory Status'),
        backgroundColor: const Color(0xFF0F172A),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: inventory.isEmpty
            ? const Center(
                child: Text('No inventory data available.'),
              )
            : ListView.separated(
                itemCount: inventory.length,
                separatorBuilder: (context, index) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final item = inventory[index];
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
                            item.partNumber,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text('Quantity available: ${item.quantityAvailable}'),
                          const SizedBox(height: 6),
                          Text(item.inStock ? 'Status: In stock' : 'Status: Out of stock'),
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
