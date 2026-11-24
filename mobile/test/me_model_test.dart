import 'package:flutter_test/flutter_test.dart';
import 'package:mh_companion/api/me_api.dart';

void main() {
  test('Me.fromJson parses the /api/v1/me response', () {
    final me = Me.fromJson({
      'profile': {
        'id': 'b6b1c3a4-0000-4000-8000-000000000001',
        'role': 'student',
        'display_name': null,
        'department': 'CSE',
        'year': 3,
        'pseudonym': 'A7F2C0DE',
        'created_at': '2026-11-16T10:00:00Z',
      },
      'consents': [
        {
          'kind': 'terms',
          'granted': true,
          'policy_version': 'v1',
          'updated_at': '2026-11-16T10:00:00Z',
        },
        {
          'kind': 'camera',
          'granted': false,
          'policy_version': 'v1',
          'updated_at': '2026-11-16T10:00:00Z',
        },
      ],
      'current_policy_version': 'v1',
      'needs_consent': false,
      'missing_consents': [],
    });
    expect(me.profile.department, 'CSE');
    expect(me.profile.displayName, isNull);
    expect(me.consents, {'terms': true, 'camera': false});
    expect(me.needsConsent, isFalse);
  });
}
