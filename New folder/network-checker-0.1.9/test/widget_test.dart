import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:rdnbenet/app.dart';

void main() {
  testWidgets('App loads correctly', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const RdnbenetApp());

    // Verify that the app loads with navigation
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('Domains'), findsOneWidget);
  });
}
