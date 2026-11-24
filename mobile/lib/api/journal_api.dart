import 'package:dio/dio.dart';

import 'support.dart';

/// Hand-written for Step 2 (mirrors backend/app/schemas/journal.py).

class MoodLog {
  MoodLog({
    required this.id,
    required this.moodScore,
    required this.createdAt,
    this.sleepHours,
    this.energy,
    this.tags = const [],
    this.note,
    this.support,
  });

  factory MoodLog.fromJson(Map<String, dynamic> json) => MoodLog(
    id: json['id'] as int,
    moodScore: json['mood_score'] as int,
    sleepHours: (json['sleep_hours'] as num?)?.toDouble(),
    energy: json['energy'] as int?,
    tags: [for (final t in json['tags'] as List<dynamic>) t as String],
    note: json['note'] as String?,
    createdAt: DateTime.parse(json['created_at'] as String).toLocal(),
    support: Support.maybe(json['support']),
  );

  final int id;
  final int moodScore;
  final double? sleepHours;
  final int? energy;
  final List<String> tags;
  final String? note;
  final DateTime createdAt;

  /// Set only on the create response, when the note needs a safety follow-up.
  final Support? support;
}

class NewMoodLog {
  const NewMoodLog({
    required this.moodScore,
    this.sleepHours,
    this.energy,
    this.tags = const [],
    this.note,
  });

  final int moodScore;
  final double? sleepHours;
  final int? energy;
  final List<String> tags;
  final String? note;

  Map<String, dynamic> toJson() => {
    'mood_score': moodScore,
    'sleep_hours': ?sleepHours,
    'energy': ?energy,
    'tags': tags,
    if (note != null && note!.trim().isNotEmpty) 'note': note!.trim(),
  };
}

class MoodLogPage {
  MoodLogPage(this.items, this.nextBeforeId);

  factory MoodLogPage.fromJson(Map<String, dynamic> json) => MoodLogPage([
    for (final i in json['items'] as List<dynamic>)
      MoodLog.fromJson(i as Map<String, dynamic>),
  ], json['next_before_id'] as int?);

  final List<MoodLog> items;
  final int? nextBeforeId;
}

class DaySummary {
  DaySummary({
    required this.date,
    required this.entries,
    this.moodAvg,
    this.sleepAvg,
  });

  factory DaySummary.fromJson(Map<String, dynamic> json) => DaySummary(
    date: DateTime.parse(json['date'] as String),
    entries: json['entries'] as int,
    moodAvg: (json['mood_avg'] as num?)?.toDouble(),
    sleepAvg: (json['sleep_avg'] as num?)?.toDouble(),
  );

  final DateTime date;
  final int entries;
  final double? moodAvg;
  final double? sleepAvg;
}

class JournalInsights {
  JournalInsights({
    required this.rangeDays,
    required this.days,
    required this.entries,
    required this.streakDays,
    required this.topTags,
    this.moodAvg,
    this.sleepAvg,
  });

  factory JournalInsights.fromJson(Map<String, dynamic> json) =>
      JournalInsights(
        rangeDays: json['range_days'] as int,
        days: [
          for (final d in json['days'] as List<dynamic>)
            DaySummary.fromJson(d as Map<String, dynamic>),
        ],
        entries: json['entries'] as int,
        moodAvg: (json['mood_avg'] as num?)?.toDouble(),
        sleepAvg: (json['sleep_avg'] as num?)?.toDouble(),
        streakDays: json['streak_days'] as int,
        topTags: {
          for (final t in json['top_tags'] as List<dynamic>)
            (t as Map<String, dynamic>)['tag'] as String: t['count'] as int,
        },
      );

  final int rangeDays;
  final List<DaySummary> days;
  final int entries;
  final double? moodAvg;
  final double? sleepAvg;
  final int streakDays;

  /// Most frequent tags in the range, most frequent first.
  final Map<String, int> topTags;
}

abstract interface class JournalApi {
  Future<MoodLog> create(NewMoodLog entry);
  Future<MoodLogPage> list({int limit = 20, int? beforeId});
  Future<JournalInsights> insights({required int rangeDays});
}

class DioJournalApi implements JournalApi {
  DioJournalApi(this._dio);
  final Dio _dio;

  @override
  Future<MoodLog> create(NewMoodLog entry) async {
    final res = await _dio.post<Map<String, dynamic>>(
      '/api/v1/journal',
      data: entry.toJson(),
    );
    return MoodLog.fromJson(res.data!);
  }

  @override
  Future<MoodLogPage> list({int limit = 20, int? beforeId}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/journal',
      queryParameters: {'limit': limit, 'before_id': ?beforeId},
    );
    return MoodLogPage.fromJson(res.data!);
  }

  @override
  Future<JournalInsights> insights({required int rangeDays}) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/journal/insights',
      queryParameters: {
        'range': '${rangeDays}d',
        // Days are grouped by the student's local calendar.
        'tz_offset_minutes': DateTime.now().timeZoneOffset.inMinutes,
      },
    );
    return JournalInsights.fromJson(res.data!);
  }
}
