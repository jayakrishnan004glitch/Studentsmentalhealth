import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../api/questionnaire_api.dart';
import '../../core/providers.dart';
import '../../shared/help_sheet.dart';

/// S-11: screening band (never a diagnosis), what it means, next steps, history.
class QuestionnaireResultView extends ConsumerWidget {
  const QuestionnaireResultView({super.key, required this.result});
  final QuestionnaireResult result;

  String get _meaning {
    final high = result.level >= result.maxLevel - 1;
    if (result.level == 0) {
      return 'Your answers are in the lowest range. Keep looking after yourself.';
    }
    if (high) {
      return 'Your answers are in a higher range. Talking to your college '
          'counsellor or a doctor is a good next step.';
    }
    return 'Your answers show some difficulties. Small steps can help: sleep, '
        'movement, and talking to someone you trust.';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final history = ref.watch(questionnaireHistoryProvider(result.instrument));
    final support = result.support;
    return ListView(
      key: const ValueKey('result'),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
      children: [
        Text('Your screening result', style: text.titleMedium),
        const SizedBox(height: 8),
        Text(result.severityLabel, style: text.headlineMedium),
        const SizedBox(height: 4),
        Text('Score ${result.total} of ${result.maxTotal}'),
        const SizedBox(height: 8),
        LinearProgressIndicator(
          value: result.maxLevel == 0 ? 0 : result.level / result.maxLevel,
          minHeight: 8,
          borderRadius: BorderRadius.circular(4),
        ),
        for (final s in result.subscales)
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(s.label),
            trailing: Text('${s.severityLabel} · ${s.score}'),
          ),
        const SizedBox(height: 12),
        Text(_meaning),
        const SizedBox(height: 8),
        Text(
          'This is a screening, not a diagnosis. Only a qualified professional '
          'can diagnose a condition.',
          style: text.bodySmall,
        ),
        if (support != null) ...[
          const SizedBox(height: 16),
          Card(
            color: support.isUrgent
                ? scheme.errorContainer
                : scheme.secondaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(support.title, style: text.titleMedium),
                  const SizedBox(height: 4),
                  Text(support.message),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    key: const ValueKey('result-get-help'),
                    icon: const Icon(Icons.support_agent),
                    label: const Text('Talk to someone'),
                    onPressed: () => showSupportSheet(context, support),
                  ),
                ],
              ),
            ),
          ),
        ],
        const SizedBox(height: 16),
        history.maybeWhen(
          data: (items) => items.length < 2
              ? const SizedBox.shrink()
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Previous results', style: text.titleSmall),
                    for (final h in items.skip(1).take(5))
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        dense: true,
                        title: Text(
                          '${h.createdAt.day}/${h.createdAt.month}/${h.createdAt.year}',
                        ),
                        trailing: Text('Score ${h.total}'),
                      ),
                  ],
                ),
          orElse: () => const SizedBox.shrink(),
        ),
      ],
    );
  }
}
