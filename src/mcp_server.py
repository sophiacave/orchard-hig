#!/usr/bin/env python3
"""
orchard-hig MCP server — Apple HIG compliance checker for Claude Code.

Tools:
  hig_check_file   — Check a SwiftUI file against HIG rules
  hig_check_code   — Check SwiftUI code snippet against HIG rules
  hig_suggest       — Get HIG-compliant suggestions for a UI component
  hig_rules         — List all available HIG rules
"""

import json
import sys
import io
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from rules import check_all, format_report, Violation

HIG_RULES = {
    "A1": {"id": "A1", "category": "accessibility", "name": "Missing Accessibility Label",
           "desc": "Interactive elements must have .accessibilityLabel() for VoiceOver users."},
    "A2": {"id": "A2", "category": "accessibility", "name": "Hard-coded Font Size",
           "desc": "Use Dynamic Type text styles (.body, .headline) instead of fixed sizes."},
    "A3": {"id": "A3", "category": "accessibility", "name": "Fixed Frame Dimensions",
           "desc": "Fixed frames may not scale with Dynamic Type. Use @ScaledMetric."},
    "A4": {"id": "A4", "category": "accessibility", "name": "Reduce Motion Not Respected",
           "desc": "Animations must respect the user's Reduce Motion preference."},
    "T1": {"id": "T1", "category": "interaction", "name": "Small Touch Target",
           "desc": "Touch targets must be at least 44x44 points per Apple HIG."},
    "C1": {"id": "C1", "category": "color", "name": "Hard-coded Color",
           "desc": "Use semantic colors for Dark Mode compatibility."},
    "C2": {"id": "C2", "category": "color", "name": "Color-only State Indicator",
           "desc": "Never use color alone to communicate state. Add icons or text."},
    "S1": {"id": "S1", "category": "components", "name": "Deprecated NavigationView",
           "desc": "NavigationView is deprecated. Use NavigationStack or NavigationSplitView."},
    "S2": {"id": "S2", "category": "components", "name": "Direct Alert Usage",
           "desc": "Prefer .alert() view modifier over Alert() for consistent system styling."},
    "S3": {"id": "S3", "category": "components", "name": "Deprecated List Style Syntax",
           "desc": "Use short-form list styles (.grouped) instead of full type names."},
    "S4": {"id": "S4", "category": "components", "name": "Missing Navigation Title",
           "desc": "NavigationStack screens should have .navigationTitle for proper navigation."},
    "L1": {"id": "L1", "category": "layout", "name": "Unsafe Area Ignored",
           "desc": "Only ignore safe area for backgrounds/images, not interactive content."},
    "L2": {"id": "L2", "category": "layout", "name": "Non-standard Spacing",
           "desc": "Use system default padding or multiples of 4/8pt for consistent spacing."},
    "L3": {"id": "L3", "category": "layout", "name": "Fixed Width Without Adaptive Layout",
           "desc": "Multiple fixed widths without GeometryReader may break across device sizes."},
    "D1": {"id": "D1", "category": "color", "name": "UIColor in SwiftUI",
           "desc": "Use SwiftUI Color or Asset Catalog for automatic Dark Mode adaptation."},
    "D2": {"id": "D2", "category": "color", "name": "Hard-coded Background Color",
           "desc": "Use semantic background colors for Dark Mode support."},
    "G1": {"id": "G1", "category": "materials", "name": "Opaque Background on Floating UI",
           "desc": "Use glass materials for sheets, popovers, and floating elements in iOS 26+."},
    "G2": {"id": "G2", "category": "materials", "name": "Custom Toolbar Background",
           "desc": "Let system manage toolbar appearance for Liquid Glass support."},
    "G3": {"id": "G3", "category": "materials", "name": "UIKit Tab Bar Appearance Override",
           "desc": "UITabBar.appearance() overrides system materials. Use SwiftUI modifiers."},
    "I1": {"id": "I1", "category": "interaction", "name": "Destructive Action Without Confirmation",
           "desc": "Destructive actions must have a confirmation dialog before executing."},
    "I2": {"id": "I2", "category": "interaction", "name": "Missing Haptic Feedback",
           "desc": "Significant user actions should include haptic feedback."},
    "P1": {"id": "P1", "category": "privacy", "name": "Privacy Purpose String Needed",
           "desc": "APIs requiring permission need clear Info.plist purpose strings."},
}

COMPONENT_SUGGESTIONS = {
    "button": {
        "code": '''Button(action: { }) {
    Label("Action", systemImage: "star.fill")
}
.buttonStyle(.borderedProminent)
.accessibilityLabel("Perform action")''',
        "notes": "Use Label for icon+text. borderedProminent for primary actions. Always add accessibilityLabel."
    },
    "list": {
        "code": '''List {
    ForEach(items) { item in
        NavigationLink(value: item) {
            HStack {
                Image(systemName: item.icon)
                    .accessibilityHidden(true)
                Text(item.name)
            }
        }
    }
}
.navigationTitle("Items")''',
        "notes": "Use NavigationLink(value:) with NavigationStack. Hide decorative images from VoiceOver."
    },
    "form": {
        "code": '''Form {
    Section("Account") {
        TextField("Email", text: $email)
            .textContentType(.emailAddress)
            .keyboardType(.emailAddress)
            .accessibilityLabel("Email address")
        SecureField("Password", text: $password)
            .textContentType(.password)
            .accessibilityLabel("Password")
    }
}''',
        "notes": "Use textContentType for AutoFill. Add accessibilityLabel for each field."
    },
    "tab": {
        "code": '''TabView {
    HomeView()
        .tabItem {
            Label("Home", systemImage: "house")
        }
    SettingsView()
        .tabItem {
            Label("Settings", systemImage: "gear")
        }
}''',
        "notes": "Use Label for tab items (icon+text). Max 5 tabs. Use .badge() for notifications."
    },
    "alert": {
        "code": '''.alert("Confirm Delete", isPresented: $showAlert) {
    Button("Delete", role: .destructive) { deleteItem() }
    Button("Cancel", role: .cancel) { }
} message: {
    Text("This action cannot be undone.")
}''',
        "notes": "Use .alert() modifier, not Alert(). Use destructive role for dangerous actions."
    },
    "navigation": {
        "code": '''NavigationStack {
    List(items) { item in
        NavigationLink(value: item) {
            ItemRow(item: item)
        }
    }
    .navigationTitle("Items")
    .navigationDestination(for: Item.self) { item in
        ItemDetail(item: item)
    }
}''',
        "notes": "Use NavigationStack (not NavigationView). Use navigationDestination for type-safe navigation."
    },
}


def hig_check_file(file_path: str) -> dict:
    """Check a SwiftUI file against HIG rules."""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    if not path.suffix == ".swift":
        return {"error": "Only .swift files are supported"}

    code = path.read_text()
    violations = check_all(code)
    report = format_report(violations, path.name)

    return {
        "file": str(path),
        "violations": len(violations),
        "report": report,
        "details": [
            {"rule": v.rule_id, "severity": v.severity, "message": v.message,
             "line": v.line, "suggestion": v.suggestion}
            for v in violations
        ]
    }


def hig_check_code(code: str) -> dict:
    """Check a SwiftUI code snippet against HIG rules."""
    violations = check_all(code)
    report = format_report(violations, "snippet")

    return {
        "violations": len(violations),
        "report": report,
        "details": [
            {"rule": v.rule_id, "severity": v.severity, "message": v.message,
             "line": v.line, "suggestion": v.suggestion}
            for v in violations
        ]
    }


def hig_suggest(component: str) -> dict:
    """Get HIG-compliant code suggestion for a UI component."""
    key = component.lower().strip()
    if key in COMPONENT_SUGGESTIONS:
        sug = COMPONENT_SUGGESTIONS[key]
        return {"component": key, "code": sug["code"], "notes": sug["notes"]}

    available = list(COMPONENT_SUGGESTIONS.keys())
    return {"error": f"Unknown component: {component}", "available": available}


# MCP stdio protocol handler
def handle_request(request):
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "orchard-hig", "version": "0.1.0"}
        }

    if method == "tools/list":
        return {"tools": [
            {
                "name": "hig_check_file",
                "description": "Check a SwiftUI .swift file against Apple Human Interface Guidelines. Returns violations with fix suggestions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the .swift file to check"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "hig_check_code",
                "description": "Check a SwiftUI code snippet against Apple HIG rules. Paste code directly.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "SwiftUI code to check"}
                    },
                    "required": ["code"]
                }
            },
            {
                "name": "hig_suggest",
                "description": "Get an HIG-compliant SwiftUI code example for a UI component (button, list, form, tab, alert, navigation).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "component": {"type": "string", "description": "Component type: button, list, form, tab, alert, navigation"}
                    },
                    "required": ["component"]
                }
            },
            {
                "name": "hig_rules",
                "description": "List all available HIG rules that orchard-hig checks for.",
                "inputSchema": {"type": "object", "properties": {}}
            },
        ]}

    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        if tool_name == "hig_check_file":
            result = hig_check_file(args["file_path"])
        elif tool_name == "hig_check_code":
            result = hig_check_code(args["code"])
        elif tool_name == "hig_suggest":
            result = hig_suggest(args["component"])
        elif tool_name == "hig_rules":
            result = {"rules": list(HIG_RULES.values()), "total": len(HIG_RULES)}
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    return {"error": f"Unknown method: {method}"}


def main():
    input_stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    for line in input_stream:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            result = handle_request(request)
            response = {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if "request" in dir() else None,
                "error": {"code": -32603, "message": str(e)}
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
