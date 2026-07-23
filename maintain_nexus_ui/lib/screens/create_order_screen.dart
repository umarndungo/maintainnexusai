// Manual work order creation screen for MaintainNexus.
//
// Allows users to enter equipment, technician, and part details and dispatch a new order.
import 'package:flutter/material.dart';

import '../models/work_order.dart';
import '../services/api_service.dart';

/// Form screen for manually creating and dispatching a work order.
///
/// Validates user input and then sends the work order payload to the API.
class CreateOrderScreen extends StatefulWidget {
  final ApiService apiService;

  const CreateOrderScreen({super.key, required this.apiService});

  @override
  State<CreateOrderScreen> createState() => _CreateOrderScreenState();
}

class _CreateOrderScreenState extends State<CreateOrderScreen> {
  final _formKey = GlobalKey<FormState>();
  final _equipmentController = TextEditingController();
  final _technicianController = TextEditingController();
  final _partController = TextEditingController();
  bool _isSubmitting = false;
  String _resultMessage = '';

  @override
  void dispose() {
    _equipmentController.dispose();
    _technicianController.dispose();
    _partController.dispose();
    super.dispose();
  }

  /// Submit a manual work order after validating the form.
  ///
  /// Sets a loading state while the API request is in flight and shows the
  /// result message once the request completes.
  Future<void> _submitOrder() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSubmitting = true;
      _resultMessage = 'Submitting work order...';
    });

    final workOrder = WorkOrder(
      id: '',
      equipmentId: _equipmentController.text.trim(),
      technicianId: _technicianController.text.trim(),
      partNumber: _partController.text.trim(),
      status: 'CREATED',
      createdAt: null,
      durationSeconds: 0,
    );

    try {
      final result = await widget.apiService.dispatchWorkOrder(workOrder);
      setState(() {
        _resultMessage = 'Created ${result.id} (${result.status})';
      });
    } catch (e) {
      setState(() {
        _resultMessage = 'Error: $e';
      });
    } finally {
      setState(() {
        _isSubmitting = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    // Work order creation form with validation and result feedback.
    return Scaffold(
      appBar: AppBar(
        title: const Text('Create Work Order'),
        backgroundColor: const Color(0xFF0F172A),
      ),
      backgroundColor: const Color(0xFFF8FAFC),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Equipment ID input field.
              TextFormField(
                controller: _equipmentController,
                decoration: const InputDecoration(
                  labelText: 'Equipment ID',
                  border: OutlineInputBorder(),
                ),
                validator: (value) => value == null || value.isEmpty
                    ? 'Enter equipment ID'
                    : null,
              ),
              const SizedBox(height: 16),
              // Technician ID input field.
              TextFormField(
                controller: _technicianController,
                decoration: const InputDecoration(
                  labelText: 'Technician ID',
                  border: OutlineInputBorder(),
                ),
                validator: (value) => value == null || value.isEmpty
                    ? 'Enter technician ID'
                    : null,
              ),
              const SizedBox(height: 16),
              // Part number input field.
              TextFormField(
                controller: _partController,
                decoration: const InputDecoration(
                  labelText: 'Part Number',
                  border: OutlineInputBorder(),
                ),
                validator: (value) =>
                    value == null || value.isEmpty ? 'Enter part number' : null,
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _isSubmitting ? null : _submitOrder,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0284C7),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: Text(
                  _isSubmitting ? 'Submitting...' : 'Dispatch Work Order',
                ),
              ),
              const SizedBox(height: 16),
              // Display the result of the submission after the request completes.
              Text(_resultMessage, style: const TextStyle(fontSize: 16)),
            ],
          ),
        ),
      ),
    );
  }
}
