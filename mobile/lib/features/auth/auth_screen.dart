import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/providers.dart';
import '../../shared/help_sheet.dart';

/// Sign in / sign up with email and password (Supabase Auth).
class AuthScreen extends ConsumerStatefulWidget {
  const AuthScreen({super.key});

  @override
  ConsumerState<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends ConsumerState<AuthScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _signUp = false;
  bool _busy = false;
  String? _message;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _message = null;
    });
    final auth = ref.read(supabaseProvider).auth;
    try {
      if (_signUp) {
        final res = await auth.signUp(
          email: _email.text.trim(),
          password: _password.text,
        );
        if (res.session == null) {
          _message = 'Check your email to confirm your account, then sign in.';
        }
      } else {
        await auth.signInWithPassword(
          email: _email.text.trim(),
          password: _password.text,
        );
      }
      // On success the router reacts to the auth state change.
    } on AuthException catch (e) {
      _message = e.message;
    } catch (_) {
      _message = 'Something went wrong. Check your connection and try again.';
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Scaffold(
      floatingActionButton: const HelpButton(),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text('MH Companion', style: text.headlineMedium),
                    const SizedBox(height: 4),
                    Text(
                      _signUp ? 'Create your account' : 'Welcome back',
                      style: text.titleMedium,
                    ),
                    const SizedBox(height: 24),
                    TextFormField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      autofillHints: const [AutofillHints.email],
                      decoration: const InputDecoration(
                        labelText: 'College email',
                      ),
                      validator: (v) => (v == null || !v.contains('@'))
                          ? 'Enter a valid email'
                          : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _password,
                      obscureText: true,
                      decoration: const InputDecoration(labelText: 'Password'),
                      validator: (v) => (v == null || v.length < 8)
                          ? 'At least 8 characters'
                          : null,
                    ),
                    const SizedBox(height: 20),
                    FilledButton(
                      onPressed: _busy ? null : _submit,
                      child: Text(_signUp ? 'Sign up' : 'Sign in'),
                    ),
                    TextButton(
                      onPressed: _busy
                          ? null
                          : () => setState(() {
                              _signUp = !_signUp;
                              _message = null;
                            }),
                      child: Text(
                        _signUp
                            ? 'Already have an account? Sign in'
                            : 'New here? Create an account',
                      ),
                    ),
                    if (_message != null) ...[
                      const SizedBox(height: 8),
                      Text(_message!, textAlign: TextAlign.center),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
