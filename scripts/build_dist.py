#!/usr/bin/env python3
"""Build the SkillHub upload archive for this skill.

SkillHub rejects some file types outright — uploading a tree that contains
`.gitignore` fails with `不允许的文件类型: .gitignore`. Packaging therefore has to
be reproducible instead of an ad-hoc `zip -r`, so the exclusions live here and
are covered by a test.

Usage:
    python3 scripts/build_dist.py [output-dir]

Writes `<output-dir>/<slug>-<version>.zip`, defaulting the output dir to
`<repo>/dist`.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_SLUG = REPO_ROOT.name

# Rejected by SkillHub, or meaningless on a published skill:
#   .gitignore / .gitattributes / .git / .github / __pycache__ / .DS_Store
# `dist` is our own build output and must not nest inside the archive.
EXCLUDED_NAMES = frozenset(
    {".git", ".github", ".gitignore", ".gitattributes", ".DS_Store", "__pycache__", "dist"}
)
EXCLUDED_SUFFIXES = frozenset({".pyc", ".pyo"})
# Repo-maintenance tooling, not skill runtime.
EXCLUDED_RELATIVE = frozenset({"scripts/build_dist.py"})


def skill_version(root: Path = REPO_ROOT) -> str:
    """Read `version:` from the SKILL.md frontmatter."""
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SystemExit("SKILL.md must open with YAML frontmatter")
    frontmatter = text.split("---\n", 2)[1]
    match = re.search(r"(?m)^version:\s*(\S+)\s*$", frontmatter)
    if not match:
        raise SystemExit("SKILL.md frontmatter is missing `version`")
    return match.group(1)


def iter_payload(root: Path = REPO_ROOT):
    """Yield (absolute path, path relative to root) for every file to package."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_NAMES for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        if relative.as_posix() in EXCLUDED_RELATIVE:
            continue
        yield path, relative


def build(output_dir: Path | None = None, root: Path = REPO_ROOT) -> Path:
    destination = Path(output_dir) if output_dir is not None else root / "dist"
    destination.mkdir(parents=True, exist_ok=True)
    slug = root.name
    archive = destination / f"{slug}-{skill_version(root)}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path, relative in iter_payload(root):
            bundle.write(path, f"{slug}/{relative.as_posix()}")
    return archive


def main(argv: list[str]) -> int:
    output_dir = Path(argv[1]).expanduser() if len(argv) > 1 else None
    archive = build(output_dir)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
