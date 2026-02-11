# Architecture Design: Slides Export Feature

**Date**: 2026-02-12
**Status**: Proposed
**Inputs**: [slides_requirements.md](slides_requirements.md), [slides_tech_research.md](slides_tech_research.md)

---

## 1. Design Goals

1. **Minimal changes to existing code** -- the 3-phase pipeline in `__main__.py` must not be restructured; we extract data at the boundary between pipeline and rendering.
2. **Formatter abstraction** -- both Markdown and PPTX are formatters that consume the same data model.
3. **Optional dependency** -- `python-pptx` is imported lazily; users who do not need slides are unaffected.
4. **Clean module boundaries** -- new code lives in new files; existing files receive only surgical modifications.

---

## 2. Data Model

The pipeline currently builds three dicts/lists inline (`authored_details`, `reviewed_prs`, `waiting_prs`) and computes summary metrics before rendering Markdown. We introduce a `ReportData` dataclass that captures all of this in a structured, formatter-agnostic form.

### 2.1 Dataclass Definitions

All dataclasses live in a new file `daily_report/report_data.py`.

```python
"""Structured report data model, consumed by all formatters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AuthoredPR:
    """A PR authored or contributed to by the user."""
    repo: str
    title: str
    number: int
    status: str              # "Open", "Draft", "Merged", "Closed"
    additions: int           # line additions (0 for Merged/Closed)
    deletions: int           # line deletions (0 for Merged/Closed)
    contributed: bool        # True if user is contributor, not author
    original_author: Optional[str]  # PR author login when contributed=True


@dataclass
class ReviewedPR:
    """A PR reviewed or approved by the user."""
    repo: str
    title: str
    number: int
    author: str              # PR author login
    status: str              # "Open", "Draft", "Merged", "Closed"


@dataclass
class WaitingPR:
    """A PR authored by the user that is waiting for review."""
    repo: str
    title: str
    number: int
    reviewers: List[str]     # logins of pending reviewers
    created_at: str          # YYYY-MM-DD
    days_waiting: int


@dataclass
class SummaryStats:
    """Aggregate metrics for the report."""
    total_prs: int
    repo_count: int
    merged_count: int
    open_count: int
    themes: List[str]        # conventional commit prefixes found
    is_range: bool           # True if date_from != date_to


@dataclass
class ReportData:
    """Complete report data, produced by the pipeline and consumed by formatters."""
    user: str
    date_from: str           # YYYY-MM-DD
    date_to: str             # YYYY-MM-DD
    authored_prs: List[AuthoredPR] = field(default_factory=list)
    reviewed_prs: List[ReviewedPR] = field(default_factory=list)
    waiting_prs: List[WaitingPR] = field(default_factory=list)
    summary: SummaryStats = field(default_factory=lambda: SummaryStats(
        total_prs=0, repo_count=0, merged_count=0, open_count=0,
        themes=[], is_range=False,
    ))
```

### 2.2 Mapping from Current Dicts to Dataclasses

The existing code builds `authored_details` as a list of dicts (lines 528-554 of `__main__.py`), `reviewed_prs` as a list of dicts (lines 557-573), and `waiting_prs` as a list of dicts (lines 576-608). The summary metrics are computed inline (lines 613-627). The mapping is one-to-one:

| Current dict key | Dataclass field | Notes |
|---|---|---|
| `authored_details[i]["repo"]` | `AuthoredPR.repo` | |
| `authored_details[i]["title"]` | `AuthoredPR.title` | |
| `authored_details[i]["number"]` | `AuthoredPR.number` | |
| `authored_details[i]["status"]` | `AuthoredPR.status` | |
| `authored_details[i]["additions"]` | `AuthoredPR.additions` | |
| `authored_details[i]["deletions"]` | `AuthoredPR.deletions` | |
| `authored_details[i]["contributed"]` | `AuthoredPR.contributed` | |
| `authored_details[i]["original_author"]` | `AuthoredPR.original_author` | |
| `reviewed_prs[i]["repo"]` | `ReviewedPR.repo` | |
| `reviewed_prs[i]["title"]` | `ReviewedPR.title` | |
| `reviewed_prs[i]["number"]` | `ReviewedPR.number` | |
| `reviewed_prs[i]["author"]` | `ReviewedPR.author` | |
| `reviewed_prs[i]["status"]` | `ReviewedPR.status` | |
| `waiting_prs[i]["repo"]` | `WaitingPR.repo` | |
| `waiting_prs[i]["title"]` | `WaitingPR.title` | |
| `waiting_prs[i]["number"]` | `WaitingPR.number` | |
| `waiting_prs[i]["reviewers"]` | `WaitingPR.reviewers` | |
| `waiting_prs[i]["created_at"]` | `WaitingPR.created_at` | |
| `waiting_prs[i]["days_waiting"]` | `WaitingPR.days_waiting` | |

---

## 3. Module Structure

### 3.1 New Files

```
daily_report/
    __init__.py          (existing, unchanged)
    __main__.py          (existing, surgically modified)
    config.py            (existing, unchanged)
    git_local.py         (existing, unchanged)
    graphql_client.py    (existing, unchanged)
    report_data.py       (NEW -- dataclass definitions from Section 2)
    format_markdown.py   (NEW -- markdown formatter, extracted from __main__.py)
    format_slides.py     (NEW -- PPTX formatter using python-pptx)
```

### 3.2 Responsibilities

| Module | Responsibility | Depends on |
|---|---|---|
| `report_data.py` | Data model definitions only. No logic, no imports beyond `dataclasses`/`typing`. | nothing |
| `format_markdown.py` | `format_markdown(data: ReportData) -> str` -- returns the full Markdown report as a string. Pure function, no side effects. | `report_data` |
| `format_slides.py` | `format_slides(data: ReportData, output_path: str) -> None` -- writes a .pptx file to disk. Imports `python-pptx` at call time. | `report_data`, `python-pptx` |
| `__main__.py` | Pipeline orchestration + CLI. Builds `ReportData`, dispatches to the selected formatter. | `report_data`, `format_markdown`, `format_slides` |

### 3.3 Dependency Graph

```
__main__.py
  |
  +-- config.py
  +-- git_local.py
  +-- graphql_client.py
  +-- report_data.py  <-- NEW (pure data, no deps)
  +-- format_markdown.py  <-- NEW (depends on report_data)
  +-- format_slides.py  <-- NEW (depends on report_data, python-pptx)
```

No circular dependencies. `report_data.py` is a leaf node. Both formatters depend only on `report_data`. `__main__.py` imports both formatters but only calls the selected one.

---

## 4. Changes to `__main__.py`

The goal is **surgical, minimal changes**. The 3-phase pipeline (lines 335-608) is untouched. Only the report-building and output section (lines 528-688) is restructured.

### 4.1 New Imports (top of file)

Add at the existing import block (after line 28):

```python
from daily_report.report_data import (
    ReportData, AuthoredPR, ReviewedPR, WaitingPR, SummaryStats,
)
from daily_report.format_markdown import format_markdown
```

The slides formatter is NOT imported at the top level -- it is imported lazily inside a conditional block (see Section 7).

### 4.2 New CLI Arguments (inside `main()`, after line 275)

Add two new arguments to the argument parser:

```python
parser.add_argument(
    "--slides", action="store_true", default=False,
    help="generate .pptx slide deck instead of Markdown output",
)
parser.add_argument(
    "--slides-output", dest="slides_output", default=None,
    help="output path for .pptx file (default: auto-generated name in CWD)",
)
```

These are inserted after the existing `--no-local` argument (line 275), before `args = parser.parse_args()` (line 276).

### 4.3 Validate Slides Arguments (after line 312)

After the date validation block, add:

```python
if args.slides_output and not args.slides:
    print("Error: --slides-output requires --slides.", file=sys.stderr)
    sys.exit(1)
```

### 4.4 Replace Dict Building with Dataclass Construction (lines 528-608)

**Current code** (lines 528-554) builds `authored_details` as a list of dicts. **Replace** with `AuthoredPR` dataclass instances:

```python
    # Build authored_prs list
    authored_prs_list: list[AuthoredPR] = []
    for key, role in authored_pr_keys.items():
        pr_org, repo_name, pr_number = key
        detail = pr_details.get(key, {})
        title = detail.get("title", "")
        state = detail.get("state", "")
        is_draft = detail.get("isDraft", False)
        merged_at = detail.get("mergedAt")
        additions = detail.get("additions", 0) or 0
        deletions = detail.get("deletions", 0) or 0
        pr_author = (detail.get("author") or {}).get("login", "")
        status = format_status(state, is_draft, merged_at)
        if status not in ("Open", "Draft"):
            additions, deletions = 0, 0
        authored_prs_list.append(AuthoredPR(
            repo=repo_name,
            title=title,
            number=pr_number,
            status=status,
            additions=additions,
            deletions=deletions,
            contributed=(role == "contributed"),
            original_author=pr_author if role == "contributed" else None,
        ))

    authored_prs_list.sort(key=lambda d: (d.repo, d.number))
```

The change is mechanical: dict literals become dataclass constructors, bracket access becomes attribute access. The sorting key changes from `d["repo"]` to `d.repo`.

**Similarly for `reviewed_prs`** (lines 557-573):

```python
    reviewed_prs_list: list[ReviewedPR] = []
    for key in sorted(reviewed_pr_keys):
        pr_org, repo_name, pr_number = key
        detail = pr_details.get(key, {})
        title = detail.get("title", "")
        state = detail.get("state", "")
        is_draft = detail.get("isDraft", False)
        merged_at = detail.get("mergedAt")
        pr_author = (detail.get("author") or {}).get("login", "")
        status = format_status(state, is_draft, merged_at)
        reviewed_prs_list.append(ReviewedPR(
            repo=repo_name,
            title=title,
            number=pr_number,
            author=pr_author,
            status=status,
        ))
```

**Similarly for `waiting_prs`** (lines 576-608):

```python
    waiting_prs_list: list[WaitingPR] = []
    # ... (same loop body as current, but using WaitingPR(...) instead of dict)
```

The pipeline logic inside these loops (GraphQL calls, date filtering, reviewer extraction) is identical. Only the final data structure changes from dict to dataclass.

### 4.5 Build ReportData and SummaryStats (replaces lines 613-627)

Replace the inline summary computation and `lines` list construction:

```python
    # Build summary
    all_titles = [p.title for p in authored_prs_list] + [p.title for p in reviewed_prs_list]
    themes = extract_themes(all_titles)

    all_repos = set()
    for p in authored_prs_list:
        all_repos.add(p.repo)
    for p in reviewed_prs_list:
        all_repos.add(p.repo)

    total_prs = len(authored_prs_list) + len(reviewed_prs_list)
    merged_count = (
        sum(1 for p in authored_prs_list if p.status == "Merged")
        + sum(1 for p in reviewed_prs_list if p.status == "Merged")
    )
    open_count = sum(1 for p in authored_prs_list if p.status in ("Open", "Draft"))

    report = ReportData(
        user=user,
        date_from=date_from,
        date_to=date_to,
        authored_prs=authored_prs_list,
        reviewed_prs=reviewed_prs_list,
        waiting_prs=waiting_prs_list,
        summary=SummaryStats(
            total_prs=total_prs,
            repo_count=len(all_repos),
            merged_count=merged_count,
            open_count=open_count,
            themes=themes,
            is_range=is_range,
        ),
    )
```

### 4.6 Format Dispatch (replaces lines 629-688)

Replace the Markdown rendering block with format dispatch:

```python
    # Output
    if args.slides:
        # Lazy import -- python-pptx is optional
        try:
            from daily_report.format_slides import format_slides
        except ImportError:
            print(
                "Error: python-pptx is required for --slides. "
                "Install it with: pip install python-pptx",
                file=sys.stderr,
            )
            sys.exit(1)

        if args.slides_output:
            output_path = args.slides_output
        else:
            if date_from == date_to:
                output_path = f"daily-report-{user}-{date_from}.pptx"
            else:
                output_path = f"daily-report-{user}-{date_from}_{date_to}.pptx"

        format_slides(report, output_path)
        print(f"Slides written to {output_path}", file=sys.stderr)
    else:
        output = format_markdown(report)
        print(output)
```

### 4.7 Summary of Line Changes

| Lines (current) | Action | Description |
|---|---|---|
| 1-28 | ADD imports | Add `report_data` and `format_markdown` imports |
| 262-276 | ADD arguments | Add `--slides` and `--slides-output` to argparser |
| 282-312 | ADD validation | Validate `--slides-output` requires `--slides` |
| 528-554 | MODIFY | Change `authored_details` dict list to `AuthoredPR` dataclass list |
| 557-573 | MODIFY | Change `reviewed_prs` dict list to `ReviewedPR` dataclass list |
| 576-608 | MODIFY | Change `waiting_prs` dict list to `WaitingPR` dataclass list |
| 613-627 | MODIFY | Compute `SummaryStats` and build `ReportData` |
| 629-688 | REPLACE | Replace inline Markdown rendering with format dispatch |

Total: ~10 lines added for CLI/imports, ~60 lines modified (dict->dataclass), ~60 lines replaced (rendering->dispatch). The 3-phase pipeline (lines 335-527) is completely untouched.

---

## 5. Formatter Interface

There is no abstract base class or protocol -- the formatters are simply functions with a known signature. Adding a formal interface would be over-engineering for two formatters.

### 5.1 Markdown Formatter

```python
def format_markdown(report: ReportData) -> str:
    """Render the report as a Markdown string.

    Args:
        report: Complete report data.

    Returns:
        The full Markdown report as a single string (no trailing newline).
    """
```

This is a pure function. It returns a string; the caller decides whether to print it or write it to a file. The implementation is extracted verbatim from the current `lines.append(...)` block in `__main__.py` (lines 629-687), with `d["repo"]` access replaced by `p.repo` attribute access.

### 5.2 Slides Formatter

```python
def format_slides(report: ReportData, output_path: str) -> None:
    """Render the report as a PPTX slide deck.

    Args:
        report: Complete report data.
        output_path: File path to write the .pptx file.

    Raises:
        OSError: If the file cannot be written (permissions, missing directory).
    """
```

This function has a side effect (writing a file). It does not print to stdout. Errors propagate as exceptions; the caller in `__main__.py` can catch and display them.

### 5.3 Why Not a Protocol/ABC

- Two formatters with different signatures (`-> str` vs `-> None` with a path argument) do not share a clean interface without introducing artificial uniformity.
- A protocol would force the Markdown formatter to accept an `output_path` it does not need, or force the slides formatter to return a string it does not produce.
- If a third formatter is added in the future, introducing an abstraction at that point is straightforward. Two cases do not justify the abstraction cost.

---

## 6. Slides Formatter: Detailed Design (`format_slides.py`)

### 6.1 Module Structure

```python
"""PPTX slide deck formatter for daily-report.

Requires python-pptx: pip install python-pptx
"""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN

from daily_report.report_data import (
    ReportData, AuthoredPR, ReviewedPR, WaitingPR,
)


def format_slides(report: ReportData, output_path: str) -> None:
    ...

# --- internal helpers (private) ---

def _add_title_slide(prs: Presentation, report: ReportData) -> None:
    ...

def _add_project_slide(prs: Presentation, repo_name: str,
                        authored: list[AuthoredPR],
                        reviewed: list[ReviewedPR],
                        waiting: list[WaitingPR]) -> None:
    ...

def _add_summary_slide(prs: Presentation, report: ReportData) -> None:
    ...

def _group_by_repo(report: ReportData) -> dict[str, dict]:
    ...
```

### 6.2 Slide Generation Flow

```
format_slides(report, output_path)
  |
  +-- prs = Presentation()   # blank, default 16:9
  |
  +-- _add_title_slide(prs, report)
  |     Slide layout 0 (Title Slide)
  |     Title: "Activity Report"
  |     Subtitle: "{user}\n{date_from} .. {date_to}"
  |
  +-- projects = _group_by_repo(report)
  |     Groups authored_prs, reviewed_prs, waiting_prs by repo name
  |     Returns: dict[repo_name -> {"authored": [...], "reviewed": [...], "waiting": [...]}]
  |
  +-- for repo_name in sorted(projects):
  |     _add_project_slide(prs, repo_name, authored, reviewed, waiting)
  |       Slide layout 1 (Title and Content)
  |       Title: repo_name
  |       Body: grouped bullet lists with section subheadings
  |
  +-- _add_summary_slide(prs, report)
  |     Slide layout 1 (Title and Content)
  |     Title: "Summary"
  |     Body: bullet list of aggregate metrics
  |
  +-- prs.save(output_path)
```

### 6.3 Grouping Logic (`_group_by_repo`)

```python
def _group_by_repo(report: ReportData) -> dict[str, dict]:
    """Group all PR lists by repository name.

    Returns:
        Dict mapping repo name to {"authored": [...], "reviewed": [...], "waiting": [...]}.
        Only repos with at least one item are included.
    """
    projects: dict[str, dict] = {}
    for pr in report.authored_prs:
        projects.setdefault(pr.repo, {"authored": [], "reviewed": [], "waiting": []})
        projects[pr.repo]["authored"].append(pr)
    for pr in report.reviewed_prs:
        projects.setdefault(pr.repo, {"authored": [], "reviewed": [], "waiting": []})
        projects[pr.repo]["reviewed"].append(pr)
    for pr in report.waiting_prs:
        projects.setdefault(pr.repo, {"authored": [], "reviewed": [], "waiting": []})
        projects[pr.repo]["waiting"].append(pr)
    return projects
```

### 6.4 Project Slide Content

Each project slide uses layout index 1 (Title and Content). The body text frame contains:

```
[Bold] Authored / Contributed          <-- section heading (level 0, bold, 14pt)
  PR title #123 -- Merged             <-- item (level 1, 12pt)
  PR title #456 (alice) -- Open (+10/-3)

[Bold] Reviewed                        <-- omitted if empty
  PR title #789 (bob) -- Merged

[Bold] Waiting for Review              <-- omitted if empty
  PR title #101 -- reviewer: carol, dave -- 5 days
```

Sections with no items are omitted entirely (no empty headings).

### 6.5 Text Formatting

| Element | Font Size | Bold | Level |
|---|---|---|---|
| Slide title | Default (layout) | Yes | N/A |
| Section heading | 14pt | Yes | 0 |
| PR item | 12pt | No | 1 |
| Summary bullet | 14pt | No | 0 |

Font family: Calibri (PowerPoint default, converts well to Google Slides).

### 6.6 Slide Dimensions

Use the default python-pptx presentation size, which is 10" x 7.5" (standard 4:3). To use 16:9 widescreen (matching the requirements doc):

```python
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
```

### 6.7 Bullet Text Construction

Helper functions for constructing bullet text for each PR type:

```python
def _authored_pr_text(pr: AuthoredPR) -> str:
    text = f"{pr.title} #{pr.number}"
    if pr.contributed and pr.original_author:
        text += f" ({pr.original_author})"
    text += f" -- {pr.status}"
    if pr.status in ("Open", "Draft"):
        text += f" (+{pr.additions}/-{pr.deletions})"
    return text

def _reviewed_pr_text(pr: ReviewedPR) -> str:
    return f"{pr.title} #{pr.number} ({pr.author}) -- {pr.status}"

def _waiting_pr_text(pr: WaitingPR) -> str:
    reviewers = ", ".join(pr.reviewers)
    return f"{pr.title} #{pr.number} -- reviewer: {reviewers} -- {pr.days_waiting} days"
```

---

## 7. CLI Changes

### 7.1 New Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `--slides` | flag | `False` | Generate .pptx slide deck instead of Markdown |
| `--slides-output` | string | auto | Custom output path for .pptx file |

### 7.2 Behavior Matrix

| `--slides` | `--slides-output` | Stdout | File output |
|---|---|---|---|
| absent | N/A | Markdown (current behavior) | None |
| present | absent | Nothing | `.pptx` with auto-generated name |
| present | provided | Nothing | `.pptx` at specified path |

When `--slides` is active, a confirmation message is printed to stderr:
```
Slides written to daily-report-username-2026-02-06.pptx
```

### 7.3 Validation Rules

- `--slides-output` without `--slides` is an error.
- `--slides` does not conflict with any existing flags (`--org`, `--user`, `--date`, `--from`, `--to`, `--config`, `--repos-dir`, `--git-email`, `--no-local`). All data-gathering flags work identically regardless of output format.

---

## 8. Dependency Management

### 8.1 Optional Dependency Pattern

`python-pptx` is NOT added to the core requirements. It is an optional dependency:

```
# In requirements.txt or setup.cfg extras:
[slides]
python-pptx>=0.6.23
```

### 8.2 Lazy Import in `__main__.py`

The slides formatter is imported only when `--slides` is used:

```python
if args.slides:
    try:
        from daily_report.format_slides import format_slides
    except ImportError:
        print(
            "Error: python-pptx is required for --slides. "
            "Install it with: pip install python-pptx",
            file=sys.stderr,
        )
        sys.exit(1)
```

This means:
- `format_slides.py` has `from pptx import Presentation` at module level -- this is fine because the module is only imported when needed.
- Users who never use `--slides` never trigger the `python-pptx` import.
- If `python-pptx` is not installed and `--slides` is used, the user gets a clear, actionable error message.

### 8.3 Import in `format_slides.py`

`format_slides.py` imports `python-pptx` at the top of the file (not lazily inside functions). The lazy gate is in `__main__.py` where the module itself is imported conditionally. This keeps `format_slides.py` clean and avoids try/except blocks scattered throughout the module.

---

## 9. File Naming Convention

### 9.1 Auto-Generated Name

```
daily-report-{username}-{date_from}[_{date_to}].pptx
```

Examples:
- Single date: `daily-report-alexdev-2026-02-06.pptx`
- Date range: `daily-report-alexdev-2026-01-26_2026-02-06.pptx`

When `date_from == date_to`, the date suffix is just the single date (no duplication).

### 9.2 Custom Path via `--slides-output`

The user-provided path is used verbatim. If the parent directory does not exist, `prs.save()` will raise `FileNotFoundError`, which propagates and is caught in `__main__.py`:

```python
try:
    format_slides(report, output_path)
except (OSError, FileNotFoundError) as e:
    print(f"Error: cannot write slides: {e}", file=sys.stderr)
    sys.exit(1)
```

### 9.3 Overwrite Behavior

Existing files are overwritten silently. The date-encoded filename provides sufficient uniqueness to prevent accidental data loss.

---

## 10. Markdown Formatter: Extraction Plan (`format_markdown.py`)

### 10.1 What Moves

The Markdown rendering logic from `__main__.py` lines 629-687 (the `lines = []` block through `print("\n".join(lines))`) is extracted into `format_markdown.py`. The function takes `ReportData` and returns a string.

### 10.2 Implementation

```python
"""Markdown formatter for daily-report."""

from __future__ import annotations

from daily_report.report_data import ReportData


def format_markdown(report: ReportData) -> str:
    """Render the report as a Markdown string.

    Args:
        report: Complete report data.

    Returns:
        The full Markdown report as a single string.
    """
    lines: list[str] = []
    is_range = report.summary.is_range

    if is_range:
        lines.append(f"# Daily Report \u2014 {report.date_from} .. {report.date_to}")
    else:
        lines.append(f"# Daily Report \u2014 {report.date_from}")
    lines.append("")

    # Authored / Contributed PRs
    lines.append("**Authored / Contributed PRs**")
    lines.append("")
    if report.authored_prs:
        for p in report.authored_prs:
            stats = ""
            if p.status in ("Open", "Draft"):
                stats = f" (+{p.additions}/\u2212{p.deletions})"
            author_info = ""
            if p.contributed and p.original_author:
                author_info = f" ({p.original_author})"
            lines.append(
                f"- `{p.repo}` \u2014 {p.title} #{p.number}{author_info} "
                f"\u2014 **{p.status}**{stats}"
            )
    else:
        lines.append("_No authored or contributed PRs._")
    lines.append("")

    # Reviewed / Approved PRs
    lines.append("**Reviewed / Approved PRs**")
    lines.append("")
    if report.reviewed_prs:
        for p in report.reviewed_prs:
            lines.append(
                f"- `{p.repo}` \u2014 {p.title} #{p.number} ({p.author}) "
                f"\u2014 **{p.status}**"
            )
    else:
        lines.append("_No reviewed or approved PRs._")
    lines.append("")

    # Waiting for review
    lines.append("**Waiting for review**")
    lines.append("")
    if report.waiting_prs:
        for w in report.waiting_prs:
            reviewer_names = ", ".join(f"**{r}**" for r in w.reviewers)
            lines.append(
                f"- `{w.repo}` \u2014 {w.title} #{w.number} \u2014 "
                f"reviewer: {reviewer_names} \u2014 since {w.created_at} "
                f"({w.days_waiting} days)"
            )
    else:
        lines.append("_No PRs waiting for review._")
    lines.append("")

    # Summary
    s = report.summary
    themes_str = ", ".join(s.themes) if s.themes else "general development"
    merged_label = "merged" if is_range else "merged today"
    lines.append(
        f"**Summary:** {s.total_prs} PRs across {s.repo_count} repos, "
        f"{s.merged_count} {merged_label}, {s.open_count} still open. "
        f"Key themes: {themes_str}."
    )

    return "\n".join(lines)
```

This is a near-verbatim extraction with `d["key"]` replaced by `p.attribute`. The output is identical to the current implementation.

---

## 11. Testing Strategy

### 11.1 Unit Tests for `report_data.py`

Minimal: verify dataclass construction and field access. Since these are plain dataclasses with no logic, a smoke test is sufficient.

### 11.2 Unit Tests for `format_markdown.py`

Create a `ReportData` fixture with known values and assert the output string matches expected Markdown. This replaces the current implicit test coverage (which tests the full pipeline end-to-end).

### 11.3 Unit Tests for `format_slides.py`

- Create a `ReportData` fixture.
- Call `format_slides(report, tmp_path / "test.pptx")`.
- Open the resulting file with `python-pptx` and assert:
  - Slide count matches expected (1 title + N projects + 1 summary).
  - Title slide text contains user and date.
  - Project slide titles match repo names.
  - Summary slide contains expected metrics text.

### 11.4 Regression Test for Markdown Output

Run the full pipeline (or a mocked version) and compare output before and after the refactoring. The Markdown output must be byte-identical.

### 11.5 Integration Tests for CLI Flags

- `--slides` without `python-pptx` prints error and exits 1.
- `--slides-output` without `--slides` prints error and exits 1.
- `--slides` produces a valid .pptx file.
- No `--slides` produces Markdown to stdout (unchanged behavior).

---

## 12. Migration Safety

### 12.1 Backward Compatibility Guarantee

- Without `--slides`, the tool's behavior is identical to before.
- The Markdown output is character-for-character identical because `format_markdown()` is a verbatim extraction of the existing rendering logic.
- All existing CLI flags continue to work unchanged.
- No existing imports are broken (no public API changes to any existing module).

### 12.2 Rollback Plan

If issues are discovered:
- `format_slides.py` and `format_slides.py` can be deleted without affecting Markdown output.
- The `--slides` and `--slides-output` arguments can be removed from the parser.
- The `ReportData` construction in `__main__.py` has no functional impact on the pipeline -- it simply replaces dicts with dataclasses at the output boundary.

---

## 13. Open Decisions

### 13.1 Slide Layout Index

The default `python-pptx` `Presentation()` has a set of built-in layouts. Layout 0 is "Title Slide", layout 1 is "Title and Content". These are used as-is. If a custom template is used in the future, layout indices may differ -- but that is a v2 concern.

### 13.2 Widescreen vs Standard

The requirements document specifies 16:9. The implementation should set `prs.slide_width = Inches(13.333)` and `prs.slide_height = Inches(7.5)` explicitly.

### 13.3 Font Fallback in Google Slides

Calibri (PowerPoint default) maps to a Google-available equivalent in Google Slides. No action needed. If the team later prefers a specific font, it can be changed in a single constant.
