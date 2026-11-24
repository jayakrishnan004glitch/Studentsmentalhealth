import 'package:material_ui/material_ui.dart';

/// Calm, low-arousal palette. Red is reserved for SOS / help actions.
class AppTheme {
  static const seed = Color(0xFF3F8F87); // soft teal
  static const sos = Color(0xFFC62828);

  static ThemeData light() => ThemeData(
    colorScheme: ColorScheme.fromSeed(seedColor: seed),
    scaffoldBackgroundColor: const Color(0xFFFAF8F5),
    inputDecorationTheme: const InputDecorationTheme(
      border: OutlineInputBorder(),
    ),
  );

  static ThemeData dark() => ThemeData(
    colorScheme: ColorScheme.fromSeed(
      seedColor: seed,
      brightness: Brightness.dark,
    ),
    inputDecorationTheme: const InputDecorationTheme(
      border: OutlineInputBorder(),
    ),
  );
}
