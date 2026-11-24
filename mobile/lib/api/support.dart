/// Support message returned by the API after a submission
/// (mirrors backend/app/schemas/support.py).
class Support {
  const Support({
    required this.level,
    required this.title,
    required this.message,
  });

  factory Support.fromJson(Map<String, dynamic> j) => Support(
    level: j['level'] as String,
    title: j['title'] as String,
    message: j['message'] as String,
  );

  static Support? maybe(Object? json) =>
      json == null ? null : Support.fromJson(json as Map<String, dynamic>);

  /// "urgent" (show the crisis card now) or "suggest" (gentle nudge).
  final String level;
  final String title;
  final String message;

  bool get isUrgent => level == 'urgent';
}
