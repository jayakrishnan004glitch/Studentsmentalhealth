import 'package:dio/dio.dart';

/// Hand-written for Step 1. Later replaced by a client generated from the
/// FastAPI OpenAPI schema (openapi-generator, dart-dio).

class Profile {
  Profile({
    required this.id,
    required this.role,
    required this.pseudonym,
    this.displayName,
    this.department,
    this.year,
    this.ktuScheme,
    this.branch,
    this.semester,
  });

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
    id: json['id'] as String,
    role: json['role'] as String,
    pseudonym: json['pseudonym'] as String,
    displayName: json['display_name'] as String?,
    department: json['department'] as String?,
    year: json['year'] as int?,
    ktuScheme: json['ktu_scheme'] as String?,
    branch: json['branch'] as String?,
    semester: json['semester'] as int?,
  );

  /// KTU study profile (decides which subjects are shown).
  final String? ktuScheme;
  final String? branch;
  final int? semester;

  bool get hasStudyProfile =>
      ktuScheme != null && branch != null && semester != null;

  final String id;
  final String role;
  final String pseudonym;
  final String? displayName;
  final String? department;
  final int? year;
}

class Me {
  Me({
    required this.profile,
    required this.consents,
    required this.currentPolicyVersion,
    required this.needsConsent,
  });

  factory Me.fromJson(Map<String, dynamic> json) => Me(
    profile: Profile.fromJson(json['profile'] as Map<String, dynamic>),
    consents: {
      for (final c in json['consents'] as List<dynamic>)
        (c as Map<String, dynamic>)['kind'] as String: c['granted'] as bool,
    },
    currentPolicyVersion: json['current_policy_version'] as String,
    needsConsent: json['needs_consent'] as bool,
  );

  final Profile profile;

  /// Current state per consent kind, e.g. {'terms': true, 'camera': false}.
  final Map<String, bool> consents;
  final String currentPolicyVersion;
  final bool needsConsent;
}

abstract interface class MeApi {
  Future<Me> getMe();
  Future<Me> giveConsents(String policyVersion, Map<String, bool> items);

  /// PATCH /me with only the given fields (snake_case keys).
  Future<Me> updateProfile(Map<String, Object?> changes);
}

class DioMeApi implements MeApi {
  DioMeApi(this._dio);
  final Dio _dio;

  @override
  Future<Me> getMe() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/me');
    return Me.fromJson(res.data!);
  }

  @override
  Future<Me> giveConsents(String policyVersion, Map<String, bool> items) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/me/consents',
      data: {
        'policy_version': policyVersion,
        'items': [
          for (final e in items.entries) {'kind': e.key, 'granted': e.value},
        ],
      },
    );
    return Me.fromJson(res.data!);
  }

  @override
  Future<Me> updateProfile(Map<String, Object?> changes) async {
    final res = await _dio.patch<Map<String, dynamic>>(
      '/api/v1/me',
      data: changes,
    );
    return Me.fromJson(res.data!);
  }
}

/// Dio instance that attaches the current Supabase access token.
Dio buildApiDio(String baseUrl, String? Function() accessToken) {
  final dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
    ),
  );
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        final token = accessToken();
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        handler.next(options);
      },
    ),
  );
  return dio;
}
