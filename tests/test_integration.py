#!/usr/bin/env python3
"""Integration tests for orchard-hig MCP server."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from rules import check_all, format_report, Violation
from mcp_server import handle_request, HIG_RULES

PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def test_rule_coverage():
    """All 22 rules exist and are documented."""
    print("\n--- Rule Coverage ---")
    expected_rules = [
        "A1", "A2", "A3", "A4", "T1", "C1", "C2",
        "S1", "S2", "S3", "S4",
        "L1", "L2", "L3",
        "D1", "D2",
        "G1", "G2", "G3",
        "I1", "I2",
        "P1",
    ]
    check("22 rules defined in HIG_RULES", len(HIG_RULES) >= 22)
    for rule_id in expected_rules:
        check(f"Rule {rule_id} in HIG_RULES", rule_id in HIG_RULES)


def test_accessibility_rules():
    """A1-A4 fire correctly."""
    print("\n--- Accessibility Rules ---")

    # A1: Missing accessibility label
    code = 'Button("Tap") { }\n'
    violations = check_all(code)
    a1 = [v for v in violations if v.rule_id == "A1"]
    check("A1 fires on Button without accessibilityLabel", len(a1) > 0)

    # A1 should NOT fire when label is present
    code = 'Button("Tap") { }\n.accessibilityLabel("Tap button")\n'
    violations = check_all(code)
    a1 = [v for v in violations if v.rule_id == "A1"]
    check("A1 silent when accessibilityLabel present", len(a1) == 0)

    # A2: Hard-coded font size
    code = '.font(.system(size: 16))\n'
    violations = check_all(code)
    a2 = [v for v in violations if v.rule_id == "A2"]
    check("A2 fires on hard-coded font size", len(a2) > 0)

    # A4: Animation without reduce motion
    code = 'withAnimation(.spring()) {\n    show.toggle()\n}\n'
    violations = check_all(code)
    a4 = [v for v in violations if v.rule_id == "A4"]
    check("A4 fires on animation without reduce motion check", len(a4) > 0)


def test_touch_targets():
    """T1 fires on small touch targets."""
    print("\n--- Touch Targets ---")
    code = 'Button("X") { }\n.frame(width: 20, height: 20)\n'
    violations = check_all(code)
    t1 = [v for v in violations if v.rule_id == "T1"]
    check("T1 fires on 20pt touch target", len(t1) > 0)

    code = 'Button("X") { }\n.frame(width: 44, height: 44)\n'
    violations = check_all(code)
    t1 = [v for v in violations if v.rule_id == "T1"]
    check("T1 silent on 44pt touch target", len(t1) == 0)


def test_color_rules():
    """C1-C2, D1-D2 fire correctly."""
    print("\n--- Color Rules ---")

    # C1: Hard-coded color
    code = 'Color(red: 0.5, green: 0.3, blue: 0.1)\n'
    violations = check_all(code)
    c1 = [v for v in violations if v.rule_id == "C1"]
    check("C1 fires on Color(red:green:blue:)", len(c1) > 0)

    # D2: Hard-coded white background
    code = '.background(Color.white)\n'
    violations = check_all(code)
    d2 = [v for v in violations if v.rule_id == "D2"]
    check("D2 fires on .background(Color.white)", len(d2) > 0)


def test_component_rules():
    """S1-S4 fire correctly."""
    print("\n--- Component Rules ---")

    # S1: NavigationView
    code = 'NavigationView {\n    Text("Hello")\n}\n'
    violations = check_all(code)
    s1 = [v for v in violations if v.rule_id == "S1"]
    check("S1 fires on NavigationView", len(s1) > 0)

    # S4: Missing navigation title
    code = 'NavigationStack {\n    List { }\n}\n'
    violations = check_all(code)
    s4 = [v for v in violations if v.rule_id == "S4"]
    check("S4 fires on NavigationStack without navigationTitle", len(s4) > 0)


def test_layout_rules():
    """L1-L3 fire correctly."""
    print("\n--- Layout Rules ---")

    # L1: Ignoring safe area for non-background content
    code = 'Text("Content")\n.ignoresSafeArea()\n'
    violations = check_all(code)
    l1 = [v for v in violations if v.rule_id == "L1"]
    check("L1 fires on ignoresSafeArea without background context", len(l1) > 0)

    # L2: Non-standard padding
    code = '.padding(13)\n'
    violations = check_all(code)
    l2 = [v for v in violations if v.rule_id == "L2"]
    check("L2 fires on non-standard padding(13)", len(l2) > 0)


def test_material_rules():
    """G1-G3 fire correctly."""
    print("\n--- Material Rules ---")

    # G3: UITabBar.appearance
    code = 'TabView {\n}\n.background(Color.red)\nUITabBar.appearance().backgroundColor = .white\n'
    violations = check_all(code)
    g3 = [v for v in violations if v.rule_id == "G3"]
    check("G3 fires on UITabBar.appearance()", len(g3) > 0)


def test_interaction_rules():
    """I1-I2 fire correctly."""
    print("\n--- Interaction Rules ---")

    # I1: Destructive without confirmation
    code = 'Button("Delete", role: .destructive) { deleteItem() }\n'
    violations = check_all(code)
    i1 = [v for v in violations if v.rule_id == "I1"]
    check("I1 fires on destructive action without confirmation", len(i1) > 0)


def test_mcp_protocol():
    """MCP protocol handlers work."""
    print("\n--- MCP Protocol ---")

    # Initialize
    resp = handle_request({"method": "initialize", "id": 1})
    check("initialize returns serverInfo", "serverInfo" in resp)
    check("server name is orchard-hig", resp["serverInfo"]["name"] == "orchard-hig")

    # Tools list
    resp = handle_request({"method": "tools/list", "id": 2})
    tools = resp["tools"]
    tool_names = [t["name"] for t in tools]
    check("4 tools listed", len(tools) == 4)
    check("hig_check_file tool exists", "hig_check_file" in tool_names)
    check("hig_check_code tool exists", "hig_check_code" in tool_names)
    check("hig_suggest tool exists", "hig_suggest" in tool_names)
    check("hig_rules tool exists", "hig_rules" in tool_names)

    # hig_check_code
    resp = handle_request({
        "method": "tools/call",
        "params": {"name": "hig_check_code", "arguments": {"code": 'Button("X") { }'}},
        "id": 3
    })
    result = json.loads(resp["content"][0]["text"])
    check("hig_check_code returns violations count", "violations" in result)

    # hig_suggest
    resp = handle_request({
        "method": "tools/call",
        "params": {"name": "hig_suggest", "arguments": {"component": "button"}},
        "id": 4
    })
    result = json.loads(resp["content"][0]["text"])
    check("hig_suggest returns code for button", "code" in result)

    # hig_rules
    resp = handle_request({
        "method": "tools/call",
        "params": {"name": "hig_rules", "arguments": {}},
        "id": 5
    })
    result = json.loads(resp["content"][0]["text"])
    check("hig_rules returns 22+ rules", result["total"] >= 22)

    # Unknown tool
    resp = handle_request({
        "method": "tools/call",
        "params": {"name": "nonexistent", "arguments": {}},
        "id": 6
    })
    result = json.loads(resp["content"][0]["text"])
    check("unknown tool returns error", "error" in result)


def test_format_report():
    """Report formatting works."""
    print("\n--- Format Report ---")
    violations = [
        Violation("A1", "accessibility", "warning", "Test warning", 1, "Fix it"),
        Violation("C1", "color", "info", "Test info", 5),
    ]
    report = format_report(violations, "test.swift")
    check("report contains filename", "test.swift" in report)
    check("report contains issue count", "2 issue(s)" in report)
    check("report contains summary", "Summary:" in report)

    empty = format_report([], "clean.swift")
    check("empty report says all clear", "All clear" in empty)


if __name__ == "__main__":
    test_rule_coverage()
    test_accessibility_rules()
    test_touch_targets()
    test_color_rules()
    test_component_rules()
    test_layout_rules()
    test_material_rules()
    test_interaction_rules()
    test_mcp_protocol()
    test_format_report()
    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL > 0 else 0)
