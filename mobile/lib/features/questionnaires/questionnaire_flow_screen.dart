import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../api/questionnaire_api.dart';
import '../../core/providers.dart';
import '../../shared/help_sheet.dart';
import 'questionnaire_result_view.dart';

/// S-10: one question per step, progress bar, back button; then S-11 result.
class QuestionnaireFlowScreen extends ConsumerStatefulWidget {
  const QuestionnaireFlowScreen({super.key, required this.instrument});
  final String instrument;

  @override
  ConsumerState<QuestionnaireFlowScreen> createState() => _FlowState();
}

class _FlowState extends ConsumerState<QuestionnaireFlowScreen> {
  final _answers = <int, int>{};
  int _step = 0;
  bool _busy = false;
  String? _error;
  QuestionnaireResult? _result;

  Future<void> _submit(QuestionnaireDefinition d) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await ref.read(questionnaireApiProvider).submit(
        widget.instrument,
        [for (var i = 0; i < d.items.length; i++) _answers[i]!],
      );
      ref.invalidate(questionnairesProvider);
      ref.invalidate(questionnaireHistoryProvider(widget.instrument));
      if (!mounted) return;
      setState(() => _result = result);
      if (result.support?.isUrgent ?? false) {
        // Crisis card first (PHQ-9 item 9). The result stays underneath.
        await showSupportSheet(context, result.support!);
      }
    } on Exception catch (_) {
      if (mounted) {
        setState(() => _error = 'Could not submit. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _choose(QuestionnaireDefinition d, int value) {
    setState(() {
      _answers[_step] = value;
      if (_step < d.items.length - 1) _step++;
    });
  }

  @override
  Widget build(BuildContext context) {
    final def = ref.watch(questionnaireDefinitionProvider(widget.instrument));
    return Scaffold(
      appBar: AppBar(title: Text(def.value?.shortName ?? 'Questionnaire')),
      floatingActionButton: const HelpButton(),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      body: Column(
        children: [
          const DisclaimerBar(),
          Expanded(
            child: def.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, _) => Center(
                child: TextButton(
                  onPressed: () => ref.invalidate(
                    questionnaireDefinitionProvider(widget.instrument),
                  ),
                  child: const Text('Could not load. Retry'),
                ),
              ),
              data: (d) => _result != null
                  ? QuestionnaireResultView(result: _result!)
                  : _question(context, d),
            ),
          ),
        ],
      ),
    );
  }

  Widget _question(BuildContext context, QuestionnaireDefinition d) {
    final text = Theme.of(context).textTheme;
    final total = d.items.length;
    final isLast = _step == total - 1;
    final complete = _answers.length == total;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
      children: [
        LinearProgressIndicator(value: (_step + 1) / total),
        const SizedBox(height: 8),
        Text('Question ${_step + 1} of $total', style: text.labelMedium),
        const SizedBox(height: 12),
        Text(d.stem, style: text.bodyMedium),
        const SizedBox(height: 8),
        Text(
          d.items[_step],
          key: const ValueKey('question'),
          style: text.titleLarge,
        ),
        const SizedBox(height: 16),
        RadioGroup<int>(
          groupValue: _answers[_step],
          onChanged: (v) => _busy || v == null ? null : _choose(d, v),
          child: Column(
            children: [
              for (var i = 0; i < d.options.length; i++)
                RadioListTile<int>(
                  key: ValueKey('option-$i'),
                  value: i,
                  title: Text(d.options[i]),
                ),
            ],
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        const SizedBox(height: 16),
        Row(
          children: [
            OutlinedButton(
              key: const ValueKey('back'),
              onPressed: _step == 0 || _busy
                  ? null
                  : () => setState(() => _step--),
              child: const Text('Back'),
            ),
            const Spacer(),
            if (isLast)
              FilledButton(
                key: const ValueKey('submit'),
                onPressed: complete && !_busy ? () => _submit(d) : null,
                child: const Text('See my result'),
              )
            else
              FilledButton(
                key: const ValueKey('next'),
                onPressed: _answers.containsKey(_step) && !_busy
                    ? () => setState(() => _step++)
                    : null,
                child: const Text('Next'),
              ),
          ],
        ),
      ],
    );
  }
}
