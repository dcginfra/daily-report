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
        for d in report.authored_prs:
            stats = ""
            if d.status in ("Open", "Draft"):
                stats = f" (+{d.additions}/\u2212{d.deletions})"
            author_info = ""
            if d.contributed and d.original_author:
                author_info = f" ({d.original_author})"
            lines.append(
                f"- `{d.repo}` \u2014 {d.title} #{d.number}{author_info} \u2014 **{d.status}**{stats}"
            )
    else:
        lines.append("_No authored or contributed PRs._")
    lines.append("")

    # Reviewed / Approved PRs
    lines.append("**Reviewed / Approved PRs**")
    lines.append("")
    if report.reviewed_prs:
        for pr in report.reviewed_prs:
            lines.append(
                f"- `{pr.repo}` \u2014 {pr.title} #{pr.number} ({pr.author}) \u2014 **{pr.status}**"
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
                f"- `{w.repo}` \u2014 {w.title} #{w.number} \u2014 reviewer: {reviewer_names} \u2014 since {w.created_at} ({w.days_waiting} days)"
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
