import 'package:dio/dio.dart';

/// Hand-written client for /api/v1/study (mirrors backend/app/schemas/study.py).

class CodeName {
  const CodeName(this.code, this.name);
  factory CodeName.fromJson(Map<String, dynamic> j) =>
      CodeName(j['code'] as String, j['name'] as String);
  final String code;
  final String name;
}

class StudyCatalog {
  StudyCatalog({
    required this.schemes,
    required this.branches,
    required this.semesters,
  });

  factory StudyCatalog.fromJson(Map<String, dynamic> j) => StudyCatalog(
    schemes: [
      for (final s in j['schemes'] as List<dynamic>)
        CodeName.fromJson(s as Map<String, dynamic>),
    ],
    branches: [
      for (final b in j['branches'] as List<dynamic>)
        CodeName.fromJson(b as Map<String, dynamic>),
    ],
    semesters: [for (final s in j['semesters'] as List<dynamic>) s as int],
  );

  final List<CodeName> schemes;
  final List<CodeName> branches;
  final List<int> semesters;
}

class Subject {
  Subject({
    required this.id,
    required this.scheme,
    required this.code,
    required this.name,
    required this.linkCount,
  });

  factory Subject.fromJson(Map<String, dynamic> j) => Subject(
    id: j['id'] as int,
    scheme: j['scheme'] as String,
    code: j['code'] as String,
    name: j['name'] as String,
    linkCount: j['link_count'] as int,
  );

  final int id;
  final String scheme;
  final String code;
  final String name;
  final int linkCount;
}

class SubjectList {
  SubjectList({
    required this.scheme,
    required this.branch,
    required this.semester,
    required this.subjects,
  });

  factory SubjectList.fromJson(Map<String, dynamic> j) => SubjectList(
    scheme: j['scheme'] as String,
    branch: j['branch'] as String,
    semester: j['semester'] as int,
    subjects: [
      for (final s in j['subjects'] as List<dynamic>)
        Subject.fromJson(s as Map<String, dynamic>),
    ],
  );

  final String scheme;
  final String branch;
  final int semester;
  final List<Subject> subjects;
}

class StudyLink {
  StudyLink({
    required this.id,
    required this.kind,
    required this.title,
    required this.url,
    this.module,
    this.sourceName,
  });

  factory StudyLink.fromJson(Map<String, dynamic> j) => StudyLink(
    id: j['id'] as int,
    module: j['module'] as int?,
    kind: j['kind'] as String,
    title: j['title'] as String,
    url: j['url'] as String,
    sourceName: j['source_name'] as String?,
  );

  final int id;

  /// 1–6, or null for links about the whole subject.
  final int? module;

  /// notes, question_paper, syllabus, video, textbook, other
  final String kind;
  final String title;
  final String url;
  final String? sourceName;
}

class SubjectDetail {
  SubjectDetail({
    required this.id,
    required this.scheme,
    required this.code,
    required this.name,
    required this.links,
  });

  factory SubjectDetail.fromJson(Map<String, dynamic> j) => SubjectDetail(
    id: j['id'] as int,
    scheme: j['scheme'] as String,
    code: j['code'] as String,
    name: j['name'] as String,
    links: [
      for (final l in j['links'] as List<dynamic>)
        StudyLink.fromJson(l as Map<String, dynamic>),
    ],
  );

  final int id;
  final String scheme;
  final String code;
  final String name;
  final List<StudyLink> links;
}

/// Thrown when the student has not set scheme/branch/semester yet (HTTP 409).
class StudyProfileIncomplete implements Exception {}

abstract interface class StudyApi {
  Future<StudyCatalog> catalog();

  /// Subjects for the student's profile; [semester] browses another semester.
  Future<SubjectList> subjects({int? semester});
  Future<SubjectDetail> subject(int id);
}

class DioStudyApi implements StudyApi {
  DioStudyApi(this._dio);
  final Dio _dio;

  @override
  Future<StudyCatalog> catalog() async {
    final res = await _dio.get<Map<String, dynamic>>('/api/v1/study/catalog');
    return StudyCatalog.fromJson(res.data!);
  }

  @override
  Future<SubjectList> subjects({int? semester}) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>(
        '/api/v1/study/subjects',
        queryParameters: {'semester': ?semester},
      );
      return SubjectList.fromJson(res.data!);
    } on DioException catch (e) {
      if (e.response?.statusCode == 409) throw StudyProfileIncomplete();
      rethrow;
    }
  }

  @override
  Future<SubjectDetail> subject(int id) async {
    final res = await _dio.get<Map<String, dynamic>>(
      '/api/v1/study/subjects/$id',
    );
    return SubjectDetail.fromJson(res.data!);
  }
}
