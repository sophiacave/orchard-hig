# orchard-hig

**Apple HIG compliance checker for Claude Code.** Checks SwiftUI code against 22 Human Interface Guidelines rules. Zero competitors.

Every AI coding tool generates SwiftUI that violates Apple's design standards. orchard-hig catches violations before your users do.

## Quick Start

Add to `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "orchard-hig": {
      "command": "python3",
      "args": ["/path/to/orchard-hig/src/mcp_server.py"]
    }
  }
}
```

## Tools

| Tool | What It Does |
|------|-------------|
| `hig_check_file` | Check a .swift file against all 22 HIG rules |
| `hig_check_code` | Check a SwiftUI code snippet against HIG rules |
| `hig_suggest` | Get HIG-compliant code examples (button, list, form, tab, alert, navigation) |
| `hig_rules` | List all 22 rules with descriptions |

## Rules (22)

| Rule | Category | What It Checks |
|------|----------|---------------|
| A1 | Accessibility | Missing `.accessibilityLabel()` on interactive elements |
| A2 | Accessibility | Hard-coded font sizes (should use Dynamic Type) |
| A3 | Accessibility | Fixed frame dimensions without `@ScaledMetric` |
| A4 | Accessibility | Animations without Reduce Motion check |
| T1 | Interaction | Touch targets below 44x44pt minimum |
| C1 | Color | Hard-coded colors instead of semantic colors |
| C2 | Color | Color-only state indicators (no icon/text backup) |
| D1 | Color | UIColor in SwiftUI (doesn't auto-adapt to Dark Mode) |
| D2 | Color | Hard-coded white/black backgrounds |
| S1 | Components | Deprecated NavigationView (use NavigationStack) |
| S2 | Components | Direct Alert() usage (use .alert() modifier) |
| S3 | Components | Deprecated list style syntax |
| S4 | Components | Missing NavigationTitle on NavigationStack |
| L1 | Layout | Ignoring safe area for non-background content |
| L2 | Layout | Non-standard spacing values |
| L3 | Layout | Multiple fixed widths without adaptive layout |
| G1 | Materials | Opaque backgrounds where glass materials apply (iOS 26+) |
| G2 | Materials | Custom toolbar backgrounds overriding Liquid Glass |
| G3 | Materials | UITabBar.appearance() overriding system materials |
| I1 | Interaction | Destructive actions without confirmation dialog |
| I2 | Interaction | Missing haptic feedback on significant actions |
| P1 | Privacy | APIs requiring Info.plist purpose strings |

## Example

```
> hig_check_code "Button(\"Tap\") { }.frame(width: 30).font(.system(size: 14)).background(Color.white)"

HIG Check: snippet — 4 issue(s)

  [WARN] A1: Button may need an .accessibilityLabel() modifier
    Fix: Add .accessibilityLabel("descriptive label")

  [WARN] A2: Hard-coded font size (14). Use Dynamic Type text styles.
    Fix: Replace with .font(.body), .font(.headline), etc.

  [WARN] T1: Frame dimension 30pt is below the 44pt minimum touch target.
    Fix: Increase to at least 44x44 points.

  [WARN] D2: Hard-coded white/black background. Won't adapt to Dark Mode.
    Fix: Use Color(.systemBackground) for auto Dark Mode adaptation.

Summary: 0 errors, 4 warnings, 0 info
```

## Testing

```bash
python3 tests/test_integration.py
# 52 tests, 0 failures
```

## Part of Orchard

orchard-hig is part of the Orchard suite — Apple developer MCP tools by [Like One](https://likeone.ai).

- **orchard-hig** — HIG compliance checker (this repo)
- **[orchard-sign](https://github.com/sophiacave/orchard-sign)** — Code signing automation

## License

MIT
