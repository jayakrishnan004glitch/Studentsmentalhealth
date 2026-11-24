import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api/journal_api.dart';
import '../api/me_api.dart';
import '../api/questionnaire_api.dart';
import '../api/study_api.dart';
import 'config.dart';

final supabaseProvider = Provider<SupabaseClient>(
  (ref) => Supabase.instance.client,
);

/// Dio for the FastAPI backend, sending the current Supabase access token.
final apiDioProvider = Provider<Dio>((ref) {
  final supabase = ref.watch(supabaseProvider);
  return buildApiDio(
    AppConfig.apiBaseUrl,
    () => supabase.auth.currentSession?.accessToken,
  );
});

final meApiProvider = Provider<MeApi>(
  (ref) => DioMeApi(ref.watch(apiDioProvider)),
);

/// The signed-in student's profile and consent state from the API.
final meProvider = FutureProvider<Me>(
  (ref) => ref.watch(meApiProvider).getMe(),
);

final journalApiProvider = Provider<JournalApi>(
  (ref) => DioJournalApi(ref.watch(apiDioProvider)),
);

/// Mood/sleep insights for the last N days (7, 30 or 90).
final journalInsightsProvider = FutureProvider.autoDispose
    .family<JournalInsights, int>(
      (ref, rangeDays) =>
          ref.watch(journalApiProvider).insights(rangeDays: rangeDays),
    );

final questionnaireApiProvider = Provider<QuestionnaireApi>(
  (ref) => DioQuestionnaireApi(ref.watch(apiDioProvider)),
);

final questionnairesProvider =
    FutureProvider.autoDispose<List<QuestionnaireSummary>>(
      (ref) => ref.watch(questionnaireApiProvider).list(),
    );

final questionnaireDefinitionProvider = FutureProvider.autoDispose
    .family<QuestionnaireDefinition, String>(
      (ref, instrument) =>
          ref.watch(questionnaireApiProvider).definition(instrument),
    );

final questionnaireHistoryProvider = FutureProvider.autoDispose
    .family<List<ResultHistoryItem>, String>(
      (ref, instrument) =>
          ref.watch(questionnaireApiProvider).history(instrument),
    );

final studyApiProvider = Provider<StudyApi>(
  (ref) => DioStudyApi(ref.watch(apiDioProvider)),
);

final studyCatalogProvider = FutureProvider<StudyCatalog>(
  (ref) => ref.watch(studyApiProvider).catalog(),
);

/// Subjects for the student's profile; pass a semester to browse another one.
final subjectsProvider = FutureProvider.autoDispose.family<SubjectList, int?>(
  (ref, semester) => ref.watch(studyApiProvider).subjects(semester: semester),
  // "Course not set up" will not fix itself by retrying.
  retry: (count, error) => error is StudyProfileIncomplete || count >= 3
      ? null
      : Duration(seconds: 1 << count),
);

final subjectDetailProvider = FutureProvider.autoDispose
    .family<SubjectDetail, int>(
      (ref, id) => ref.watch(studyApiProvider).subject(id),
    );

/// Opens a study link outside the app (overridden in tests).
final linkOpenerProvider = Provider<Future<bool> Function(Uri)>(
  (ref) =>
      (uri) => launchUrl(uri, mode: LaunchMode.externalApplication),
);

/// The most recent journal entries (first page).
final recentMoodLogsProvider = FutureProvider.autoDispose<MoodLogPage>(
  (ref) => ref.watch(journalApiProvider).list(limit: 30),
);
