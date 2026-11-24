import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../api/journal_api.dart';
import '../../core/providers.dart';
import '../../shared/help_sheet.dart';
import '../../shared/mood.dart';

/// S-07: log mood, sleep, energy, tags and an optional note.
class MoodLogScreen extends ConsumerStatefulWidget {
  const MoodLogScreen({super.key, this.initialMood, this.onSaved});

  final int? initialMood;
  final VoidCallback? onSaved;

  @override
  ConsumerState<MoodLogScreen> createState() => _MoodLogScreenState();
}

class _MoodLogScreenState extends ConsumerState<MoodLogScreen> {
  late int? _mood = widget.initialMood;
  bool _logSleep = false;
  double _sleep = 7;
  int? _energy;
  final _tags = <String>{};
  final _note = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final saved = await ref
          .read(journalApiProvider)
          .create(
            NewMoodLog(
              moodScore: _mood!,
              sleepHours: _logSleep ? _sleep : null,
              energy: _energy,
              tags: [
                for (final t in moodTags.keys)
                  if (_tags.contains(t)) t,
              ],
              note: _note.text,
            ),
          );
      ref.invalidate(journalInsightsProvider);
      ref.invalidate(recentMoodLogsProvider);
      if (!mounted) return;
      if (saved.support != null) {
        // The note triggered the safety rules: show help before leaving.
        await showSupportSheet(context, saved.support!);
        if (!mounted) return;
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Saved. Thanks for checking in.')),
        );
      }
      if (widget.onSaved != null) {
        widget.onSaved!();
      } else {
        Navigator.of(context).maybePop();
      }
    } on Exception catch (_) {
      if (mounted) setState(() => _error = 'Could not save. Please try again.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Mood check-in')),
      floatingActionButton: const HelpButton(),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      body: Column(
        children: [
          const DisclaimerBar(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
              children: [
                Text('How are you feeling?', style: text.titleMedium),
                const SizedBox(height: 8),
                MoodPicker(
                  selected: _mood,
                  onSelected: (v) => setState(() => _mood = v),
                ),
                const Divider(height: 32),
                SwitchListTile(
                  key: const ValueKey('log-sleep'),
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Log last night\'s sleep'),
                  value: _logSleep,
                  onChanged: (v) => setState(() => _logSleep = v),
                ),
                if (_logSleep) ...[
                  Text(
                    '${_formatHours(_sleep)} of sleep',
                    style: text.bodyLarge,
                  ),
                  Slider(
                    key: const ValueKey('sleep-slider'),
                    value: _sleep,
                    max: 14,
                    divisions: 28,
                    label: _formatHours(_sleep),
                    onChanged: (v) => setState(() => _sleep = v),
                  ),
                ],
                const Divider(height: 32),
                Text('Energy (optional)', style: text.titleMedium),
                const SizedBox(height: 8),
                SegmentedButton<int>(
                  emptySelectionAllowed: true,
                  showSelectedIcon: false,
                  segments: const [
                    ButtonSegment(value: 1, label: Text('1')),
                    ButtonSegment(value: 2, label: Text('2')),
                    ButtonSegment(value: 3, label: Text('3')),
                    ButtonSegment(value: 4, label: Text('4')),
                    ButtonSegment(value: 5, label: Text('5')),
                  ],
                  selected: {?_energy},
                  onSelectionChanged: (s) =>
                      setState(() => _energy = s.isEmpty ? null : s.first),
                ),
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    '1 = drained, 5 = full of energy',
                    style: text.bodySmall,
                  ),
                ),
                const Divider(height: 32),
                Text(
                  'What\'s on your mind? (optional)',
                  style: text.titleMedium,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 4,
                  children: [
                    for (final e in moodTags.entries)
                      FilterChip(
                        key: ValueKey('tag-${e.key}'),
                        label: Text(e.value),
                        selected: _tags.contains(e.key),
                        onSelected: (on) => setState(
                          () => on ? _tags.add(e.key) : _tags.remove(e.key),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                TextField(
                  key: const ValueKey('note'),
                  controller: _note,
                  maxLength: 1000,
                  maxLines: 4,
                  minLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Note (optional, private)',
                    alignLabelWithHint: true,
                  ),
                ),
                if (_error != null)
                  Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: FilledButton(
            key: const ValueKey('save-mood'),
            onPressed: _mood != null && !_busy ? _save : null,
            child: const Text('Save'),
          ),
        ),
      ),
    );
  }
}

String _formatHours(double h) {
  final whole = h.truncate();
  final half = h - whole >= 0.5;
  return half ? '${whole}h 30m' : '${whole}h';
}
