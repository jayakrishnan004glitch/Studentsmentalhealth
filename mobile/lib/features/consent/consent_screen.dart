import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/providers.dart';
import '../../shared/help_sheet.dart';

class ConsentOption {
  const ConsentOption(
    this.kind,
    this.title,
    this.description, {
    this.required = false,
  });
  final String kind;
  final String title;
  final String description;
  final bool required;
}

const consentOptions = <ConsentOption>[
  ConsentOption(
    'terms',
    'Terms and privacy policy',
    'I understand this app is a supportive screening tool, not a diagnosis '
        'or treatment, and does not replace professional help.',
    required: true,
  ),
  ConsentOption(
    'ai_processing',
    'AI companion chat',
    'My messages are analysed to detect emotion and wellbeing risk, and are '
        'sent without my name to an AI provider to write replies. '
        'Needed for chat.',
  ),
  ConsentOption(
    'camera',
    'Camera check-ins (optional)',
    'A single photo is analysed for facial expression, then discarded. '
        'Images are never stored.',
  ),
  ConsentOption(
    'microphone',
    'Voice check-ins (optional)',
    'A short clip is analysed for tone of voice, then discarded. '
        'Audio is never stored.',
  ),
  ConsentOption(
    'counsellor_contact',
    'Counsellor contact (optional)',
    'If the app detects high risk, the college counsellor may see my '
        'contact details to reach out to me.',
  ),
];

/// Shown before first use and whenever the policy version changes.
/// Every option except the terms can be changed later in Settings.
class ConsentScreen extends ConsumerStatefulWidget {
  const ConsentScreen({
    super.key,
    required this.policyVersion,
    this.initial = const {},
    this.onDone,
  });

  final String policyVersion;
  final Map<String, bool> initial;
  final VoidCallback? onDone;

  @override
  ConsumerState<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends ConsumerState<ConsentScreen> {
  late final Map<String, bool> _choices = {
    for (final o in consentOptions) o.kind: widget.initial[o.kind] ?? false,
  };
  bool _busy = false;
  String? _error;

  bool get _canContinue =>
      consentOptions.where((o) => o.required).every((o) => _choices[o.kind]!);

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(meApiProvider)
          .giveConsents(widget.policyVersion, _choices);
      ref.invalidate(meProvider);
      widget.onDone?.call();
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not save. Please try again.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Your privacy choices')),
      floatingActionButton: const HelpButton(),
      floatingActionButtonLocation: FloatingActionButtonLocation.startFloat,
      body: Column(
        children: [
          const DisclaimerBar(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.only(bottom: 96),
              children: [
                for (final o in consentOptions)
                  SwitchListTile(
                    key: ValueKey('consent-${o.kind}'),
                    title: Text(o.required ? '${o.title} (required)' : o.title),
                    subtitle: Text(o.description),
                    isThreeLine: true,
                    value: _choices[o.kind]!,
                    onChanged: _busy
                        ? null
                        : (v) => setState(() => _choices[o.kind] = v),
                  ),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      _error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
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
            key: const ValueKey('consent-continue'),
            onPressed: _canContinue && !_busy ? _submit : null,
            child: const Text('Continue'),
          ),
        ),
      ),
    );
  }
}
