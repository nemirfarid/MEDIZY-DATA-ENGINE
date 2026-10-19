import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sante_dz_medizy/main.dart';

void main() {
  testWidgets('Medizy splash screen visual and branding test', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: MedizySplashScreen(statusMessage: 'Initialisation du registre sanitaire national...'),
      ),
    );

    // Vérifie le logo circulaire avec coeur bien-être et le nom Medizy
    expect(find.byIcon(Icons.favorite_rounded), findsOneWidget);
    // Vérifie l'absence absolue de croix médicale (+)
    expect(find.byIcon(Icons.local_hospital), findsNothing);
    expect(find.byIcon(Icons.add), findsNothing);
    // Vérifie la typographie et les textes officiels Medizy
    expect(find.text('Medizy'), findsOneWidget);
    expect(find.text('Votre santé au quotidien'), findsOneWidget);
    expect(find.text('Initialisation du registre sanitaire national...'), findsOneWidget);
  });

  testWidgets('Medizy app startup smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const SanteDzMedizyApp());
    await tester.pump();

    // L'application s'initialise et affiche l'interface Medizy
    expect(find.text('Medizy'), findsOneWidget);
    expect(find.text('Carte Sanitaire Hors-Ligne (58 Wilayas)'), findsOneWidget);
  });
}
