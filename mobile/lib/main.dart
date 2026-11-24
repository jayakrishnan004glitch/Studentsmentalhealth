import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'core/config.dart';
import 'core/router.dart';
import 'core/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (!AppConfig.isConfigured) {
    runApp(const _MissingConfigApp());
    return;
  }
  await Supabase.initialize(
    url: AppConfig.supabaseUrl,
    publishableKey: AppConfig.supabasePublishableKey,
  );
  runApp(const ProviderScope(child: MhCompanionApp()));
}

class MhCompanionApp extends ConsumerWidget {
  const MhCompanionApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'MH Companion',
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      routerConfig: ref.watch(routerProvider),
      debugShowCheckedModeBanner: false,
    );
  }
}

class _MissingConfigApp extends StatelessWidget {
  const _MissingConfigApp();

  @override
  Widget build(BuildContext context) => const MaterialApp(
    home: Scaffold(
      body: Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'Missing configuration.\nRun with --dart-define-from-file=env/dev.json '
            '(see mobile/README.md).',
            textAlign: TextAlign.center,
          ),
        ),
      ),
    ),
  );
}
