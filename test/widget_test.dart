import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sante_dz_medizy/main.dart';

void main() {
  testWidgets('Santé DZ / Medizy app startup widget smoke test', (WidgetTester tester) async {
    // Initialise l'application Santé DZ Medizy
    await tester.pumpWidget(const SanteDzMedizyApp());

    // Vérifie que le titre ou l'icône de l'hôpital est affiché
    expect(find.byIcon(Icons.local_hospital), findsOneWidget);
    expect(find.text('SANTÉ DZ / MEDIZY'), findsOneWidget);
  });
}
