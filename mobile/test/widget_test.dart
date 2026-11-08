import 'dart:ui' show Size;

import 'package:flutter_test/flutter_test.dart';
import 'package:medizy_mobile/main.dart';

void main() {
  testWidgets('MEDIZY home renders brand and navigation without network', (tester) async {
    tester.view.physicalSize = const Size(1080, 1920);
    tester.view.devicePixelRatio = 1;
    await tester.pumpWidget(const MedizyApp());
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('MEDIZY'), findsAtLeastNWidgets(1));
    expect(find.text('Annuaire'), findsOneWidget);
    expect(find.text('Carte'), findsOneWidget);
    expect(find.text('Favoris'), findsOneWidget);
    expect(find.text('Assistant IA'), findsOneWidget);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  });
}
