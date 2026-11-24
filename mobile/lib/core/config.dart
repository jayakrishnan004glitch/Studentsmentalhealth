import 'package:flutter/foundation.dart';

/// Build-time configuration, passed with --dart-define (see mobile/README.md).
class AppConfig {
  static const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  static const supabasePublishableKey = String.fromEnvironment(
    'SUPABASE_PUBLISHABLE_KEY',
  );
  static const _apiBaseUrl = String.fromEnvironment('API_BASE_URL');

  /// FastAPI base URL. Defaults: the Android emulator reaches the host
  /// machine at 10.0.2.2; the web build uses localhost.
  static String get apiBaseUrl {
    if (_apiBaseUrl.isNotEmpty) return _apiBaseUrl;
    return kIsWeb ? 'http://localhost:8000' : 'http://10.0.2.2:8000';
  }

  static bool get isConfigured =>
      supabaseUrl.isNotEmpty && supabasePublishableKey.isNotEmpty;
}
