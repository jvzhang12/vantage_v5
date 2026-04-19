from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SummaryRule:
    label: str
    summary_root: Path
    source_roots: tuple[Path, ...]
    suffixes: tuple[str, ...]
    exact_suffixes: tuple[str, ...] = ()


RULES = (
    SummaryRule(
        label="python",
        summary_root=REPO_ROOT / "docs" / "codebase" / "python",
        source_roots=(
            REPO_ROOT / "src" / "vantage_v5",
            REPO_ROOT / "tests",
            REPO_ROOT / "scripts",
        ),
        suffixes=(".py",),
    ),
    SummaryRule(
        label="webapp",
        summary_root=REPO_ROOT / "docs" / "codebase" / "webapp",
        source_roots=(
            REPO_ROOT / "src" / "vantage_v5" / "webapp",
            REPO_ROOT / "tests",
        ),
        suffixes=(".js", ".mjs", ".html", ".css"),
        exact_suffixes=(".test.mjs",),
    ),
)

REQUIRED_GUIDES = (
    REPO_ROOT / "docs" / "codebase" / "README.md",
    REPO_ROOT / "docs" / "codebase" / "python" / "README.md",
    REPO_ROOT / "docs" / "codebase" / "webapp" / "README.md",
)


def _is_relevant_source(path: Path, rule: SummaryRule) -> bool:
    if "__pycache__" in path.parts:
        return False
    if path.suffix == ".pyc":
        return False
    if any(part.endswith(".egg-info") for part in path.parts):
        return False
    if not path.is_file():
        return False
    path_str = str(path)
    if rule.exact_suffixes and any(path_str.endswith(suffix) for suffix in rule.exact_suffixes):
        return True
    return path.suffix in rule.suffixes


def _summary_path_for(source_path: Path, summary_root: Path) -> Path:
    relative = source_path.relative_to(REPO_ROOT)
    return summary_root / Path(f"{relative}.md")


def _expected_summary_paths(rule: SummaryRule) -> set[Path]:
    expected: set[Path] = set()
    for root in rule.source_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if _is_relevant_source(path, rule):
                expected.add(_summary_path_for(path, rule.summary_root))
    return expected


def _actual_summary_paths(summary_root: Path) -> set[Path]:
    if not summary_root.exists():
        return set()
    return {
        path
        for path in summary_root.rglob("*.md")
        if path.name != "README.md"
    }


def collect_hygiene_issues() -> dict[str, list[Path]]:
    missing_guides = [path for path in REQUIRED_GUIDES if not path.exists()]
    missing_summaries: list[Path] = []
    orphaned_summaries: list[Path] = []

    for rule in RULES:
        expected = _expected_summary_paths(rule)
        actual = _actual_summary_paths(rule.summary_root)
        missing_summaries.extend(sorted(expected - actual))
        orphaned_summaries.extend(sorted(actual - expected))

    return {
        "missing_guides": sorted(missing_guides),
        "missing_summaries": sorted(missing_summaries),
        "orphaned_summaries": sorted(orphaned_summaries),
    }


def main() -> int:
    issues = collect_hygiene_issues()
    if not any(issues.values()):
        print("Repo hygiene check passed.")
        return 0

    print("Repo hygiene check failed.")
    for label, paths in issues.items():
        if not paths:
            continue
        print(f"\n{label.replace('_', ' ').title()}:")
        for path in paths:
            print(f"- {path.relative_to(REPO_ROOT)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
