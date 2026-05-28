#!/usr/bin/env python3
"""
orchard-hig rules engine — Checks SwiftUI code against Apple HIG.

Rules are organized by category:
  - accessibility: Dynamic Type, VoiceOver, contrast, touch targets
  - components: System component usage, custom vs standard
  - layout: Safe area, spacing, responsive design
  - interaction: Touch targets, gestures, feedback
  - color: Contrast ratios, color-independent states, Dark Mode
"""

import re
from dataclasses import dataclass, field


@dataclass
class Violation:
    rule_id: str
    category: str
    severity: str  # error, warning, info
    message: str
    line: int = 0
    suggestion: str = ""
    hig_link: str = ""


def check_accessibility(code: str, lines: list[str]) -> list[Violation]:
    """Check accessibility-related HIG rules."""
    violations = []

    # A1: Missing accessibility labels on interactive elements
    interactive_patterns = [
        (r'Button\s*\(', "Button"),
        (r'NavigationLink\s*\(', "NavigationLink"),
        (r'Toggle\s*\(', "Toggle"),
        (r'Slider\s*\(', "Slider"),
        (r'Stepper\s*\(', "Stepper"),
        (r'Picker\s*\(', "Picker"),
        (r'DatePicker\s*\(', "DatePicker"),
        (r'TextField\s*\(', "TextField"),
        (r'SecureField\s*\(', "SecureField"),
    ]

    for i, line in enumerate(lines, 1):
        for pattern, element in interactive_patterns:
            if re.search(pattern, line):
                # Check if accessibilityLabel is nearby (within 5 lines)
                context = "\n".join(lines[max(0, i-1):min(len(lines), i+5)])
                if ".accessibilityLabel" not in context and ".accessibility(label:" not in context:
                    violations.append(Violation(
                        rule_id="A1",
                        category="accessibility",
                        severity="warning",
                        message=f"{element} on line {i} may need an .accessibilityLabel() modifier",
                        line=i,
                        suggestion=f'Add .accessibilityLabel("descriptive label") to the {element}',
                        hig_link="https://developer.apple.com/design/human-interface-guidelines/accessibility"
                    ))

    # A2: Hard-coded font sizes (should use Dynamic Type)
    font_size_pattern = re.compile(r'\.font\(\s*\.system\(\s*size:\s*(\d+)')
    for i, line in enumerate(lines, 1):
        match = font_size_pattern.search(line)
        if match:
            violations.append(Violation(
                rule_id="A2",
                category="accessibility",
                severity="warning",
                message=f"Hard-coded font size ({match.group(1)}) on line {i}. Use Dynamic Type text styles instead.",
                line=i,
                suggestion="Replace .font(.system(size: N)) with .font(.body), .font(.headline), etc.",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/typography"
            ))

    # A3: Missing .dynamicTypeSize support
    if "Text(" in code and "@ScaledMetric" not in code and ".dynamicTypeSize" not in code:
        if ".frame(height:" in code or ".frame(width:" in code:
            violations.append(Violation(
                rule_id="A3",
                category="accessibility",
                severity="info",
                message="Fixed frame dimensions may not scale with Dynamic Type. Consider using @ScaledMetric.",
                suggestion="Use @ScaledMetric var size: CGFloat = 44 for dimensions that should scale with text size.",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/typography"
            ))

    # A4: Reduce Motion not respected
    animation_patterns = [".animation(", "withAnimation(", ".transition("]
    has_animation = any(p in code for p in animation_patterns)
    has_reduce_motion = "UIAccessibility.isReduceMotionEnabled" in code or "accessibilityReduceMotion" in code or "@Environment(\\.accessibilityReduceMotion)" in code
    if has_animation and not has_reduce_motion:
        violations.append(Violation(
            rule_id="A4",
            category="accessibility",
            severity="warning",
            message="Animations detected but Reduce Motion preference not checked.",
            suggestion="Add @Environment(\\.accessibilityReduceMotion) var reduceMotion and conditionally disable animations.",
            hig_link="https://developer.apple.com/design/human-interface-guidelines/motion"
        ))

    return violations


def check_touch_targets(code: str, lines: list[str]) -> list[Violation]:
    """Check touch target size compliance (minimum 44x44 points)."""
    violations = []

    frame_pattern = re.compile(r'\.frame\(\s*(?:width|height)\s*:\s*(\d+)')
    for i, line in enumerate(lines, 1):
        matches = frame_pattern.findall(line)
        for size_str in matches:
            size = int(size_str)
            if size < 44 and ("Button" in code or "onTapGesture" in code):
                violations.append(Violation(
                    rule_id="T1",
                    category="interaction",
                    severity="warning",
                    message=f"Frame dimension {size}pt on line {i} is below the 44pt minimum touch target.",
                    line=i,
                    suggestion="Increase to at least 44x44 points, or use .contentShape(Rectangle()) with adequate padding.",
                    hig_link="https://developer.apple.com/design/human-interface-guidelines/buttons"
                ))

    return violations


def check_color_usage(code: str, lines: list[str]) -> list[Violation]:
    """Check color-related HIG rules."""
    violations = []

    # C1: Hard-coded colors instead of semantic colors
    hardcoded_colors = re.compile(r'Color\(\s*(?:red|green|blue|#|\.init\(red:)')
    for i, line in enumerate(lines, 1):
        if hardcoded_colors.search(line):
            violations.append(Violation(
                rule_id="C1",
                category="color",
                severity="info",
                message=f"Hard-coded color on line {i}. Consider using semantic colors for Dark Mode support.",
                line=i,
                suggestion="Use Color.primary, Color.secondary, Color.accentColor, or define colors in Asset Catalog.",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/color"
            ))

    # C2: Color alone used for state (no icon/text backup)
    if re.search(r'\.foregroundColor\(.*?(\.red|\.green)', code):
        if ".symbolVariant" not in code and "Image(systemName:" not in code:
            violations.append(Violation(
                rule_id="C2",
                category="color",
                severity="warning",
                message="Color may be used alone to indicate state. Add icons or text for color-blind users.",
                suggestion="Pair color changes with SF Symbols or text labels (e.g., checkmark.circle for success).",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/color"
            ))

    return violations


def check_components(code: str, lines: list[str]) -> list[Violation]:
    """Check component usage against HIG recommendations."""
    violations = []

    # S1: Custom navigation instead of NavigationStack
    if ("NavigationView" in code) and ("NavigationStack" not in code):
        for i, line in enumerate(lines, 1):
            if "NavigationView" in line:
                violations.append(Violation(
                    rule_id="S1",
                    category="components",
                    severity="warning",
                    message=f"NavigationView on line {i} is deprecated. Use NavigationStack or NavigationSplitView.",
                    line=i,
                    suggestion="Replace NavigationView with NavigationStack (iOS 16+) or NavigationSplitView.",
                    hig_link="https://developer.apple.com/design/human-interface-guidelines/navigation-and-search"
                ))

    # S2: Custom alert instead of system alert
    if ".alert(" not in code and "Alert(" in code:
        violations.append(Violation(
            rule_id="S2",
            category="components",
            severity="info",
            message="Using Alert() directly. Prefer the .alert() view modifier for standard alert presentation.",
            suggestion="Use .alert(title, isPresented:) modifier instead of Alert() for consistent system styling.",
            hig_link="https://developer.apple.com/design/human-interface-guidelines/alerts"
        ))

    return violations


def check_all(code: str) -> list[Violation]:
    """Run all HIG checks on SwiftUI code."""
    lines = code.split("\n")
    violations = []
    violations.extend(check_accessibility(code, lines))
    violations.extend(check_touch_targets(code, lines))
    violations.extend(check_color_usage(code, lines))
    violations.extend(check_components(code, lines))
    return sorted(violations, key=lambda v: ("error", "warning", "info").index(v.severity))


def format_report(violations: list[Violation], filename: str = "") -> str:
    """Format violations into a readable report."""
    if not violations:
        return f"HIG Check: {filename or 'code'} — No violations found. All clear!"

    header = f"HIG Check: {filename or 'code'} — {len(violations)} issue(s)\n"
    lines = [header]

    by_severity = {"error": [], "warning": [], "info": []}
    for v in violations:
        by_severity[v.severity].append(v)

    icons = {"error": "ERROR", "warning": "WARN", "info": "INFO"}

    for sev in ["error", "warning", "info"]:
        for v in by_severity[sev]:
            line_info = f" (line {v.line})" if v.line else ""
            lines.append(f"  [{icons[sev]}] {v.rule_id}: {v.message}")
            if v.suggestion:
                lines.append(f"    Fix: {v.suggestion}")
            if v.hig_link:
                lines.append(f"    Ref: {v.hig_link}")
            lines.append("")

    summary = f"Summary: {len(by_severity['error'])} errors, {len(by_severity['warning'])} warnings, {len(by_severity['info'])} info"
    lines.append(summary)

    return "\n".join(lines)
