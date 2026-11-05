import 'dart:ui' show Size;

import 'package:flutter_test/flutter_test.dart';
import 'package:medizy_mobile/main.dart';

void main() {
  testWidgets('MEDIZY home renders brand and category grid', (tester) async {
    tester.view.physicalSize = const Size(1080, 1920);
    tester.view.devicePixelRatio = 1;
    await tester.pumpWidget(const MedizyApp());
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('MEDIZY'), findsOneWidget);
    expect(find.text('Annuaire'), findsOneWidget);
    expect(find.text('Carte'), findsOneWidget);
    expect(find.text('Favoris'), findsOneWidget);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  });

  testWidgets('navigation opens map tab', (tester) async {
    await tester.pumpWidget(const MedizyApp());
    await tester.tap(find.text('Carte').last);
    await tester.pump();
    expect(find.byType(FlutterMap), findsOneWidget);
  });
}
