import 'package:flutter_test/flutter_test.dart';
import 'package:medizy_mobile/main.dart';

void main() {
  testWidgets('MEDIZY home renders category and privacy message', (tester) async {
    await tester.pumpWidget(const MedizyApp());
    expect(find.text('MEDIZY'), findsOneWidget);
    expect(find.text('Explorer par catégorie'), findsOneWidget);
    expect(find.text('Hôpitaux'), findsOneWidget);
    expect(find.text('Mode privé : aucune donnée médicale personnelle n’est demandée. L’annuaire local reste à importer.'), findsOneWidget);
  });

  testWidgets('navigation opens map tab', (tester) async {
    await tester.pumpWidget(const MedizyApp());
    await tester.tap(find.text('Carte').last);
    await tester.pumpAndSettle();
    expect(find.text('Rechercher une structure…'), findsOneWidget);
  });
}
