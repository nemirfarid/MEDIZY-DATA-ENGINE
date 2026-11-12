import 'package:flutter/material.dart';
import '../../../../core/models/crowd_report.dart';
import '../../../../core/models/health_professional.dart';

/// Dialogue ergonomique de signalement collaboratif d'anomalie
class ReportAnomalyDialog extends StatefulWidget {
  final HealthProfessional facility;
  final Future<void> Function(CrowdReport report) onSubmit;

  const ReportAnomalyDialog({
    super.key,
    required this.facility,
    required this.onSubmit,
  });

  static Future<void> show(
    BuildContext context, {
    required HealthProfessional facility,
    required Future<void> Function(CrowdReport report) onSubmit,
  }) {
    return showDialog<void>(
      context: context,
      builder: (ctx) => ReportAnomalyDialog(
        facility: facility,
        onSubmit: onSubmit,
      ),
    );
  }

  @override
  State<ReportAnomalyDialog> createState() => _ReportAnomalyDialogState();
}

class _ReportAnomalyDialogState extends State<ReportAnomalyDialog> {
  ReportType _selectedType = ReportType.modifiedHours;
  final _descriptionController = TextEditingController();
  final _phoneController = TextEditingController();
  final _addressController = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _descriptionController.dispose();
    _phoneController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _isSubmitting = true);

    final report = CrowdReport(
      facilityId: widget.facility.id,
      facilityName: widget.facility.nom,
      reportType: _selectedType,
      description: _descriptionController.text.trim().isNotEmpty ? _descriptionController.text.trim() : null,
      suggestedPhone: _phoneController.text.trim().isNotEmpty ? _phoneController.text.trim() : null,
      suggestedAddress: _addressController.text.trim().isNotEmpty ? _addressController.text.trim() : null,
      createdAt: DateTime.now().toUtc(),
      isSynced: false,
    );

    try {
      await widget.onSubmit(report);
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Signalement enregistré hors-ligne dans la file d\'attente.'),
            backgroundColor: Color(0xFF00695C),
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Signaler une anomalie',
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 2),
          Text(
            widget.facility.nom,
            style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Nature du problème :',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            DropdownButtonFormField<ReportType>(
              key: const Key('report_type_dropdown'),
              initialValue: _selectedType,
              isExpanded: true,
              decoration: InputDecoration(
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
              items: ReportType.values.map((type) {
                return DropdownMenuItem(
                  value: type,
                  child: Text(type.label, style: const TextStyle(fontSize: 13)),
                );
              }).toList(),
              onChanged: (val) {
                if (val != null) {
                  setState(() => _selectedType = val);
                }
              },
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('report_desc_field'),
              controller: _descriptionController,
              decoration: InputDecoration(
                labelText: 'Précisions complémentaires (facultatif)',
                hintText: 'Ex: Fermé le vendredi, ouvert jusqu\'à 19h...',
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 10),
            TextField(
              key: const Key('report_phone_field'),
              controller: _phoneController,
              decoration: InputDecoration(
                labelText: 'Nouveau numéro valide (facultatif)',
                prefixIcon: const Icon(Icons.phone, size: 18),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
              keyboardType: TextInputType.phone,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _isSubmitting ? null : () => Navigator.of(context).pop(),
          child: const Text('Annuler'),
        ),
        ElevatedButton(
          key: const Key('submit_report_button'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.teal.shade800,
            foregroundColor: Colors.white,
          ),
          onPressed: _isSubmitting ? null : _submit,
          child: _isSubmitting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                )
              : const Text('Enregistrer le signalement'),
        ),
      ],
    );
  }
}
