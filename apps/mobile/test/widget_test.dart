// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';

import 'package:credit_risk_mobile/main.dart';
import 'package:credit_risk_mobile/config/env.dart';
import 'package:credit_risk_mobile/core/api_client.dart';
import 'package:credit_risk_mobile/routes/app_router.dart';

void main() {
  testWidgets('App loads login screen', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    final apiClient = ApiClient(baseUrl: Env.apiBaseUrl);
    final router = AppRouter(apiClient);
    await tester.pumpWidget(CreditRiskApp(router: router));

    // Verify that the login screen is shown (by title text).
    expect(find.text('Credit Risk System'), findsOneWidget);
  });
}
