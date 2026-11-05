import 'package:flutter_test/flutter_test.dart';
import 'package:medizy_mobile/main.dart';

void main() {
  testWidgets('MEDIZY home renders brand and categories', (tester) async {
    await tester.pumpWidget(const MedizyApp());
    expect(find.text('MEDIZY'), findsOneWidget);
    expect(find.text('Explorer par catégorie'), findsOneWidget);
    expect(find.text('Hôpitaux'), findsOneWidget);
    expect(find.text('Pharmacies'), findsOneWidget);
    expect(find.text('Carte à proximité'), findsOneWidget);
  });

  testWidgets('navigation opens map tab', (tester) async {
    await tester.pumpWidget(const MedizyApp());
    await tester.tap(find.text('Carte').last);
    await tester.pump(const Duration(milliseconds: 250));
    expect(find.text('Rechercher une structure…'), findsOneWidget);
    expect(find.textContaining('Carte OpenStreetMap'), findsOneWidget);
  });
}
