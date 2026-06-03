#!/usr/bin/env python3
"""
extract-sections.py — Extract specific ## sections from a Markdown artifact.

Usage:
  python3 extract-sections.py <md_file> <Section Name> [Section Name 2 ...]
  python3 extract-sections.py <md_file> "*"   # return entire file

Section names must match the text after '## ' exactly (case-sensitive).
Output: concatenated Markdown of the requested sections, headers preserved.

Examples:
  python3 extract-sections.py ph1_problem_spec.md "Requirements" "Acceptance Criteria"
  python3 extract-sections.py ph2_design_spec.md "Architecture" "API Contracts" "Security Considerations"
  python3 extract-sections.py ph5_6_impl_manifest.md "*"
"""

import re
import sys


def extract_sections(md_path: str, sections: list) -> str:
    with open(md_path, "r") as f:
        content = f.read()

    if sections == ["*"]:
        return content

    # Prepend newline so every ## heading has a leading newline to split on
    parts = re.split(r"\n(?=## )", "\n" + content)

    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        first_line = part.split("\n")[0]
        header = re.sub(r"^#+\s*", "", first_line).strip()
        if header in sections:
            result.append(part)

    missing = [s for s in sections if not any(
        re.sub(r"^#+\s*", "", p.split("\n")[0]).strip() == s
        for p in parts if p.strip()
    )]
    if missing:
        print(f"WARNING: sections not found in {md_path}: {missing}", file=sys.stderr)

    return "\n\n".join(result)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: extract-sections.py <md_file> <Section Name> [Section Name 2 ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    md_file = sys.argv[1]
    requested = sys.argv[2:]
    print(extract_sections(md_file, requested))
