import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';

import '../../api/me_api.dart';
import '../../core/providers.dart';
import '../../shared/help_sheet.dart';
import '../../shared/mood.dart';
import '../journal/trend_bars.dart';

/// S-01 Home: greeting, quick mood check-in, this week's mood and streak.
/// Chat, questionnaires and resources come in later steps.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key, required this.me});
  final Me me;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final name = me.profile.displayName ?? 'there';
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('MH Companion'),
        actions: [
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(supabaseProvider).auth.signOut(),
          ),
        ],
      ),
      floatingActionButton: const HelpButton(),
      body: Column(
        children: [
          const DisclaimerBar(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
              children: [
                Text('Hi $name', style: text.headlineSmall),
                const SizedBox(height: 4),
                Text('How are you feeling today?', style: text.titleMedium),
                const SizedBox(height: 12),
                MoodPicker(
                  onSelected: (score) =>
                      context.push('/journal/new?mood=$score'),
                ),
                const SizedBox(height: 16),
                const _WeekCard(),
                Card(
                  child: ListTile(
                    key: const ValueKey('open-study'),
                    leading: const Icon(Icons.school_outlined),
                    title: const Text('KTU study material'),
                    subtitle: Text(
                      me.profile.hasStudyProfile
                          ? 'S${me.profile.semester} · ${me.profile.branch} · '
                                '${me.profile.ktuScheme} scheme'
                          : 'Set up your course to see your subjects',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push('/study'),
                  ),
                ),
                const _ComingSoon(
                  Icons.chat_bubble_outline,
                  'Talk to your companion',
                ),
                Card(
                  child: ListTile(
                    key: const ValueKey('open-questionnaires'),
                    leading: const Icon(Icons.assignment_outlined),
                    title: const Text('Check-in questionnaires'),
                    subtitle: const Text('PHQ-9, GAD-7, DASS-21 · 2–5 min'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push('/questionnaires'),
                  ),
                ),
                const _ComingSoon(Icons.menu_book_outlined, 'Resources'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Streak + this week's mood bars; opens the journal.
class _WeekCard extends ConsumerWidget {
  const _WeekCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final insights = ref.watch(journalInsightsProvider(7));
    final text = Theme.of(context).textTheme;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: const ValueKey('open-journal'),
        onTap: () => context.push('/journal'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: insights.when(
            loading: () => const SizedBox(
              height: 72,
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (_, _) => const ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(Icons.insights),
              title: Text('Journal'),
              subtitle: Text('Could not load this week. Tap to open.'),
            ),
            data: (i) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.local_fire_department_outlined),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        i.streakDays == 0
                            ? 'Start a check-in streak today'
                            : '${i.streakDays}-day check-in streak',
                        style: text.titleSmall,
                      ),
                    ),
                    const Icon(Icons.chevron_right),
                  ],
                ),
                const SizedBox(height: 12),
                if (i.entries == 0)
                  Text(
                    'Your mood this week will appear here.',
                    style: text.bodySmall,
                  )
                else ...[
                  TrendBars(
                    days: i.days,
                    value: (d) => d.moodAvg,
                    max: 5,
                    height: 48,
                    semanticsUnit: 'mood out of 5',
                  ),
                  const SizedBox(height: 4),
                  Text('Mood this week', style: text.bodySmall),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ComingSoon extends StatelessWidget {
  const _ComingSoon(this.icon, this.label);
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Card(
    child: ListTile(
      leading: Icon(icon),
      title: Text(label),
      subtitle: const Text('Coming in the next steps'),
      enabled: false,
    ),
  );
}
