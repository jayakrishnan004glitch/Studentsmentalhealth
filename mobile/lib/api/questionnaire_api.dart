import 'package:dio/dio.dart';

import 'support.dart';

/// Hand-written client for /api/v1/questionnaires
/// (mirrors backend/app/schemas/questionnaire.py).

class QuestionnaireSummary {
  QuestionnaireSummary({
    required this.instrument,
    required this.shortName,
    required this.description,
    required this.itemCount,
    required this.minutes,
    this.lastTakenAt,
    this.lastSeverityLabel,
  });

  factory QuestionnaireSummary.fromJson(Map<String, dynamic> j) =>
      QuestionnaireSummary(
        instrument: j['instrument'] as String,
        shortName: j['short_name'] as String,
        description: j['description'] as String,
        itemCount: j['item_count'] as int,
        minutes: j['minutes'] as int,
        lastTakenAt: j['last_taken_at'] == null
            ? null
            : DateTime.parse(j['last_taken_at'] as String).toLocal(),
        lastSeverityLabel: j['last_severity_label'] as String?,
      );

  final String instrument;
  final String shortName;
  final String description;
  final int itemCount;
  final int minutes;
  final DateTime? lastTakenAt;
  final String? lastSeverityLabel;
}

class QuestionnaireDefinition {
  QuestionnaireDefinition({
    required this.instrument,
    required this.shortName,
    required this.stem,
    required this.options,
    required this.items,
  });

  factory QuestionnaireDefinition.fromJson(Map<String, dynamic> j) =>
      QuestionnaireDefinition(
        instrument: j['instrument'] as String,
        shortName: j['short_name'] as String,
        stem: j['stem'] as String,
        options: [for (final o in j['options'] as List<dynamic>) o as String],
        items: [for (final i in j['items'] as List<dynamic>) i as String],
      );

  final String instrument;
  final String shortName;
  final String stem;

  /// Index = score for that option.
  final List<String> options;
  final List<String> items;
}

class Subscale {
  Subscale(this.code, this.label, this.score, this.severityLabel, this.level);

  factory Subscale.fromJson(Map<String, dynamic> j) => Subscale(
    j['code'] as String,
    j['label'] as String,
    j['score'] as int,
    j['severity_label'] as String,
    j['level'] as int,
  );

  final String code;
  final String label;
  final int score;
  final String severityLabel;
  final int level;
}

class QuestionnaireResult {
  QuestionnaireResult({
    required this.id,
    required this.instrument,
    required this.total,
    required this.maxTotal,
    required this.severityLabel,
    required this.level,
    required this.maxLevel,
    required this.subscales,
    required this.item9Flag,
    this.support,
  });

  factory QuestionnaireResult.fromJson(Map<String, dynamic> j) =>
      QuestionnaireResult(
        id: j['id'] as int,
        instrument: j['instrument'] as String,
        total: j['total'] as int,
        maxTotal: j['max_total'] as int,
        severityLabel: j['severity_label'] as String,
        level: j['level'] as int,
        maxLevel: j['max_level'] as int,
        subscales: [
          for (final s in j['subscales'] as List<dynamic>)
            Subscale.fromJson(s as Map<String, dynamic>),
        ],
        item9Flag: j['item9_flag'] as bool,
        support: Support.maybe(j['support']),
      );

  final int id;
  final String instrument;
  final int total;
  final int maxTotal;
  final String severityLabel;
  final int level;
  final int maxLevel;
  final List<Subscale> subscales;
  final bool item9Flag;
  final Support? support;
}

class ResultHistoryItem {
  ResultHistoryItem(this.total, this.level, this.createdAt);

  factory ResultHistoryItem.fromJson(Map<String, dynamic> j) =>
      ResultHistoryItem(
        j['total'] as int,
        j['level'] as int,
        DateTime.parse(j['created_at'] as String).toLocal(),
      );

  final int total;
  final int level;
  final DateTime createdAt;
}

abstract interface class QuestionnaireApi {
  Future<List<QuestionnaireSummary>> list();
  Future<QuestionnaireDefinition> definition(String instrument);
  Future<QuestionnaireResult> submit(String instrument, List<int> answers);
  Future<List<ResultHistoryItem>> history(String instrument);
}

class DioQuestionnaireApi implements QuestionnaireApi {
  DioQuestionnaireApi(this._dio);
  final Dio _dio;

  @override
  Future<List<QuestionnaireSummary>> list() async {
    final res = await _dio.get<List<dynamic>>('/api/v1/questionnaires');
    return [
      for (final q in res.data!)
        QuestionnaireSummary.fromJson(q as Map<String, dynamic>),
    ];
  }

  @override
  Future<QuestionnaireDefinition> definition(String instrument) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/questionnaires/$instrument',
    );
    return QuestionnaireDefinition.fromJson(res.data!);
  }

  @override
  Future<QuestionnaireResult> submit(
    String instrument,
    List<int> answers,
  ) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/questionnaires/$instrument',
      data: {'answers': answers},
    );
    return QuestionnaireResult.fromJson(res.data!);
  }

  @override
  Future<List<ResultHistoryItem>> history(String instrument) async {
    final res = await _dio.get<List<dynamic>>(
      '/api/v1/questionnaires/$instrument/results',
    );
    return [
      for (final h in res.data!)
        ResultHistoryItem.fromJson(h as Map<String, dynamic>),
    ];
  }
}
