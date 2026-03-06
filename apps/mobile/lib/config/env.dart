class Env {
  /// Base URL cho backend, mặc định localhost khi dev.
  /// Ví dụ: http://localhost:8000/api/v1
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );
}

