import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../api/support.dart';
import '../core/helplines.dart';
import '../core/providers.dart';
import '../core/theme.dart';

/// "Get help now" button shown on every student screen.
class HelpButton extends StatelessWidget {
  const HelpButton({super.key});

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton.extended(
      heroTag: 'help',
      backgroundColor: AppTheme.sos,
      foregroundColor: Colors.white,
      icon: const Icon(Icons.support_agent),
      label: const Text('Get help now'),
      onPressed: () => showHelpSheet(context),
    );
  }
}

Future<void> showHelpSheet(BuildContext context) {
  return showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (context) => SafeArea(
      child: ListView(
        shrinkWrap: true,
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          Text(
            "You're not alone. Talk to someone now:",
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          const HelplineTiles(),
        ],
      ),
    ),
  );
}

/// Helplines with tap-to-call.
class HelplineTiles extends ConsumerWidget {
  const HelplineTiles({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Column(
    children: [
      for (final h in helplines)
        ListTile(
          key: ValueKey('call-${h.phone}'),
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.phone),
          title: Text('${h.name}: ${h.phone}'),
          subtitle: Text(h.note),
          trailing: const Icon(Icons.call),
          onTap: () async {
            try {
              await ref.read(linkOpenerProvider)(
                Uri(scheme: 'tel', path: h.phone),
              );
            } catch (_) {
              // No dialer (e.g. desktop web): the number is visible to copy.
            }
          },
        ),
    ],
  );
}

/// Shows a support message from the API. "urgent" = crisis card with
/// helplines (S-03); "suggest" = a gentle nudge.
Future<void> showSupportSheet(BuildContext context, Support support) {
  return showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    isDismissible: !support.isUrgent,
    builder: (context) {
      final text = Theme.of(context).textTheme;
      return SafeArea(
        child: ListView(
          key: const ValueKey('support-sheet'),
          shrinkWrap: true,
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          children: [
            Text(support.title, style: text.headlineSmall),
            const SizedBox(height: 8),
            Text(support.message, style: text.bodyLarge),
            const SizedBox(height: 16),
            const HelplineTiles(),
            const SizedBox(height: 8),
            FilledButton.tonal(
              key: const ValueKey('support-close'),
              onPressed: () => Navigator.of(context).pop(),
              child: Text(support.isUrgent ? 'I have seen this' : 'Close'),
            ),
          ],
        ),
      );
    },
  );
}

/// The "not a replacement for professional help" notice.
class DisclaimerBar extends StatelessWidget {
  const DisclaimerBar({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      color: scheme.secondaryContainer,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Text(
        'This app supports your wellbeing. It does not replace professional help.',
        style: TextStyle(color: scheme.onSecondaryContainer, fontSize: 13),
      ),
    );
  }
}
