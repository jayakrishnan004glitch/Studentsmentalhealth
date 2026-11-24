import 'package:material_ui/material_ui.dart';

/// Mood scale shared by the home check-in, the log screen and the journal.
class MoodLevel {
  const MoodLevel(this.score, this.emoji, this.label);
  final int score;
  final String emoji;
  final String label;
}

const moodLevels = <MoodLevel>[
  MoodLevel(1, '😞', 'Very low'),
  MoodLevel(2, '🙁', 'Low'),
  MoodLevel(3, '😐', 'Okay'),
  MoodLevel(4, '🙂', 'Good'),
  MoodLevel(5, '😄', 'Great'),
];

MoodLevel moodLevel(int score) => moodLevels[(score.clamp(1, 5)) - 1];

/// Must match MoodTag in backend/app/schemas/journal.py.
const moodTags = <String, String>{
  'exams': 'Exams',
  'assignments': 'Assignments',
  'classes': 'Classes',
  'placements': 'Placements',
  'family': 'Family',
  'friends': 'Friends',
  'relationship': 'Relationship',
  'health': 'Health',
  'sleep': 'Sleep',
  'money': 'Money',
  'homesick': 'Homesick',
  'other': 'Other',
};

/// Five tappable mood faces. [selected] highlights one of them.
class MoodPicker extends StatelessWidget {
  const MoodPicker({super.key, required this.onSelected, this.selected});

  final ValueChanged<int> onSelected;
  final int? selected;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        for (final m in moodLevels)
          Semantics(
            button: true,
            selected: selected == m.score,
            label: 'Mood: ${m.label}',
            child: InkWell(
              key: ValueKey('mood-${m.score}'),
              borderRadius: BorderRadius.circular(16),
              onTap: () => onSelected(m.score),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  color: selected == m.score ? scheme.primaryContainer : null,
                ),
                child: Column(
                  children: [
                    ExcludeSemantics(
                      child: Text(
                        m.emoji,
                        style: const TextStyle(fontSize: 32),
                      ),
                    ),
                    const SizedBox(height: 2),
                    ExcludeSemantics(
                      child: Text(
                        m.label,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}
