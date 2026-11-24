import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/providers.dart';
import '../../shared/help_sheet.dart';

/// S-09: PHQ-9, GAD-7, DASS-21 with the last time each was taken.
class QuestionnaireListScreen extends ConsumerWidget {
  const QuestionnaireListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = ref.watch(questionnairesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Check-in questionnaires')),
      floatingActionButton: const HelpButton(),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      body: Column(
        children: [
          const DisclaimerBar(),
          Expanded(
            child: list.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, _) => Center(
                child: TextButton(
                  onPressed: () => ref.invalidate(questionnairesProvider),
                  child: const Text('Could not load. Retry'),
                ),
              ),
              data: (items) => ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                children: [
                  const Text(
                    'Short, standard screening questionnaires. They help you '
                    'notice how you have been doing. They are not a diagnosis.',
                  ),
                  const SizedBox(height: 12),
                  for (final q in items)
                    Card(
                      child: ListTile(
                        key: ValueKey('q-${q.instrument}'),
                        title: Text(q.shortName),
                        subtitle: Text(
                          '${q.description}\n'
                          '${q.itemCount} questions · about ${q.minutes} min'
                          '${q.lastTakenAt == null ? '' : ' · last: ${_date(q.lastTakenAt!)}'
                                    '${q.lastSeverityLabel == null ? '' : ' (${q.lastSeverityLabel})'}'}',
                        ),
                        isThreeLine: true,
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () =>
                            context.push('/questionnaires/${q.instrument}'),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

String _date(DateTime t) => '${t.day}/${t.month}/${t.year}';
