#!/usr/bin/env python3
"""
Standard Build Script

Concatenates all markdown files into a single document with generated table of contents.
"""

import os
import re
from pathlib import Path
from datetime import datetime


STANDARD_DIR = Path(__file__).parent
OUTPUT_FILE = STANDARD_DIR.parent / "SAGA-Standard-v1.0.md"

SECTION_ORDER = [
    "README.md",
    "00-foreword.md",
    "part-1-foundations/01-introduction.md",
    "part-1-foundations/02-scope.md",
    "part-1-foundations/03-threat-model.md",
    "part-1-foundations/04-core-concepts.md",
    "part-2-principles/05-design-principles.md",
    "part-2-principles/06-trust-boundaries.md",
    "part-2-principles/07-autonomy-tiers.md",
    "part-3-architecture/08-secret-profiles.md",
    "part-3-architecture/09-access-control.md",
    "part-3-architecture/10-approval-policies.md",
    "part-3-architecture/11-secret-lifecycle.md",
    "part-3-architecture/12-delegation.md",
    "part-4-conformance/13-conformance.md",
    "part-5-reference/14-cryptographic-requirements.md",
    "part-5-reference/15-audit-observability.md",
    "part-5-reference/16-relationship-to-standards.md",
    "appendices/appendix-a-evaluation-criteria.md",
    "appendices/appendix-b-compensating-controls.md",
    "appendices/appendix-c-anti-patterns.md",
]


def extract_headers(content: str, file_path: str) -> list[dict]:
    """Extract headers from markdown content."""
    headers = []
    lines = content.split("\n")

    for line in lines:
        match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            anchor = generate_anchor(title)
            headers.append({
                "level": level,
                "title": title,
                "anchor": anchor,
                "file": file_path,
            })

    return headers


def generate_anchor(title: str) -> str:
    """Generate GitHub-style anchor from title."""
    anchor = title.lower()
    anchor = re.sub(r"[^a-z0-9\s-]", "", anchor)
    anchor = re.sub(r"\s+", "-", anchor)
    anchor = re.sub(r"-+", "-", anchor)
    return anchor.strip("-")


def generate_toc(headers: list[dict]) -> str:
    """Generate table of contents from headers."""
    lines = ["## Table of Contents\n"]

    for header in headers:
        if header["level"] == 1:
            indent = ""
        elif header["level"] == 2:
            indent = "  "
        elif header["level"] == 3:
            indent = "    "
        else:
            continue

        title = re.sub(r"<[^>]+>", "", header["title"])
        lines.append(f"{indent}- [{title}](#{header['anchor']})")

    lines.append("")
    return "\n".join(lines)


def read_file(file_path: str) -> str:
    """Read and return file content."""
    full_path = STANDARD_DIR / file_path
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def adjust_header_levels(content: str, is_readme: bool = False) -> str:
    """Adjust header levels for consistent document structure."""
    lines = content.split("\n")
    adjusted = []

    for line in lines:
        match = re.match(r"^(#+)\s+(.+)$", line)
        if match:
            hashes = match.group(1)
            title = match.group(2)

            if is_readme:
                if len(hashes) == 1:
                    new_level = 1
                else:
                    new_level = len(hashes)
            else:
                new_level = len(hashes)

            adjusted.append(f"{'#' * new_level} {title}")
        else:
            adjusted.append(line)

    return "\n".join(adjusted)


def build_standard():
    """Build the complete standard document."""
    print("Building the Standard v1.0...")

    all_headers = []
    all_content = []

    for file_path in SECTION_ORDER:
        print(f"  Processing: {file_path}")

        content = read_file(file_path)
        is_readme = file_path == "README.md"

        if not is_readme:
            headers = extract_headers(content, file_path)
            all_headers.extend(headers)

        adjusted = adjust_header_levels(content, is_readme)
        all_content.append(adjusted)

    print("  Generating table of contents...")
    toc = generate_toc(all_headers)

    header = f"""# SAGA: Secret Access Governance for Agents

## Version 1.0 — Public Draft

**Standard Identifier:** SAGA-2026-01
**Status:** Public Draft
**Date:** {datetime.now().strftime("%Y-%m-%d")}
**Working Group:** Open

---

"""

    print(f"  Writing: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(toc)
        f.write("\n---\n\n")

        for content in all_content:
            f.write(content)
            f.write("\n\n---\n\n")

    print("Done!")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Sections: {len(SECTION_ORDER)}")
    print(f"Headers: {len(all_headers)}")


if __name__ == "__main__":
    build_standard()
