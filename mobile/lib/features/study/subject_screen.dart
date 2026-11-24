import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../api/study_api.dart';
import '../../core/providers.dart';

const _kindLabels = {
  'notes': 'Notes',
  'question_paper': 'Question paper',
  'syllabus': 'Syllabus',
  'video': 'Video',
  'textbook': 'Textbook',
  'other': 'Link',
};

const _kindIcons = {
  'notes': Icons.description_outlined,
  'question_paper': Icons.quiz_outlined,
  'syllabus': Icons.list_alt,
  'video': Icons.play_circle_outline,
  'textbook': Icons.menu_book_outlined,
  'other': Icons.link,
};

/// One subject's links, grouped by module. Links open in the browser.
class SubjectScreen extends ConsumerWidget {
  const SubjectScreen({super.key, required this.subjectId});
  final int subjectId;

  Future<void> _open(
    BuildContext context,
    WidgetRef ref,
    StudyLink link,
  ) async {
    final uri = Uri.tryParse(link.url);
    var ok = false;
    if (uri != null && uri.scheme == 'https') {
      try {
        ok = await ref.read(linkOpenerProvider)(uri);
      } catch (_) {
        ok = false;
      }
    }
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Could not open the link.')));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(subjectDetailProvider(subjectId));
    return Scaffold(
      appBar: AppBar(title: Text(detail.value?.code ?? 'Subject')),
      body: detail.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, _) => Center(
          child: TextButton(
            onPressed: () => ref.invalidate(subjectDetailProvider(subjectId)),
            child: const Text('Could not load. Retry'),
          ),
        ),
        data: (s) {
          final groups = <int?, List<StudyLink>>{};
          for (final l in s.links) {
            groups.putIfAbsent(l.module, () => []).add(l);
          }
          final text = Theme.of(context).textTheme;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Text(s.name, style: text.titleLarge),
              const SizedBox(height: 4),
              Text(
                'Links open external websites that are not run by the app.',
                style: text.bodySmall,
              ),
              if (s.links.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: Text('No links for this subject yet.'),
                ),
              for (final e in groups.entries) ...[
                const SizedBox(height: 16),
                Text(
                  e.key == null ? 'Whole subject' : 'Module ${e.key}',
                  style: text.titleSmall,
                ),
                for (final l in e.value)
                  ListTile(
                    key: ValueKey('link-${l.id}'),
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(_kindIcons[l.kind] ?? Icons.link),
                    title: Text(l.title),
                    subtitle: Text(
                      [
                        _kindLabels[l.kind] ?? l.kind,
                        Uri.tryParse(l.url)?.host ?? '',
                        ?l.sourceName,
                      ].where((x) => x.isNotEmpty).join(' · '),
                    ),
                    trailing: const Icon(Icons.open_in_new, size: 20),
                    onTap: () => _open(context, ref, l),
                  ),
              ],
            ],
          );
        },
      ),
    );
  }
}
