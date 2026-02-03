## Usage: python lint_switch_config.py <config.txt>

import re
import sys
from ciscoconfparse import CiscoConfParse

PARKING_VLAN = "999"

UNUSED_DESC_PATTERNS = [
    r"\bUNUSED\b",
    r"\bNOT\s*IN\s*USE\b",
    r"\bSPARE\b",
]

def normalize_lines(raw_text: str) -> list[str]:
    """
    Normalize config text to improve parsing:
    - Convert non-breaking spaces to normal spaces
    - Strip trailing whitespace
    """
    raw_text = raw_text.replace("\xa0", " ")
    return [line.rstrip("\r\n") for line in raw_text.splitlines()]

def has_child(intf_obj, child_regex):
    return bool(intf_obj.re_search_children(child_regex))

def desc_text(intf_obj):
    # Look for " description ...." as a child line
    for child in intf_obj.children:
        m = re.match(r"^\s*description\s+(.+)$", child.text)
        if m:
            return m.group(1)
    return ""

def matches_any_pattern(text, patterns):
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

def is_access_port(intf_obj):
    return (
        has_child(intf_obj, r"^\s*switchport\s+mode\s+access\s*$")
        or has_child(intf_obj, r"^\s*switchport\s+access\s+vlan\s+\d+\s*$")
    )

def is_unused_port(intf_obj):
    d = desc_text(intf_obj)
    if matches_any_pattern(d, UNUSED_DESC_PATTERNS):
        return True
    vlan = None
    for child in intf_obj.children:
        m = re.match(r"^\s*switchport\s+access\s+vlan\s+(\d+)\s*$", child.text)
        if m:
            vlan = m.group(1)
            break
    return vlan == PARKING_VLAN


def is_auth_controlled(intf_obj):
    # If you're using MAB as your primary auth method, this is a good trigger
    return has_child(intf_obj, r"^\s*authentication\s+port-control\s+auto\s*$")

def lint_config(config_path):
    with open(config_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    lines = normalize_lines(raw)

    # Parse from normalized lines instead of file path
    parse = CiscoConfParse(lines, syntax="ios", factory=True)

    # Also match "interface range ..." blocks
    interfaces = parse.find_objects(r"^interface\s+")

    findings = []

    for intf in interfaces:
        name = intf.text.replace("interface", "").strip()
        d = desc_text(intf)

        # RULE: Unused ports must be shutdown
        if is_unused_port(intf):
            if not has_child(intf, r"^\s*shutdown\s*$"):
                findings.append({
                    "interface": name,
                    "description": d,
                    "rule": "Unused ports must be shutdown",
                    "missing": "shutdown",
                    "suggest": f"interface {name}\n shutdown\n!"
                })

        # RULE: Access ports must have authentication port-control auto
        if is_access_port(intf):
            if not has_child(intf, r"^\s*authentication\s+port-control\s+auto\s*$"):
                findings.append({
                    "interface": name,
                    "description": d,
                    "rule": "Access ports must require auth",
                    "missing": "authentication port-control auto",
                    "suggest": f"interface {name}\n authentication port-control auto\n!"
                })


        # OPTIONAL RULE: If auth-controlled, require MAB (useful in MAB-only environments)
        if is_auth_controlled(intf):
            if not has_child(intf, r"^\s*mab\s*$"):
                findings.append({
                    "interface": name,
                    "description": d,
                    "rule": "Auth-controlled ports must enable MAB (MAB environment)",
                    "missing": "mab",
                    "suggest": f"interface {name}\n mab\n!"
                })

    return findings

def main():
    if len(sys.argv) != 2:
        print("Usage: python lint_switch_config.py <config.txt>")
        sys.exit(1)

    config_path = sys.argv[1]
    findings = lint_config(config_path)

    if not findings:
        print("✅ No findings. Config matches rules.")
        return

    print(f"❌ Found {len(findings)} issue(s):\n")
    for i, f in enumerate(findings, 1):
        print(f"{i}. Interface: {f['interface']}")
        if f["description"]:
            print(f"   Description: {f['description']}")
        print(f"   Rule: {f['rule']}")
        print(f"   Missing: {f['missing']}")
        print("   Suggested fix:")
        print("   " + "\n   ".join(f["suggest"].splitlines()))
        print()

if __name__ == "__main__":
    main()