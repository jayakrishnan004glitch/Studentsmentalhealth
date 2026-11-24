import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../api/journal_api.dart';
import '../../core/providers.dart';
import '../../shared/help_sheet.dart';
import '../../shared/mood.dart';
import 'trend_bars.dart';

/// S-08: journal history and insights (7 / 30 days).
class JournalScreen extends ConsumerStatefulWidget {
  const JournalScreen({super.key});

  @override
  ConsumerState<JournalScreen> createState() => _JournalScreenState();
}

class _JournalScreenState extends ConsumerState<JournalScreen> {
  int _range = 7;

  @override
  Widget build(BuildContext context) {
    final insights = ref.watch(journalInsightsProvider(_range));
    final logs = ref.watch(recentMoodLogsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Journal')),
      floatingActionButton: const HelpButton(),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      body: Column(
        children: [
          const DisclaimerBar(),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () async {
                ref.invalidate(journalInsightsProvider);
                ref.invalidate(recentMoodLogsProvider);
                await ref.read(journalInsightsProvider(_range).future);
              },
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                children: [
                  SegmentedButton<int>(
                    segments: const [
                      ButtonSegment(value: 7, label: Text('7 days')),
                      ButtonSegment(value: 30, label: Text('30 days')),
                    ],
                    selected: {_range},
                    onSelectionChanged: (s) => setState(() => _range = s.first),
                  ),
                  const SizedBox(height: 16),
                  insights.when(
                    loading: () => const Padding(
                      padding: EdgeInsets.all(32),
                      child: Center(child: CircularProgressIndicator()),
                    ),
                    error: (_, _) => _Retry(
                      onRetry: () => ref.invalidate(journalInsightsProvider),
                    ),
                    data: (i) => _InsightsView(insights: i),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Recent entries',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  logs.when(
                    loading: () => const SizedBox.shrink(),
                    error: (_, _) => const SizedBox.shrink(),
                    data: (page) => page.items.isEmpty
                        ? const Padding(
                            padding: EdgeInsets.symmetric(vertical: 16),
                            child: Text('No entries yet.'),
                          )
                        : Column(
                            children: [
                              for (final log in page.items) _LogTile(log: log),
                            ],
                          ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: FilledButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('New check-in'),
            onPressed: () => context.push('/journal/new'),
          ),
        ),
      ),
    );
  }
}

class _InsightsView extends StatelessWidget {
  const _InsightsView({required this.insights});
  final JournalInsights insights;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    if (insights.entries == 0) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            'No check-ins in this period yet. Log your mood to start seeing patterns.',
          ),
        ),
      );
    }
    final mood = insights.moodAvg;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            _Stat(
              label: 'Average mood',
              value: mood == null
                  ? '–'
                  : '${moodLevel(mood.round()).emoji} ${mood.toStringAsFixed(1)}',
            ),
            _Stat(
              label: 'Average sleep',
              value: insights.sleepAvg == null
                  ? '–'
                  : '${insights.sleepAvg!.toStringAsFixed(1)} h',
            ),
            _Stat(label: 'Streak', value: '${insights.streakDays} d'),
          ],
        ),
        const SizedBox(height: 16),
        Text('Mood', style: text.titleSmall),
        TrendBars(
          key: const ValueKey('mood-bars'),
          days: insights.days,
          value: (d) => d.moodAvg,
          max: 5,
          semanticsUnit: 'mood out of 5',
        ),
        const SizedBox(height: 16),
        Text('Sleep (hours)', style: text.titleSmall),
        TrendBars(
          key: const ValueKey('sleep-bars'),
          days: insights.days,
          value: (d) => d.sleepAvg,
          max: 12,
          semanticsUnit: 'hours of sleep',
        ),
        if (insights.topTags.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text('Often on your mind', style: text.titleSmall),
          const SizedBox(height: 4),
          Wrap(
            spacing: 8,
            children: [
              for (final e in insights.topTags.entries)
                Chip(label: Text('${moodTags[e.key] ?? e.key} · ${e.value}')),
            ],
          ),
        ],
      ],
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              Text(value, style: text.titleLarge),
              const SizedBox(height: 2),
              Text(label, style: text.bodySmall, textAlign: TextAlign.center),
            ],
          ),
        ),
      ),
    );
  }
}

class _LogTile extends StatelessWidget {
  const _LogTile({required this.log});
  final MoodLog log;

  @override
  Widget build(BuildContext context) {
    final m = moodLevel(log.moodScore);
    final details = [
      if (log.sleepHours != null) '${log.sleepHours} h sleep',
      if (log.energy != null) 'energy ${log.energy}/5',
      for (final t in log.tags) moodTags[t] ?? t,
    ].join(' · ');
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Text(m.emoji, style: const TextStyle(fontSize: 28)),
      title: Text('${m.label} · ${_when(log.createdAt)}'),
      subtitle: Text(
        [details, log.note ?? ''].where((s) => s.isNotEmpty).join('\n'),
      ),
      isThreeLine: log.note != null && details.isNotEmpty,
    );
  }
}

String _when(DateTime t) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final day = DateTime(t.year, t.month, t.day);
  final hm =
      '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
  final diff = today.difference(day).inDays;
  if (diff == 0) return 'today $hm';
  if (diff == 1) return 'yesterday $hm';
  return '${t.day}/${t.month} $hm';
}

class _Retry extends StatelessWidget {
  const _Retry({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      const Text('Could not load your journal.'),
      TextButton(onPressed: onRetry, child: const Text('Retry')),
    ],
  );
}
