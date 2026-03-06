import 'package:credit_risk_mobile/config/env.dart';
import 'package:credit_risk_mobile/core/api_client.dart';
import 'package:credit_risk_mobile/routes/app_router.dart';
import 'package:flutter/material.dart';

void main() {
  final apiClient = ApiClient(baseUrl: Env.apiBaseUrl);
  final appRouter = AppRouter(apiClient);

  runApp(CreditRiskApp(router: appRouter));
}

class CreditRiskApp extends StatelessWidget {
  const CreditRiskApp({
    super.key,
    required this.router,
  });

  final AppRouter router;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Credit Risk Mobile',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      initialRoute: AppRoutes.login,
      onGenerateRoute: router.onGenerateRoute,
    );
  }
}

