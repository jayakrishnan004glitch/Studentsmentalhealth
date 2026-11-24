import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:mh_companion/api/journal_api.dart';
import 'package:mh_companion/api/questionnaire_api.dart';
import 'package:mh_companion/api/support.dart';
import 'package:mh_companion/core/providers.dart';
import 'package:mh_companion/features/journal/mood_log_screen.dart';
import 'package:mh_companion/features/questionnaires/questionnaire_flow_screen.dart';

const _urgent = Support(
  level: 'urgent',
  title: "You're not alone",
  message: 'Please reach out to someone you trust or a helpline below.',
);

class FakeQuestionnaireApi implements QuestionnaireApi {
  List<int>? sent;
  bool item9 = false;

  @override
  Future<QuestionnaireDefinition> definition(String instrument) async =>
      QuestionnaireDefinition(
        instrument: instrument,
        shortName: 'GAD-7',
        stem: 'Over the last 2 weeks…',
        options: const [
          'Not at all',
          'Several days',
          'More than half',
          'Nearly',
        ],
        items: const ['Q one', 'Q two', 'Q three'],
      );

  @override
  Future<QuestionnaireResult> submit(
    String instrument,
    List<int> answers,
  ) async {
    sent = answers;
    return QuestionnaireResult(
      id: 1,
      instrument: instrument,
      total: answers.fold(0, (a, b) => a + b),
      maxTotal: 9,
      severityLabel: item9 ? 'Minimal' : 'Mild',
      level: item9 ? 0 : 1,
      maxLevel: 3,
      subscales: const [],
      item9Flag: item9,
      support: item9 ? _urgent : null,
    );
  }

  @override
  Future<List<ResultHistoryItem>> history(String instrument) async => [];

  @override
  Future<List<QuestionnaireSummary>> list() async => [];
}

class FlaggingJournalApi implements JournalApi {
  @override
  Future<MoodLog> create(NewMoodLog entry) async => MoodLog(
    id: 1,
    moodScore: entry.moodScore,
    createdAt: DateTime.now(),
    note: entry.note,
    support: _urgent,
  );

  @override
  Future<MoodLogPage> list({int limit = 20, int? beforeId}) =>
      throw UnimplementedError();

  @override
  Future<JournalInsights> insights({required int rangeDays}) =>
      throw UnimplementedError();
}

Future<void> pump(
  WidgetTester tester,
  Widget child, {
  QuestionnaireApi? q,
  JournalApi? journal,
  List<Uri>? opened,
}) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  return tester.pumpWidget(
    ProviderScope(
      overrides: [
        questionnaireApiProvider.overrideWithValue(q ?? FakeQuestionnaireApi()),
        if (journal != null) journalApiProvider.overrideWithValue(journal),
        linkOpenerProvider.overrideWithValue((uri) async {
          opened?.add(uri);
          return true;
        }),
      ],
      child: MaterialApp(home: child),
    ),
  );
}

String questionText(WidgetTester tester) =>
    tester.widget<Text>(find.byKey(const ValueKey('question'))).data!;

void main() {
  test('QuestionnaireResult parses subscales and support', () {
    final r = QuestionnaireResult.fromJson({
      'id': 3,
      'instrument': 'dass21',
      'total': 40,
      'max_total': 126,
      'severity': 'moderate',
      'severity_label': 'Moderate (depression)',
      'level': 2,
      'max_level': 4,
      'subscales': [
        {
          'code': 'depression',
          'label': 'Depression',
          'score': 14,
          'severity': 'moderate',
          'severity_label': 'Moderate',
          'level': 2,
        },
      ],
      'item9_flag': false,
      'created_at': '2026-11-24T10:00:00Z',
      'support': {'level': 'suggest', 'title': 'T', 'message': 'M'},
    });
    expect(r.subscales.single.score, 14);
    expect(r.support!.isUrgent, isFalse);
  });

  testWidgets('One question per step, back keeps answers, submit sends all', (
    tester,
  ) async {
    final api = FakeQuestionnaireApi();
    await pump(
      tester,
      const QuestionnaireFlowScreen(instrument: 'gad7'),
      q: api,
    );
    await tester.pumpAndSettle();
    expect(questionText(tester), 'Q one');

    await tester.tap(find.byKey(const ValueKey('option-1')));
    await tester.pumpAndSettle();
    expect(questionText(tester), 'Q two'); // auto-advances

    await tester.tap(find.byKey(const ValueKey('back')));
    await tester.pumpAndSettle();
    expect(questionText(tester), 'Q one');
    await tester.tap(find.byKey(const ValueKey('next')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('option-2')));
    await tester.pumpAndSettle();
    final submit = find.byKey(const ValueKey('submit'));
    expect(tester.widget<FilledButton>(submit).onPressed, isNull);
    await tester.tap(find.byKey(const ValueKey('option-0')));
    await tester.pumpAndSettle();
    await tester.tap(submit);
    await tester.pumpAndSettle();

    expect(api.sent, [1, 2, 0]);
    expect(find.byKey(const ValueKey('result')), findsOneWidget);
    expect(find.text('Mild'), findsOneWidget);
    expect(find.textContaining('not a diagnosis'), findsOneWidget);
    expect(find.byKey(const ValueKey('support-sheet')), findsNothing);
  });

  testWidgets('Urgent result opens the crisis card with tap-to-call', (
    tester,
  ) async {
    final opened = <Uri>[];
    await pump(
      tester,
      const QuestionnaireFlowScreen(instrument: 'phq9'),
      q: FakeQuestionnaireApi()..item9 = true,
      opened: opened,
    );
    await tester.pumpAndSettle();
    for (var i = 0; i < 3; i++) {
      await tester.tap(find.byKey(const ValueKey('option-0')));
      await tester.pumpAndSettle();
    }
    await tester.tap(find.byKey(const ValueKey('submit')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('support-sheet')), findsOneWidget);
    expect(find.text("You're not alone"), findsWidgets);
    await tester.tap(find.byKey(const ValueKey('call-14416')));
    await tester.pump();
    expect(opened, [Uri(scheme: 'tel', path: '14416')]);

    await tester.tap(find.byKey(const ValueKey('support-close')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('result-get-help')), findsOneWidget);
  });

  testWidgets('Flagged journal note shows the crisis card before closing', (
    tester,
  ) async {
    var saved = false;
    await pump(
      tester,
      MoodLogScreen(initialMood: 1, onSaved: () => saved = true),
      journal: FlaggingJournalApi(),
    );
    await tester.enterText(find.byKey(const ValueKey('note')), 'hard day');
    await tester.tap(find.byKey(const ValueKey('save-mood')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('support-sheet')), findsOneWidget);
    expect(saved, isFalse);
    await tester.tap(find.byKey(const ValueKey('support-close')));
    await tester.pumpAndSettle();
    expect(saved, isTrue);
  });
}
