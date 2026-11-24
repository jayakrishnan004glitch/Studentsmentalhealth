import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:material_ui/material_ui.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../features/auth/auth_screen.dart';
import '../features/consent/consent_screen.dart';
import '../features/home/home_screen.dart';
import '../features/journal/journal_screen.dart';
import '../features/journal/mood_log_screen.dart';
import '../features/questionnaires/questionnaire_flow_screen.dart';
import '../features/questionnaires/questionnaire_list_screen.dart';
import '../features/study/study_screen.dart';
import '../features/study/study_setup_screen.dart';
import '../features/study/subject_screen.dart';
import 'providers.dart';

/// Re-runs the router's redirect whenever the Supabase session changes.
class _AuthRefresh extends ChangeNotifier {
  _AuthRefresh(Stream<AuthState> stream) {
    _sub = stream.listen((_) => notifyListeners());
  }
  late final StreamSubscription<AuthState> _sub;

  @override
  void dispose() {
    _sub.cancel();
    super.dispose();
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(supabaseProvider).auth;
  final refresh = _AuthRefresh(auth.onAuthStateChange);
  ref.onDispose(refresh.dispose);

  return GoRouter(
    initialLocation: '/',
    refreshListenable: refresh,
    redirect: (context, state) {
      final signedIn = auth.currentSession != null;
      final onAuth = state.matchedLocation == '/auth';
      if (!signedIn) return onAuth ? null : '/auth';
      if (onAuth) {
        ref.invalidate(meProvider);
        return '/';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/auth', builder: (_, _) => const AuthScreen()),
      GoRoute(path: '/', builder: (_, _) => const StartGate()),
      GoRoute(path: '/journal', builder: (_, _) => const JournalScreen()),
      GoRoute(
        path: '/journal/new',
        builder: (_, state) => MoodLogScreen(
          initialMood: int.tryParse(state.uri.queryParameters['mood'] ?? ''),
        ),
      ),
      GoRoute(
        path: '/questionnaires',
        builder: (_, _) => const QuestionnaireListScreen(),
      ),
      GoRoute(
        path: '/questionnaires/:instrument',
        builder: (_, state) => QuestionnaireFlowScreen(
          instrument: state.pathParameters['instrument']!,
        ),
      ),
      GoRoute(path: '/study', builder: (_, _) => const StudyScreen()),
      GoRoute(
        path: '/study/setup',
        builder: (_, _) => const StudySetupScreen(),
      ),
      GoRoute(
        path: '/study/subjects/:id',
        builder: (_, state) =>
            SubjectScreen(subjectId: int.parse(state.pathParameters['id']!)),
      ),
    ],
  );
});

/// Loads the profile and shows consent (if needed) or home.
class StartGate extends ConsumerWidget {
  const StartGate({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final me = ref.watch(meProvider);
    return me.when(
      loading: () =>
          const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (_, _) => Scaffold(
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Could not reach the server.'),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () => ref.invalidate(meProvider),
                child: const Text('Retry'),
              ),
              TextButton(
                onPressed: () => ref.read(supabaseProvider).auth.signOut(),
                child: const Text('Sign out'),
              ),
            ],
          ),
        ),
      ),
      data: (me) => me.needsConsent
          ? ConsentScreen(
              policyVersion: me.currentPolicyVersion,
              initial: me.consents,
            )
          : HomeScreen(me: me),
    );
  }
}
