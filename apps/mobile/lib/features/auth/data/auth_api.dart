import 'package:credit_risk_mobile/core/api_client.dart';

class AuthToken {
  AuthToken({
    required this.accessToken,
    required this.userId,
    required this.email,
    required this.fullName,
    required this.role,
  });

  final String accessToken;
  final int userId;
  final String email;
  final String fullName;
  final String role;
}

class AuthApi {
  AuthApi(this._client);

  final ApiClient _client;

  Future<AuthToken> login({
    required String usernameOrEmail,
    required String password,
  }) async {
    final json = await _client.postJson(
      '/auth/login',
      <String, dynamic>{
        'username_or_email': usernameOrEmail,
        'password': password,
      },
    );

    final accessToken = json['access_token'] as String?;
    if (accessToken == null || accessToken.isEmpty) {
      throw ApiException(500, 'Invalid login response');
    }

    _client.setAccessToken(accessToken);

    return AuthToken(
      accessToken: accessToken,
      userId: (json['user_id'] as num?)?.toInt() ?? 0,
      email: (json['email'] as String?) ?? '',
      fullName: (json['full_name'] as String?) ?? '',
      role: (json['role'] as String?) ?? '',
    );
  }
}

