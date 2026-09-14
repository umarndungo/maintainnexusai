import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// IBM Plex Mono text for technical data only — equipment IDs,
/// timestamps, risk scores. Never used for UI labels or decoration
/// (spec, "Type": "used only for technical data ... never for UI
/// labels or decoration").
class MonoText extends StatelessWidget {
  const MonoText(this.data, {super.key, this.fontSize, this.fontWeight, this.color});

  final String data;
  final double? fontSize;
  final FontWeight? fontWeight;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Text(
      data,
      style: AppTheme.monoTextStyle(context, fontSize: fontSize, fontWeight: fontWeight, color: color),
    );
  }
}
