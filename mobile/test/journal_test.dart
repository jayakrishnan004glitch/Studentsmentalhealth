import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:mh_companion/api/journal_api.dart';
import 'package:mh_companion/core/providers.dart';
import 'package:mh_companion/features/journal/journal_screen.dart';
import 'package:mh_companion/features/journal/mood_log_screen.dart';

class FakeJournalApi implements JournalApi {
  NewMoodLog? sent;
  bool fail = false;
  JournalInsights insightsResult = _insights(entries: 0);

  @override
  Future<MoodLog> create(NewMoodLog entry) async {
    if (fail) throw Exception('network');
    sent = entry;
    return MoodLog(
      id: 1,
      moodScore: entry.moodScore,
      createdAt: DateTime.now(),
    );
  }

  @override
  Future<MoodLogPage> list({int limit = 20, int? beforeId}) async =>
      MoodLogPage([], null);

  @override
  Future<JournalInsights> insights({required int rangeDays}) async =>
      insightsResult;
}

JournalInsights _insights({required int entries}) => JournalInsights.fromJson({
  'range_days': 7,
  'days': [
    for (var i = 0; i < 7; i++)
      {
        'date': '2026-11-${(14 + i).toString().padLeft(2, '0')}',
        'entries': i == 6 ? entries : 0,
        'mood_avg': i == 6 && entries > 0 ? 4.0 : null,
        'sleep_avg': i == 6 && entries > 0 ? 7.5 : null,
      },
  ],
  'entries': entries,
  'mood_avg': entries > 0 ? 4.0 : null,
  'sleep_avg': entries > 0 ? 7.5 : null,
  'streak_days': entries > 0 ? 1 : 0,
  'top_tags': entries > 0
      ? [
          {'tag': 'exams', 'count': 1},
        ]
      : [],
});

Future<void> pump(WidgetTester tester, FakeJournalApi api, Widget child) {
  tester.view.physicalSize = const Size(1080, 2600);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  return tester.pumpWidget(
    ProviderScope(
      overrides: [journalApiProvider.overrideWithValue(api)],
      child: MaterialApp(home: child),
    ),
  );
}

FilledButton saveButton(WidgetTester tester) =>
    tester.widget<FilledButton>(find.byKey(const ValueKey('save-mood')));

void main() {
  test('NewMoodLog.toJson leaves out empty optional fields', () {
    expect(const NewMoodLog(moodScore: 3, note: '   ').toJson(), {
      'mood_score': 3,
      'tags': <String>[],
    });
    expect(
      const NewMoodLog(
        moodScore: 2,
        sleepHours: 6.5,
        energy: 4,
        tags: ['exams'],
        note: ' hi ',
      ).toJson(),
      {
        'mood_score': 2,
        'sleep_hours': 6.5,
        'energy': 4,
        'tags': ['exams'],
        'note': 'hi',
      },
    );
  });

  test('MoodLog.fromJson parses an API entry', () {
    final log = MoodLog.fromJson({
      'id': 7,
      'mood_score': 4,
      'sleep_hours': 7,
      'energy': null,
      'tags': ['family'],
      'note': null,
      'created_at': '2026-11-16T10:00:00Z',
    });
    expect(log.sleepHours, 7.0);
    expect(log.tags, ['family']);
    expect(log.createdAt.isUtc, isFalse);
  });

  testWidgets('Save is disabled until a mood is picked', (tester) async {
    await pump(tester, FakeJournalApi(), const MoodLogScreen());
    expect(saveButton(tester).onPressed, isNull);
    await tester.tap(find.byKey(const ValueKey('mood-2')));
    await tester.pump();
    expect(saveButton(tester).onPressed, isNotNull);
  });

  testWidgets('Saving sends mood, sleep, tags and note', (tester) async {
    final api = FakeJournalApi();
    var saved = false;
    await pump(
      tester,
      api,
      MoodLogScreen(initialMood: 4, onSaved: () => saved = true),
    );

    await tester.tap(find.byKey(const ValueKey('log-sleep')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('tag-exams')));
    await tester.enterText(find.byKey(const ValueKey('note')), 'Long day');
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('save-mood')));
    await tester.pumpAndSettle();

    expect(saved, isTrue);
    expect(api.sent!.moodScore, 4);
    expect(api.sent!.sleepHours, 7); // slider default
    expect(api.sent!.tags, ['exams']);
    expect(api.sent!.note, 'Long day');
    expect(api.sent!.energy, isNull);
  });

  testWidgets('Shows an error when saving fails', (tester) async {
    final api = FakeJournalApi()..fail = true;
    await pump(tester, api, const MoodLogScreen(initialMood: 3));
    await tester.tap(find.byKey(const ValueKey('save-mood')));
    await tester.pumpAndSettle();
    expect(find.text('Could not save. Please try again.'), findsOneWidget);
  });

  testWidgets('Journal shows an empty state', (tester) async {
    await pump(tester, FakeJournalApi(), const JournalScreen());
    await tester.pumpAndSettle();
    expect(
      find.textContaining('No check-ins in this period yet'),
      findsOneWidget,
    );
  });

  testWidgets('Journal shows insights', (tester) async {
    final api = FakeJournalApi()..insightsResult = _insights(entries: 1);
    await pump(tester, api, const JournalScreen());
    await tester.pumpAndSettle();
    expect(find.text('7.5 h'), findsOneWidget);
    expect(find.text('1 d'), findsOneWidget);
    expect(find.byKey(const ValueKey('mood-bars')), findsOneWidget);
    expect(find.text('Exams · 1'), findsOneWidget);
  });
}
