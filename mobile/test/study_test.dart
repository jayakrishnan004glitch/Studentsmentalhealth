import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:mh_companion/api/me_api.dart';
import 'package:mh_companion/api/study_api.dart';
import 'package:mh_companion/core/providers.dart';
import 'package:mh_companion/features/study/study_screen.dart';
import 'package:mh_companion/features/study/study_setup_screen.dart';
import 'package:mh_companion/features/study/subject_screen.dart';

class FakeStudyApi implements StudyApi {
  bool incomplete = false;
  final requestedSemesters = <int?>[];

  @override
  Future<StudyCatalog> catalog() async => StudyCatalog(
    schemes: const [CodeName('2019', '2019 scheme')],
    branches: const [CodeName('CSE', 'Computer Science and Engineering')],
    semesters: const [1, 2, 3, 4, 5, 6, 7, 8],
  );

  @override
  Future<SubjectList> subjects({int? semester}) async {
    requestedSemesters.add(semester);
    if (incomplete) throw StudyProfileIncomplete();
    final sem = semester ?? 3;
    return SubjectList(
      scheme: '2019',
      branch: 'CSE',
      semester: sem,
      subjects: sem == 3
          ? [
              Subject(
                id: 1,
                scheme: '2019',
                code: 'CST201',
                name: 'Data Structures',
                linkCount: 2,
              ),
            ]
          : [],
    );
  }

  @override
  Future<SubjectDetail> subject(int id) async => SubjectDetail(
    id: id,
    scheme: '2019',
    code: 'CST201',
    name: 'Data Structures',
    links: [
      StudyLink(
        id: 10,
        kind: 'syllabus',
        title: 'Official syllabus',
        url: 'https://ktu.example/syllabus',
        sourceName: 'KTU',
      ),
      StudyLink(
        id: 11,
        module: 1,
        kind: 'notes',
        title: 'Arrays notes',
        url: 'https://notes.example/m1',
      ),
    ],
  );
}

class FakeMeApi implements MeApi {
  Map<String, Object?>? sent;

  Me _me(Map<String, Object?> p) => Me(
    profile: Profile(
      id: 'u1',
      role: 'student',
      pseudonym: 'ABCD1234',
      ktuScheme: p['ktu_scheme'] as String?,
      branch: p['branch'] as String?,
      semester: p['semester'] as int?,
    ),
    consents: const {'terms': true},
    currentPolicyVersion: 'v1',
    needsConsent: false,
  );

  @override
  Future<Me> getMe() async => _me(sent ?? {});

  @override
  Future<Me> giveConsents(String policyVersion, Map<String, bool> items) =>
      throw UnimplementedError();

  @override
  Future<Me> updateProfile(Map<String, Object?> changes) async {
    sent = changes;
    return _me(changes);
  }
}

Future<void> pump(
  WidgetTester tester,
  Widget child, {
  FakeStudyApi? study,
  FakeMeApi? me,
  List<Uri>? opened,
}) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  return tester.pumpWidget(
    ProviderScope(
      overrides: [
        studyApiProvider.overrideWithValue(study ?? FakeStudyApi()),
        meApiProvider.overrideWithValue(me ?? FakeMeApi()),
        linkOpenerProvider.overrideWithValue((uri) async {
          opened?.add(uri);
          return true;
        }),
      ],
      child: MaterialApp(home: child),
    ),
  );
}

void main() {
  test('SubjectList and StudyLink parse API JSON', () {
    final list = SubjectList.fromJson({
      'scheme': '2019',
      'branch': 'CSE',
      'semester': 3,
      'subjects': [
        {
          'id': 1,
          'scheme': '2019',
          'code': 'CST201',
          'name': 'Data Structures',
          'link_count': 4,
        },
      ],
    });
    expect(list.subjects.single.linkCount, 4);
    final link = StudyLink.fromJson({
      'id': 1,
      'module': null,
      'kind': 'video',
      'title': 'Lecture',
      'url': 'https://example.org/v',
      'source_name': null,
    });
    expect(link.module, isNull);
  });

  testWidgets('Study screen asks for course setup when profile is incomplete', (
    tester,
  ) async {
    await pump(
      tester,
      const StudyScreen(),
      study: FakeStudyApi()..incomplete = true,
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('setup-course')), findsOneWidget);
  });

  testWidgets('Study screen lists subjects and browses semesters', (
    tester,
  ) async {
    final api = FakeStudyApi();
    await pump(tester, const StudyScreen(), study: api);
    await tester.pumpAndSettle();
    expect(find.text('Data Structures'), findsOneWidget);
    expect(find.text('CST201 · 2 links'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('sem-4')));
    await tester.pumpAndSettle();
    expect(api.requestedSemesters.last, 4);
    expect(find.textContaining('No subjects added'), findsOneWidget);
  });

  testWidgets('Subject screen groups links and opens them externally', (
    tester,
  ) async {
    final opened = <Uri>[];
    await pump(tester, const SubjectScreen(subjectId: 1), opened: opened);
    await tester.pumpAndSettle();
    expect(find.text('Whole subject'), findsOneWidget);
    expect(find.text('Module 1'), findsOneWidget);
    expect(find.text('Syllabus · ktu.example · KTU'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('link-11')));
    await tester.pump();
    expect(opened, [Uri.parse('https://notes.example/m1')]);
  });

  testWidgets('Course setup saves scheme, branch and semester', (tester) async {
    final me = FakeMeApi();
    var saved = false;
    await pump(tester, StudySetupScreen(onSaved: () => saved = true), me: me);
    await tester.pumpAndSettle();

    final save = find.byKey(const ValueKey('save-course'));
    expect(tester.widget<FilledButton>(save).onPressed, isNull);

    for (final (key, option) in [
      ('scheme', '2019 scheme'),
      ('branch', 'Computer Science and Engineering (CSE)'),
      ('semester', 'S5'),
    ]) {
      await tester.tap(find.byKey(ValueKey(key)));
      await tester.pumpAndSettle();
      await tester.tap(find.text(option).last);
      await tester.pumpAndSettle();
    }
    await tester.tap(save);
    await tester.pumpAndSettle();

    expect(saved, isTrue);
    expect(me.sent, {'ktu_scheme': '2019', 'branch': 'CSE', 'semester': 5});
  });
}
