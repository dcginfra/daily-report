# daily_report

Daily GitHub PR report generator. Uses local git repos and GitHub GraphQL API to gather authored, contributed, reviewed PRs and pending review requests across a GitHub organization.

## Prerequisites

- Python 3.8+
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated
- [PyYAML](https://pypi.org/project/PyYAML/) (`pip install pyyaml`) — required for config file support

## Usage

```bash
# Default: all orgs, authenticated user, today
python -m daily_report

# Specific date
python -m daily_report --date 2026-02-10

# Date range (inclusive)
python -m daily_report --from 2026-02-01 --to 2026-02-07

# Filter to a specific org
python -m daily_report --org dashpay

# Different org and user
python -m daily_report --org myorg --user someone

# Use local git repos from a directory (fastest mode)
python -m daily_report --repos-dir ~/git

# Use a custom config file
python -m daily_report --config ~/.config/daily-report/repos.yaml

# Force API-only mode (skip local git)
python -m daily_report --no-local

# Generate a .pptx slide deck (requires: pip install python-pptx)
python -m daily_report --slides --from 2026-01-26 --to 2026-02-06

# Specify a custom output path for the slide deck
python -m daily_report --slides --slides-output ~/presentations/sprint-review.pptx --from 2026-01-26 --to 2026-02-06
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--org` | *(none — all orgs)* | GitHub organization to report on |
| `--user` | authenticated `gh` user | GitHub username to report for |
| `--date` | today | Single date in `YYYY-MM-DD` format; mutually exclusive with `--from`/`--to` |
| `--from` | *(none)* | Start of date range in `YYYY-MM-DD` format (requires `--to`) |
| `--to` | *(none)* | End of date range in `YYYY-MM-DD` format (requires `--from`) |
| `--config` | `~/.config/daily-report/repos.yaml` | Path to YAML config file |
| `--repos-dir` | *(none)* | Scan directory for git repos, filters by `--org` if given (overrides config repos list) |
| `--git-email` | *(none)* | Additional git author email for commit matching |
| `--no-local` | `false` | Skip local git discovery, use GraphQL-only mode |
| `--slides` | `false` | Generate `.pptx` slide deck instead of Markdown output |
| `--slides-output` | *(auto-generated)* | Custom output path for `.pptx` file (requires `--slides`) |

`--date` and `--from`/`--to` are mutually exclusive. When neither is provided, defaults to today.

## Slides Export

The `--slides` flag generates a `.pptx` (PowerPoint) slide deck instead of the default Markdown output. This is useful for bi-weekly sprint presentations — the generated file can be uploaded directly to Google Slides via Google Drive or "File > Import slides".

**Requires** the optional `python-pptx` dependency:

```bash
pip install python-pptx
```

If `python-pptx` is not installed, using `--slides` prints a clear error message and exits.

The slide deck contains:

1. **Title slide** — "Activity Report" with the GitHub username and date range.
2. **Per-project slides** — one slide per repository with activity, listing authored/contributed PRs, reviewed PRs, and PRs waiting for review under grouped subheadings.
3. **Summary slide** — aggregate metrics (total PRs, repos, merged count, open count, key themes).

By default, the output file is written to the current directory with the name `daily-report-{user}-{date}.pptx` (or `daily-report-{user}-{from}_{to}.pptx` for date ranges). Use `--slides-output` to specify a custom path.

## Configuration

Create `~/.config/daily-report/repos.yaml` to enable local git commit discovery:

```yaml
default_org: dashpay

repos:
  - path: ~/git/platform
  - path: ~/git/tenderdash
  - path: ~/git/dash-evo-tool

# Optional: bots to exclude from reviewer lists
excluded_bots:
  - coderabbitai
  - copilot-pull-request-reviewer
  - github-actions
  - copilot-swe-agent
```

The `org` and `name` for each repo are auto-detected from the git remote URL. You can override them explicitly:

```yaml
repos:
  - path: ~/git/platform
    org: dashpay
    name: platform
```

Alternatively, use `--repos-dir ~/git` to auto-discover all repos in a directory, filtered by `--org` if given.

## How it works

The tool uses a three-phase pipeline:

1. **Local git commit discovery** — scans locally cloned repos for commits by the user within the date range, then maps commits to PRs via commit message parsing and GraphQL batch queries. Falls back to GraphQL search for repos not cloned locally.
2. **Review discovery** — a single GraphQL search finds PRs where the user has review or comment activity, with inline date verification.
3. **PR enrichment** — a batch GraphQL query fetches details (state, merged date, additions/deletions) for all discovered PRs in one call.

This replaces the previous approach of ~100 individual REST API calls with ~5-7 GraphQL calls, reducing runtime from ~50 seconds to ~7 seconds. Local git discovery also catches PRs that the API search misses (e.g., bot-authored PRs where the user has commits).

Without a config file or `--repos-dir`, the tool runs in GraphQL-only mode — still significantly faster than the old REST approach.
