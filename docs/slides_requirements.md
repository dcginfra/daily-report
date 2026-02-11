# Business Requirements: Google Slides Export

## 1. Executive Summary

### Problem Statement

The team conducts bi-weekly presentations using Google Slides to showcase progress
from the last two weeks. Today, team members manually copy Markdown output from
`daily-report` into Google Slides, reformatting text, splitting content across slides,
and adding structure by hand. This manual process is time-consuming, error-prone, and
discourages regular reporting.

### Proposed Solution

Add a `--slides` output mode to `daily-report` that generates a `.pptx` (PowerPoint)
file structured for direct upload to Google Slides. Each project (repository) gets its
own slide, with a title slide and summary slide bookending the deck. The existing
Markdown stdout output remains the default and is unchanged.

### Why PPTX (not Google Slides API directly)

- Google Slides API requires OAuth2 setup, service account credentials, and Google
  Cloud project configuration -- a heavy prerequisite for a CLI tool.
- PPTX files can be opened directly in Google Slides via "File > Import slides" or
  by uploading to Google Drive (auto-converts to Google Slides format).
- The `python-pptx` library is mature, well-documented, and has zero authentication
  requirements.
- Users who prefer PowerPoint or LibreOffice Impress also benefit.

---

## 2. Stakeholder & Actor Analysis

### Actor: Team Member (Primary User)

- **Description**: A software developer who runs `daily-report` to generate their
  personal activity report. Moderate to high technical proficiency. Uses the CLI
  regularly.
- **Primary Goals**: Generate a presentation-ready slide deck covering their PR
  activity for the past 1-2 weeks, with minimal manual effort.
- **Pain Points**: Manually reformatting Markdown output into slides; splitting
  content per project; losing time on formatting instead of content.
- **Success Metrics**: Can generate a slide deck in under 5 seconds; can upload to
  Google Slides without reformatting; each project is on a separate slide.
- **Frequency of Interaction**: Every 2 weeks (bi-weekly sprint presentations).

### Actor: Presentation Viewer (Secondary Stakeholder)

- **Description**: Team lead, manager, or peer who views the slide deck during
  bi-weekly presentations. Not a direct user of the CLI tool.
- **Primary Goals**: Quickly understand what work was done, in which projects, and
  what the overall activity level was.
- **Pain Points**: Inconsistent formatting across team members' slides; too much or
  too little detail; hard to scan quickly during a meeting.
- **Success Metrics**: Can understand activity at a glance; consistent structure
  across all team members' decks.
- **Frequency of Interaction**: Every 2 weeks (reading slides during meetings).

### Actor: Google Slides (Supporting System)

- **Description**: The target presentation platform. Receives `.pptx` files via
  upload/import.
- **Constraints**: PPTX import preserves text, basic formatting, and layout. Complex
  PowerPoint features (animations, SmartArt, embedded macros) do not convert well.
  Simple text + basic shapes + tables convert reliably.
- **Success Metrics**: Uploaded deck looks clean and readable without manual fixes.

---

## 3. User Stories & Acceptance Criteria

### US-1: Generate slide deck from CLI

```
As a team member,
I want to run daily-report with a --slides flag,
So that I get a .pptx file ready to upload to Google Slides.
```

**Acceptance Criteria:**

```
Given the user runs `daily-report --slides --from 2026-01-26 --to 2026-02-06`,
When the report pipeline completes,
Then a .pptx file is written to the current directory.

Given the --slides flag is provided,
When the report data is available,
Then the .pptx file contains: one title slide, one slide per project (repo) that
has activity, and one summary slide.

Given the --slides flag is NOT provided,
When the report runs,
Then output behavior is identical to today (Markdown to stdout). No .pptx is created.
```

### US-2: Title slide with report metadata

```
As a presentation viewer,
I want the first slide to show the report period and author,
So that I immediately know whose work and what timeframe I am looking at.
```

**Acceptance Criteria:**

```
Given a slide deck is generated,
When I open it,
Then the first slide displays:
  - Title: "Activity Report"
  - Subtitle line 1: the GitHub username
  - Subtitle line 2: the date range (e.g., "2026-01-26 .. 2026-02-06") or single
    date (e.g., "2026-02-06")
```

### US-3: Per-project slides with PR details

```
As a presentation viewer,
I want each project to have its own slide listing the PRs,
So that I can see activity broken down by repository.
```

**Acceptance Criteria:**

```
Given a project has authored/contributed PRs,
When its slide is rendered,
Then the slide title is the repository name,
And each authored/contributed PR appears as a bullet:
  "PR title #number -- Status"
  with contribution attribution if applicable (e.g., "(original author: username)").

Given a project has reviewed/approved PRs,
When its slide is rendered,
Then reviewed PRs appear under a "Reviewed" subheading:
  "PR title #number (author) -- Status"

Given a project has PRs waiting for review,
When its slide is rendered,
Then waiting PRs appear under a "Waiting for Review" subheading:
  "PR title #number -- reviewer: name1, name2 -- N days"

Given a project has activity in multiple categories (authored + reviewed + waiting),
When its slide is rendered,
Then all categories appear on the same slide, grouped under subheadings.
```

### US-4: Summary slide with aggregate metrics

```
As a presentation viewer,
I want the last slide to summarize overall activity,
So that I get a quick high-level picture.
```

**Acceptance Criteria:**

```
Given the slide deck is generated,
When I view the last slide,
Then it displays:
  - Title: "Summary"
  - Total number of PRs
  - Number of repositories with activity
  - Number of PRs merged
  - Number of PRs still open
  - Key themes (extracted from PR titles)
```

### US-5: File naming and output location

```
As a team member,
I want the output file to have a predictable, descriptive name,
So that I can easily find it and distinguish it from previous reports.
```

**Acceptance Criteria:**

```
Given the user runs with --slides,
When a single date is used (--date 2026-02-06),
Then the file is named: daily-report-USERNAME-2026-02-06.pptx

Given the user runs with --slides and a date range,
When --from 2026-01-26 --to 2026-02-06 is used,
Then the file is named: daily-report-USERNAME-2026-01-26_2026-02-06.pptx

Given the file already exists,
When the report runs,
Then the existing file is overwritten without prompting.

Given the user provides --slides-output PATH,
When the report runs,
Then the file is written to PATH instead of the default name.
```

### US-6: Existing Markdown output is unaffected

```
As a team member who uses the Markdown output,
I want the default behavior to remain unchanged,
So that my existing workflow is not broken.
```

**Acceptance Criteria:**

```
Given no --slides flag is provided,
When daily-report runs,
Then output is printed to stdout as Markdown (identical to current behavior).

Given --slides is provided,
When daily-report runs,
Then the Markdown is NOT printed to stdout (only the .pptx file is created),
And a message is printed to stderr indicating the file was written.
```

---

## 4. Slide Structure Specification

### Slide 1: Title Slide

| Element    | Content                                               |
|------------|-------------------------------------------------------|
| Title      | "Activity Report"                                     |
| Subtitle   | Line 1: GitHub username                               |
|            | Line 2: Date range or single date                     |

### Slides 2..N: Per-Project Slides (one per repo with activity)

| Element       | Content                                             |
|---------------|-----------------------------------------------------|
| Slide title   | Repository name (e.g., "platform")                  |
| Body          | Grouped PR listings (see below)                     |

**Body structure per project slide:**

```
Authored / Contributed
  * PR title #123 -- Merged
  * PR title #456 (original_author) -- Open (+10/-3)

Reviewed
  * PR title #789 (author_login) -- Merged

Waiting for Review
  * PR title #101 -- reviewer: alice, bob -- 5 days
```

- Sections with no items are omitted entirely (no empty headings).
- Open/Draft PRs show additions/deletions; Merged/Closed do not.
- Items are sorted by PR number within each section (consistent with current behavior).

### Slide N+1: Summary Slide

| Element    | Content                                              |
|------------|------------------------------------------------------|
| Title      | "Summary"                                            |
| Body       | Bullet list of aggregate metrics                     |

**Body content:**
```
* N PRs across M repos
* X merged, Y still open
* Key themes: feat, fix, refactor
```

### Ordering of Project Slides

- Projects are sorted alphabetically by repository name.
- This provides deterministic, predictable ordering consistent with the existing
  Markdown output's sort order.

---

## 5. Data Mapping

How existing report data structures map to slide content:

| Report Data Field              | Slide Element                    | Slide Type       |
|--------------------------------|----------------------------------|------------------|
| `user` (GitHub username)       | Title slide subtitle line 1      | Title            |
| `date_from`, `date_to`        | Title slide subtitle line 2      | Title            |
| `authored_details[].repo`     | Slide title (grouped)            | Per-project      |
| `authored_details[].title`    | Bullet text                      | Per-project      |
| `authored_details[].number`   | Bullet text (#NNN)               | Per-project      |
| `authored_details[].status`   | Bullet text (bold status)        | Per-project      |
| `authored_details[].additions`| Bullet text (+N/-M) if Open/Draft| Per-project      |
| `authored_details[].deletions`| Bullet text (+N/-M) if Open/Draft| Per-project      |
| `authored_details[].contributed` | Attribution label             | Per-project      |
| `authored_details[].original_author` | Attribution name           | Per-project      |
| `reviewed_prs[].repo`        | Slide title (grouped)             | Per-project      |
| `reviewed_prs[].title`       | Bullet text                       | Per-project      |
| `reviewed_prs[].number`      | Bullet text (#NNN)                | Per-project      |
| `reviewed_prs[].author`      | Bullet text (author)              | Per-project      |
| `reviewed_prs[].status`      | Bullet text (bold status)         | Per-project      |
| `waiting_prs[].repo`         | Slide title (grouped)             | Per-project      |
| `waiting_prs[].title`        | Bullet text                       | Per-project      |
| `waiting_prs[].number`       | Bullet text (#NNN)                | Per-project      |
| `waiting_prs[].reviewers`    | Bullet text (reviewer names)      | Per-project      |
| `waiting_prs[].days_waiting` | Bullet text (N days)              | Per-project      |
| `total_prs`                   | Summary bullet                   | Summary          |
| `len(all_repos)`             | Summary bullet                    | Summary          |
| `merged_today`               | Summary bullet                    | Summary          |
| `still_open`                 | Summary bullet                    | Summary          |
| `themes`                     | Summary bullet                    | Summary          |

### Data Grouping Logic

The current report lists PRs flat. For slides, data must be grouped by repository:

```python
# Pseudocode for grouping
projects = {}
for pr in authored_details:
    projects.setdefault(pr["repo"], {"authored": [], "reviewed": [], "waiting": []})
    projects[pr["repo"]]["authored"].append(pr)
for pr in reviewed_prs:
    projects.setdefault(pr["repo"], {"authored": [], "reviewed": [], "waiting": []})
    projects[pr["repo"]]["reviewed"].append(pr)
for pr in waiting_prs:
    projects.setdefault(pr["repo"], {"authored": [], "reviewed": [], "waiting": []})
    projects[pr["repo"]]["waiting"].append(pr)
```

---

## 6. Real-Life Usage Scenarios

### Scenario 1: Typical Bi-Weekly Report

**Actor**: Alex, a backend developer preparing for the sprint review meeting.
**Context**: It is Friday afternoon. The bi-weekly sprint review is in 1 hour. Alex
needs to present what they worked on over the past 2 weeks.

**Flow**:
1. Alex opens a terminal and runs:
   `daily-report --slides --from 2026-01-26 --to 2026-02-06`
2. The tool fetches data (takes ~6 seconds) and writes
   `daily-report-alexdev-2026-01-26_2026-02-06.pptx` to the current directory.
3. Alex uploads the file to Google Drive. It auto-converts to Google Slides.
4. Alex opens it, glances at the slides, and presents.

**Expected Outcome**: A clean deck with title slide, 3-4 project slides, and a
summary. No manual reformatting needed.

**What Could Go Wrong**:
- Network issues during data fetch -- existing retry logic handles this.
- No activity in the period -- see Scenario 4 (empty report).

### Scenario 2: Single Repo, Many PRs

**Actor**: Sam, who worked exclusively on the "platform" repo and authored 15 PRs
plus reviewed 8 more in the period.
**Context**: All activity is in one repo.

**Flow**: Sam runs the tool with `--slides --from ... --to ...`.

**Expected Outcome**: The deck has a title slide, ONE project slide for "platform"
with 23 items, and a summary slide. The single project slide may be dense.

**What Could Go Wrong**:
- The project slide has too many items to fit legibly. See Edge Case EC-3.

### Scenario 3: Many Repos, Sparse Activity

**Actor**: Jordan, who touched 8 different repos but only 1-2 PRs each.
**Context**: Cross-team work spread across many repositories.

**Flow**: Jordan runs the tool.

**Expected Outcome**: 8 project slides, each with 1-2 bullets. Clean and easy to
scan. Alphabetical ordering makes it easy to find a specific repo.

### Scenario 4: No Activity in Period

**Actor**: Pat, who was on vacation for 2 weeks.
**Context**: No PRs authored, reviewed, or waiting.

**Flow**: Pat runs the tool with `--slides`.

**Expected Outcome**: The deck has a title slide and a summary slide showing
"0 PRs across 0 repos, 0 merged, 0 still open." No project slides are created.

**What Could Go Wrong**: Nothing. An empty report is a valid report.

### Scenario 5: Custom Output Path

**Actor**: Alex, who wants to save the file to a shared team folder.

**Flow**: Alex runs:
`daily-report --slides --slides-output /shared/team/sprint-review-alex.pptx --from ...`

**Expected Outcome**: File is written to the specified path. If the parent directory
does not exist, the tool prints an error to stderr and exits with non-zero status.

---

## 7. Edge Cases

### EC-1: Empty Report (No Activity)

- **Condition**: Zero authored, reviewed, and waiting PRs.
- **Behavior**: Generate a deck with only the title slide and summary slide.
  Summary shows all zeros. No project slides.
- **Rationale**: A valid output; the user may still want to present "no activity"
  for the period.

### EC-2: Single Project

- **Condition**: All activity is in one repository.
- **Behavior**: Title slide + 1 project slide + summary slide = 3 slides total.

### EC-3: Many PRs on One Project Slide (> 15 items)

- **Condition**: A single repo has more than ~15 combined items (authored + reviewed +
  waiting).
- **Behavior**: All items are listed on one slide. The `python-pptx` library renders
  text regardless of overflow. Font size should be small enough to accommodate dense
  slides (12pt for bullets).
- **Future consideration**: If this becomes a real problem, a later enhancement could
  split into multiple slides per project. Out of scope for v1.

### EC-4: Very Long PR Title (> 100 characters)

- **Condition**: A PR title is very long.
- **Behavior**: Text wraps naturally within the text frame. No truncation -- the full
  title is shown.
- **Rationale**: Truncation loses information. Wrapping is acceptable.

### EC-5: Unicode Characters in PR Titles or Repo Names

- **Condition**: PR titles contain emoji, CJK characters, or other Unicode.
- **Behavior**: Rendered as-is. `python-pptx` supports Unicode text.

### EC-6: File Write Permission Denied

- **Condition**: The user does not have write permission to the output directory.
- **Behavior**: Print a clear error to stderr and exit with non-zero status. Do not
  silently fail.

### EC-7: python-pptx Not Installed

- **Condition**: The `python-pptx` dependency is not installed.
- **Behavior**: When `--slides` is used, print a clear error:
  `Error: python-pptx is required for --slides. Install it with: pip install python-pptx`
  Exit with non-zero status.
- **Rationale**: `python-pptx` should be an optional dependency. Users who only need
  Markdown output should not be forced to install it.

### EC-8: Output File Already Exists

- **Condition**: A file with the same name already exists.
- **Behavior**: Overwrite silently. This is standard CLI behavior and the filename
  includes the date range, making accidental overwrites unlikely.

---

## 8. Prioritized Backlog

### Must Have (v1)

| # | Item                                              | Rationale                                    |
|---|---------------------------------------------------|----------------------------------------------|
| 1 | `--slides` CLI flag                               | Core trigger for the feature                 |
| 2 | Title slide with user and date range              | Essential context for every deck             |
| 3 | Per-project slides with grouped PR listings       | The primary value of the feature             |
| 4 | Summary slide with aggregate metrics              | Quick high-level overview                    |
| 5 | Deterministic file naming (user + dates)          | Users need to find and identify files        |
| 6 | Suppress stdout Markdown when --slides is active  | Avoid confusing mixed output                 |
| 7 | stderr message confirming file written            | User feedback that the operation succeeded   |
| 8 | Graceful error when python-pptx not installed     | Optional dependency pattern                  |

### Should Have (v1 if feasible)

| # | Item                                              | Rationale                                    |
|---|---------------------------------------------------|----------------------------------------------|
| 9 | `--slides-output` custom path option              | Flexibility for team workflows               |
| 10| Clean visual styling (consistent fonts, sizes)    | Professional appearance in presentations     |

### Could Have (v2 / future)

| # | Item                                              | Rationale                                    |
|---|---------------------------------------------------|----------------------------------------------|
| 11| Color-coded status (green=Merged, yellow=Open)    | Visual polish, not essential                 |
| 12| Slide splitting for projects with >15 items       | Rare edge case, handle if it becomes real    |
| 13| Direct Google Slides API upload                   | Heavy dependency; PPTX upload works well     |
| 14| Company/team logo on title slide via config       | Nice-to-have branding                        |

### Won't Have (this iteration)

| # | Item                                              | Rationale                                    |
|---|---------------------------------------------------|----------------------------------------------|
| 15| PDF export                                        | Not requested; Google Slides can export PDF  |
| 16| HTML slide output                                 | PPTX is the standard; HTML adds complexity   |
| 17| Interactive charts/graphs                         | Disproportionate complexity for the value    |
| 18| Slide templates/themes from config                | Premature; default styling is sufficient     |

---

## 9. Items Recommended for Removal / Deferral

- **Direct Google Slides API integration**: The OAuth2 setup burden makes this
  impractical for a CLI tool. PPTX upload to Google Drive achieves the same result
  with zero configuration. Defer indefinitely unless users report friction with
  the upload step.

- **Color-coded PR statuses**: Adds visual polish but complicates the initial
  implementation. Defer to v2 after validating the basic feature works.

- **Slide splitting for dense projects**: The scenario where a single repo has >15
  items on one slide is uncommon. If it occurs, the slide is dense but still
  readable. Address only if user feedback indicates a real problem.

---

## 10. Open Questions & Assumptions

### Assumptions

1. **PPTX upload to Google Slides preserves formatting adequately.** Basic text,
   bullet lists, and font sizing convert well. Validated by common usage.
2. **`python-pptx` remains an optional dependency.** Users who do not need slides
   should not be impacted by an additional install requirement.
3. **One slide per repository is sufficient.** For typical bi-weekly reports (1-10
   PRs per repo), a single slide per repo is adequate.
4. **Overwriting existing files is acceptable.** The date-based filename provides
   sufficient uniqueness.
5. **16:9 slide aspect ratio.** Standard for modern presentations and Google Slides
   default.

### Open Questions

1. **Should the Markdown output also be written when --slides is active?** Current
   recommendation: no, to keep output clean. Users can run without --slides for
   Markdown. If this is controversial, we could add `--slides --markdown` to emit
   both.
2. **Should --slides work with --org or without it?** It should follow the same
   filtering rules as the existing Markdown output -- identical data, different format.
3. **Is there a preferred font or color scheme for the slides?** Default to clean
   sans-serif (Calibri or Arial), dark text on white background. Can be adjusted
   in v2 if the team has brand preferences.

---

## 11. Success Metrics & Validation Criteria

| Metric                                    | Target                                   |
|-------------------------------------------|------------------------------------------|
| Time to generate slide deck               | < 1 second additional over Markdown      |
| Manual formatting needed after upload     | Zero (no reformatting required)          |
| Slides render correctly in Google Slides  | 100% of text content preserved           |
| Existing Markdown workflow impact         | Zero (no changes without --slides flag)  |
| User adoption (bi-weekly presentations)   | Team members use --slides instead of manual copy |

---

## 12. Dependency: python-pptx

- **Library**: `python-pptx` (https://python-pptx.readthedocs.io/)
- **License**: MIT
- **Python compatibility**: 3.8+ (matches project requirement)
- **Install**: `pip install python-pptx`
- **Treatment**: Optional dependency. Only imported when `--slides` is used. Graceful
  error message if missing.

---

## 13. CLI Interface Changes

### New Arguments

| Argument          | Type   | Default | Description                           |
|-------------------|--------|---------|---------------------------------------|
| `--slides`        | flag   | false   | Generate .pptx slide deck             |
| `--slides-output` | string | auto    | Custom output path for .pptx file     |

### Behavior Matrix

| --slides | --slides-output | Behavior                                          |
|----------|-----------------|---------------------------------------------------|
| absent   | N/A             | Markdown to stdout (current behavior, unchanged)  |
| present  | absent          | .pptx to CWD with auto-generated filename         |
| present  | provided        | .pptx to specified path                           |

### Auto-generated Filename Pattern

```
daily-report-{username}-{date_from}[_{date_to}].pptx
```

- Single date: `daily-report-alexdev-2026-02-06.pptx`
- Date range: `daily-report-alexdev-2026-01-26_2026-02-06.pptx`
