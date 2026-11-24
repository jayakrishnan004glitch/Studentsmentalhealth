import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:mh_companion/api/me_api.dart';
import 'package:mh_companion/core/providers.dart';
import 'package:mh_companion/features/consent/consent_screen.dart';
import 'package:mh_companion/shared/help_sheet.dart';

class FakeMeApi implements MeApi {
  String? sentPolicy;
  Map<String, bool>? sentItems;
  bool fail = false;

  @override
  Future<Me> getMe() => throw UnimplementedError();

  @override
  Future<Me> updateProfile(Map<String, Object?> changes) =>
      throw UnimplementedError();

  @override
  Future<Me> giveConsents(String policyVersion, Map<String, bool> items) async {
    if (fail) throw Exception('network');
    sentPolicy = policyVersion;
    sentItems = Map.of(items);
    return Me(
      profile: Profile(id: 'u1', role: 'student', pseudonym: 'ABCD1234'),
      consents: items,
      currentPolicyVersion: policyVersion,
      needsConsent: false,
    );
  }
}

Future<void> pumpConsent(
  WidgetTester tester,
  FakeMeApi api, {
  VoidCallback? onDone,
}) {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  return tester.pumpWidget(
    ProviderScope(
      overrides: [meApiProvider.overrideWithValue(api)],
      child: MaterialApp(
        home: ConsentScreen(policyVersion: 'v1', onDone: onDone),
      ),
    ),
  );
}

FilledButton continueButton(WidgetTester tester) =>
    tester.widget<FilledButton>(find.byKey(const ValueKey('consent-continue')));

void main() {
  testWidgets('Continue is disabled until the terms are accepted', (
    tester,
  ) async {
    await pumpConsent(tester, FakeMeApi());
    expect(continueButton(tester).onPressed, isNull);

    // Optional consents alone are not enough.
    await tester.tap(find.byKey(const ValueKey('consent-camera')));
    await tester.pump();
    expect(continueButton(tester).onPressed, isNull);

    await tester.tap(find.byKey(const ValueKey('consent-terms')));
    await tester.pump();
    expect(continueButton(tester).onPressed, isNotNull);
  });

  testWidgets('Submitting sends every choice with the policy version', (
    tester,
  ) async {
    final api = FakeMeApi();
    var done = false;
    await pumpConsent(tester, api, onDone: () => done = true);

    await tester.tap(find.byKey(const ValueKey('consent-terms')));
    await tester.tap(find.byKey(const ValueKey('consent-ai_processing')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('consent-continue')));
    await tester.pumpAndSettle();

    expect(done, isTrue);
    expect(api.sentPolicy, 'v1');
    expect(api.sentItems, {
      'terms': true,
      'ai_processing': true,
      'camera': false,
      'microphone': false,
      'counsellor_contact': false,
    });
  });

  testWidgets('Shows an error when saving fails', (tester) async {
    final api = FakeMeApi()..fail = true;
    await pumpConsent(tester, api);
    await tester.tap(find.byKey(const ValueKey('consent-terms')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('consent-continue')));
    await tester.pumpAndSettle();
    expect(find.text('Could not save. Please try again.'), findsOneWidget);
  });

  testWidgets('Disclaimer and help button are always visible', (tester) async {
    await pumpConsent(tester, FakeMeApi());
    expect(find.byType(DisclaimerBar), findsOneWidget);
    expect(find.text('Get help now'), findsOneWidget);
  });
}
