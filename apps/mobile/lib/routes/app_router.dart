import 'package:credit_risk_mobile/core/api_client.dart';
import 'package:credit_risk_mobile/features/auth/data/auth_api.dart';
import 'package:credit_risk_mobile/features/auth/presentation/login_page.dart';
import 'package:credit_risk_mobile/features/dashboard/presentation/dashboard_page.dart';
import 'package:flutter/material.dart';

class AppRoutes {
  static const String login = '/login';
  static const String dashboard = '/dashboard';
}

class AppRouter {
  AppRouter(this.apiClient);

  final ApiClient apiClient;

  Route<dynamic> onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.dashboard:
        final token = settings.arguments as AuthToken?;
        return MaterialPageRoute(
          builder: (_) => DashboardPage(
            apiClient: apiClient,
            token: token,
          ),
        );
      case AppRoutes.login:
      default:
        return MaterialPageRoute(
          builder: (_) => LoginPage(
            authApi: AuthApi(apiClient),
          ),
        );
    }
  }
}

