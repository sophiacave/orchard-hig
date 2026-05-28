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

    # S3: Using deprecated List styles
    deprecated_list = re.compile(r'\.listStyle\(\s*(?:GroupedListStyle|InsetGroupedListStyle|PlainListStyle|SidebarListStyle)\s*\(\s*\)\s*\)')
    for i, line in enumerate(lines, 1):
        if deprecated_list.search(line):
            violations.append(Violation(
                rule_id="S3",
                category="components",
                severity="info",
                message=f"Deprecated list style syntax on line {i}. Use the short form.",
                line=i,
                suggestion="Use .listStyle(.grouped), .listStyle(.insetGrouped), etc. instead of the full type name.",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/lists-and-tables"
            ))

    # S4: Missing NavigationTitle on NavigationStack
    if "NavigationStack" in code and ".navigationTitle" not in code:
        violations.append(Violation(
            rule_id="S4",
            category="components",
            severity="warning",
            message="NavigationStack found without .navigationTitle. Screens should have descriptive titles.",
            suggestion="Add .navigationTitle(\"Screen Name\") inside the NavigationStack for proper navigation bar display.",
            hig_link="https://developer.apple.com/design/human-interface-guidelines/navigation-and-search"
        ))

    return violations


def check_layout(code: str, lines: list[str]) -> list[Violation]:
    """Check layout-related HIG rules."""
    violations = []

    # L1: Ignoring safe area without explicit purpose
    for i, line in enumerate(lines, 1):
        if ".ignoresSafeArea" in line or ".edgesIgnoringSafeArea" in line:
            context = "\n".join(lines[max(0, i-3):min(len(lines), i+3)])
            if "background" not in context.lower() and "image" not in context.lower():
                violations.append(Violation(
                    rule_id="L1",
                    category="layout",
                    severity="warning",
                    message=f"ignoresSafeArea on line {i}. Content behind safe area may be clipped or obscured.",
                    line=i,
                    suggestion="Only ignore safe area for backgrounds/images. Interactive content should respect safe areas.",
                    hig_link="https://developer.apple.com/design/human-interface-guidelines/layout"
                ))

    # L2: Hard-coded spacing values instead of system spacing
    spacing_pattern = re.compile(r'\.padding\(\s*(\d+)\s*\)')
    for i, line in enumerate(lines, 1):
        match = spacing_pattern.search(line)
        if match:
            value = int(match.group(1))
            if value not in (0, 4, 8, 16, 20) and value > 2:
                violations.append(Violation(
                    rule_id="L2",
                    category="layout",
                    severity="info",
                    message=f"Non-standard padding value ({value}) on line {i}. Consider using standard spacing.",
                    line=i,
                    suggestion="Use .padding() (system default), .padding(.small), or multiples of 4/8pt for consistent spacing.",
                    hig_link="https://developer.apple.com/design/human-interface-guidelines/layout"
                ))

    # L3: Fixed dimensions without adaptive layout
    if ".frame(width:" in code and "GeometryReader" not in code and ".containerRelativeFrame" not in code:
        fixed_count = code.count(".frame(width:")
        if fixed_count >= 3:
            violations.append(Violation(
                rule_id="L3",
                category="layout",
                severity="warning",
                message=f"Multiple fixed-width frames ({fixed_count}) without adaptive layout. May not work across device sizes.",
                suggestion="Use GeometryReader, .containerRelativeFrame, or relative sizing for responsive layouts.",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/layout"
            ))

    return violations


def check_dark_mode(code: str, lines: list[str]) -> list[Violation]:
    """Check Dark Mode support rules."""
    violations = []

    # D1: UIColor usage in SwiftUI (doesn't auto-adapt to Dark Mode)
    for i, line in enumerate(lines, 1):
        if "UIColor(" in line and "Color(" not in line:
            violations.append(Violation(
                rule_id="D1",
                category="color",
                severity="warning",
                message=f"UIColor on line {i} in SwiftUI context. UIColor may not adapt to Dark Mode automatically.",
                line=i,
                suggestion="Use SwiftUI Color(.label), Color(.systemBackground), or define adaptive colors in Asset Catalog.",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/dark-mode"
            ))

    # D2: White/black backgrounds without colorScheme awareness
    hardcoded_bg = re.compile(r'\.background\(\s*(?:Color\.white|Color\.black|\.white|\.black)\s*\)')
    for i, line in enumerate(lines, 1):
        if hardcoded_bg.search(line):
            violations.append(Violation(
                rule_id="D2",
                category="color",
                severity="warning",
                message=f"Hard-coded white/black background on line {i}. Won't adapt to Dark Mode.",
                line=i,
                suggestion="Use Color(.systemBackground) or Color(.secondarySystemBackground) for auto Dark Mode adaptation.",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/dark-mode"
            ))

    return violations


def check_materials(code: str, lines: list[str]) -> list[Violation]:
    """Check Liquid Glass and material usage (iOS 26+/macOS 26+)."""
    violations = []

    # G1: Opaque backgrounds on floating elements where glass materials are recommended
    floating_patterns = [".sheet(", ".popover(", ".toolbar", "TabView"]
    has_floating = any(p in code for p in floating_patterns)
    opaque_bg = re.compile(r'\.background\(\s*Color\.\w+\s*\)')

    if has_floating:
        for i, line in enumerate(lines, 1):
            if opaque_bg.search(line):
                context = "\n".join(lines[max(0, i-5):min(len(lines), i+3)])
                if any(p in context for p in floating_patterns):
                    violations.append(Violation(
                        rule_id="G1",
                        category="materials",
                        severity="info",
                        message=f"Opaque background near floating element on line {i}. Consider glass materials for iOS 26+.",
                        line=i,
                        suggestion="Use .glassEffect or .background(.regularMaterial) for sheets, popovers, and floating UI in iOS 26+.",
                        hig_link="https://developer.apple.com/design/human-interface-guidelines/materials"
                    ))

    # G2: Custom toolbar backgrounds that override system materials
    for i, line in enumerate(lines, 1):
        if ".toolbarBackground(" in line and ".visible" in line:
            violations.append(Violation(
                rule_id="G2",
                category="materials",
                severity="info",
                message=f"Custom toolbar background on line {i}. System toolbar materials adapt to Liquid Glass automatically.",
                line=i,
                suggestion="Let system manage toolbar appearance for automatic Liquid Glass support in iOS 26+. Remove .toolbarBackground if not essential.",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/materials"
            ))

    # G3: Tab bar customization that may conflict with glass tab bars
    if "TabView" in code and ".background(" in code:
        for i, line in enumerate(lines, 1):
            if "UITabBar.appearance()" in line:
                violations.append(Violation(
                    rule_id="G3",
                    category="materials",
                    severity="warning",
                    message=f"UITabBar.appearance() on line {i}. Global tab bar appearance overrides system materials.",
                    line=i,
                    suggestion="Use SwiftUI tab bar modifiers instead of UIKit appearance proxies for proper Liquid Glass support.",
                    hig_link="https://developer.apple.com/design/human-interface-guidelines/tab-bars"
                ))

    return violations


def check_interaction(code: str, lines: list[str]) -> list[Violation]:
    """Check interaction and feedback rules."""
    violations = []

    # I1: Destructive actions without confirmation
    if ".destructive" in code and ".confirmationDialog" not in code and ".alert(" not in code:
        violations.append(Violation(
            rule_id="I1",
            category="interaction",
            severity="warning",
            message="Destructive action found without confirmation dialog.",
            suggestion="Add .confirmationDialog() before performing destructive actions (delete, remove, discard).",
            hig_link="https://developer.apple.com/design/human-interface-guidelines/alerts"
        ))

    # I2: Missing haptic feedback on significant interactions
    has_significant_action = any(kw in code for kw in [".onSubmit", "Task {", ".refreshable"])
    has_haptics = "UIImpactFeedbackGenerator" in code or "UINotificationFeedbackGenerator" in code or ".sensoryFeedback" in code
    if has_significant_action and not has_haptics:
        violations.append(Violation(
            rule_id="I2",
            category="interaction",
            severity="info",
            message="Significant user actions without haptic feedback.",
            suggestion="Add .sensoryFeedback(.success, trigger:) or UIImpactFeedbackGenerator for form submissions and refresh actions.",
            hig_link="https://developer.apple.com/design/human-interface-guidelines/playing-haptics"
        ))

    return violations


def check_privacy(code: str, lines: list[str]) -> list[Violation]:
    """Check privacy and permission rules."""
    violations = []

    # P1: Camera/photo/location usage patterns without corresponding purpose strings check
    capability_hints = {
        "AVCaptureSession": ("camera", "NSCameraUsageDescription"),
        "CLLocationManager": ("location", "NSLocationWhenInUseUsageDescription"),
        "PHPhotoLibrary": ("photos", "NSPhotoLibraryUsageDescription"),
        "UNUserNotificationCenter": ("notifications", "No purpose string needed but explain value to user"),
        "HealthKit": ("health", "NSHealthShareUsageDescription"),
        "CMMotionManager": ("motion", "NSMotionUsageDescription"),
    }

    for api, (capability, plist_key) in capability_hints.items():
        if api in code:
            violations.append(Violation(
                rule_id="P1",
                category="privacy",
                severity="info",
                message=f"{api} usage detected. Ensure {plist_key} is set in Info.plist with a clear, specific description.",
                suggestion=f"Add {plist_key} to Info.plist explaining WHY {capability} access is needed (not just what).",
                hig_link="https://developer.apple.com/design/human-interface-guidelines/privacy"
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
    violations.extend(check_layout(code, lines))
    violations.extend(check_dark_mode(code, lines))
    violations.extend(check_materials(code, lines))
    violations.extend(check_interaction(code, lines))
    violations.extend(check_privacy(code, lines))
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
