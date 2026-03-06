import 'package:credit_risk_mobile/core/api_client.dart';
import 'package:credit_risk_mobile/features/auth/data/auth_api.dart';
import 'package:flutter/material.dart';

class DashboardPage extends StatelessWidget {
  const DashboardPage({
    super.key,
    required this.apiClient,
    this.token,
  });

  final ApiClient apiClient;
  final AuthToken? token;

  @override
  Widget build(BuildContext context) {
    final name = token?.fullName?.isNotEmpty == true
        ? token!.fullName
        : token?.email ?? 'User';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Xin chào, $name',
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Vai trò: ${token?.role ?? 'unknown'}',
            ),
            const SizedBox(height: 24),
            const Text(
              'Đây là dashboard mobile tối giản.\n'
              'Bạn có thể mở rộng thêm các màn hình:\n'
              '- Danh sách khách hàng\n'
              '- Phân tích rủi ro\n'
              '- Portfolio\n'
              '- AI Chat',
            ),
          ],
        ),
      ),
    );
  }
}

