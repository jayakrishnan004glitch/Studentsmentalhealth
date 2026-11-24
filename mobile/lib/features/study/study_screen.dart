import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../api/study_api.dart';
import '../../core/providers.dart';
import '../../shared/help_sheet.dart';

/// KTU study material: the student's subjects for a semester.
class StudyScreen extends ConsumerStatefulWidget {
  const StudyScreen({super.key});

  @override
  ConsumerState<StudyScreen> createState() => _StudyScreenState();
}

class _StudyScreenState extends ConsumerState<StudyScreen> {
  /// null = the student's own semester.
  int? _semester;

  @override
  Widget build(BuildContext context) {
    final subjects = ref.watch(subjectsProvider(_semester));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Study material'),
        actions: [
          IconButton(
            key: const ValueKey('change-course'),
            tooltip: 'Change course',
            icon: const Icon(Icons.tune),
            onPressed: () => context.push('/study/setup'),
          ),
        ],
      ),
      floatingActionButton: const HelpButton(),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      body: subjects.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => e is StudyProfileIncomplete
            ? _SetupPrompt(onSetup: () => context.push('/study/setup'))
            : Center(
                child: TextButton(
                  onPressed: () => ref.invalidate(subjectsProvider),
                  child: const Text('Could not load subjects. Retry'),
                ),
              ),
        data: (list) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
          children: [
            Text(
              '${list.branch} · ${list.scheme} scheme',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (var s = 1; s <= 8; s++)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: ChoiceChip(
                        key: ValueKey('sem-$s'),
                        label: Text('S$s'),
                        selected: list.semester == s,
                        onSelected: (_) => setState(() => _semester = s),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            if (list.subjects.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Text(
                  'No subjects added for this semester yet. '
                  'Your college admin adds them.',
                ),
              ),
            for (final s in list.subjects)
              Card(
                child: ListTile(
                  key: ValueKey('subject-${s.id}'),
                  title: Text(s.name),
                  subtitle: Text(
                    '${s.code} · ${s.linkCount} '
                    '${s.linkCount == 1 ? 'link' : 'links'}',
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/study/subjects/${s.id}'),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _SetupPrompt extends StatelessWidget {
  const _SetupPrompt({required this.onSetup});
  final VoidCallback onSetup;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.school_outlined, size: 48),
          const SizedBox(height: 12),
          const Text(
            'Tell us your KTU scheme, branch and semester to see your subjects.',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          FilledButton(
            key: const ValueKey('setup-course'),
            onPressed: onSetup,
            child: const Text('Set up my course'),
          ),
        ],
      ),
    ),
  );
}
