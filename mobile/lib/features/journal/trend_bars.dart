import 'package:material_ui/material_ui.dart';

import '../../api/journal_api.dart';

/// A small dependency-free bar chart: one bar per day, gaps for empty days.
/// Weekday initials are shown under the bars for ranges up to 7 days.
class TrendBars extends StatelessWidget {
  const TrendBars({
    super.key,
    required this.days,
    required this.value,
    required this.max,
    required this.semanticsUnit,
    this.height = 96,
  });

  final List<DaySummary> days;
  final double? Function(DaySummary) value;
  final double max;
  final String semanticsUnit;
  final double height;

  static const _weekdays = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final showLabels = days.length <= 7;
    final gap = days.length <= 7 ? 8.0 : 2.0;
    final logged = days.where((d) => value(d) != null).toList();
    final summary = logged.isEmpty
        ? 'No data'
        : logged
              .map(
                (d) =>
                    '${d.date.day}/${d.date.month}: '
                    '${value(d)!.toStringAsFixed(1)} $semanticsUnit',
              )
              .join(', ');

    return Semantics(
      label: summary,
      excludeSemantics: true,
      child: Column(
        children: [
          SizedBox(
            height: height,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                for (final d in days)
                  Expanded(
                    child: Padding(
                      padding: EdgeInsets.symmetric(horizontal: gap / 2),
                      child: _bar(d, scheme),
                    ),
                  ),
              ],
            ),
          ),
          if (showLabels)
            Row(
              children: [
                for (final d in days)
                  Expanded(
                    child: Text(
                      _weekdays[d.date.weekday - 1],
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _bar(DaySummary d, ColorScheme scheme) {
    final v = value(d);
    if (v == null) {
      return Container(
        height: 3,
        decoration: BoxDecoration(
          color: scheme.outlineVariant,
          borderRadius: BorderRadius.circular(2),
        ),
      );
    }
    final fraction = (v / max).clamp(0.05, 1.0);
    return Container(
      height: height * fraction,
      decoration: BoxDecoration(
        color: scheme.primary,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
      ),
    );
  }
}
