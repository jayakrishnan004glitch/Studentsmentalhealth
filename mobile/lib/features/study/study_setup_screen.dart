import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import '../../core/providers.dart';

/// Pick KTU scheme, branch and semester (stored on the profile).
class StudySetupScreen extends ConsumerStatefulWidget {
  const StudySetupScreen({super.key, this.onSaved});
  final VoidCallback? onSaved;

  @override
  ConsumerState<StudySetupScreen> createState() => _StudySetupScreenState();
}

class _StudySetupScreenState extends ConsumerState<StudySetupScreen> {
  String? _scheme;
  String? _branch;
  int? _semester;
  bool _initialised = false;
  bool _busy = false;
  String? _error;

  bool get _complete => _scheme != null && _branch != null && _semester != null;

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(meApiProvider).updateProfile({
        'ktu_scheme': _scheme,
        'branch': _branch,
        'semester': _semester,
      });
      ref.invalidate(meProvider);
      ref.invalidate(subjectsProvider);
      if (!mounted) return;
      if (widget.onSaved != null) {
        widget.onSaved!();
      } else {
        Navigator.of(context).maybePop();
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not save. Please try again.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final catalog = ref.watch(studyCatalogProvider);
    final me = ref.watch(meProvider).value;
    if (!_initialised && me != null) {
      _initialised = true;
      _scheme = me.profile.ktuScheme;
      _branch = me.profile.branch;
      _semester = me.profile.semester;
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Your course')),
      body: catalog.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, _) => Center(
          child: TextButton(
            onPressed: () => ref.invalidate(studyCatalogProvider),
            child: const Text('Could not load. Retry'),
          ),
        ),
        data: (c) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Text(
              'We use this to show the study material for your KTU subjects.',
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              key: const ValueKey('scheme'),
              initialValue: _scheme,
              decoration: const InputDecoration(labelText: 'KTU scheme'),
              items: [
                for (final s in c.schemes)
                  DropdownMenuItem(value: s.code, child: Text(s.name)),
              ],
              onChanged: (v) => setState(() => _scheme = v),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              key: const ValueKey('branch'),
              initialValue: _branch,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Branch'),
              items: [
                for (final b in c.branches)
                  DropdownMenuItem(
                    value: b.code,
                    child: Text(
                      '${b.name} (${b.code})',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: (v) => setState(() => _branch = v),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<int>(
              key: const ValueKey('semester'),
              initialValue: _semester,
              decoration: const InputDecoration(labelText: 'Current semester'),
              items: [
                for (final s in c.semesters)
                  DropdownMenuItem(value: s, child: Text('S$s')),
              ],
              onChanged: (v) => setState(() => _semester = v),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            const SizedBox(height: 24),
            FilledButton(
              key: const ValueKey('save-course'),
              onPressed: _complete && !_busy ? _save : null,
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }
}
