# Slides Generation: Technology Research

**Date**: 2026-02-12
**Context**: Evaluate approaches for adding slide/presentation generation to daily-report, a Python CLI tool that currently outputs Markdown. The tool targets Python 3.8+, has minimal dependencies (only `pyyaml`), and uses `gh` CLI for GitHub API access. The user wants minimal changes to existing code.

---

## 1. Problem Statement

The daily-report tool generates a per-user GitHub activity report as Markdown text to stdout. We need to add the ability to generate presentation slides (targeting Google Slides) with per-project pages. The solution must:

- Generate slides programmatically from the same report data
- Support per-repository slide pages with PR details
- Be importable into Google Slides
- Fit the project's CLI-first, minimal-dependency philosophy
- Work offline (no mandatory network access beyond existing `gh` usage)

---

## 2. Evaluation Criteria

| Criterion | Weight | Description |
|---|---|---|
| Dependency footprint | High | Number and size of additional packages; impact on installation |
| Auth/credential complexity | High | OAuth flows, service accounts, token management |
| Offline capability | High | Must work without additional network access |
| CLI integration | High | How naturally it fits a `python -m daily_report --format slides` workflow |
| Google Slides compatibility | Medium | How easy it is to open the output in Google Slides |
| Layout customization | Medium | Control over fonts, colors, bullet styling, tables |
| Python version support | Medium | Must support Python 3.8+ |
| Maturity and maintenance | Medium | Release history, community, bus factor |
| Learning curve | Low | API complexity (one-time cost for implementation) |

---

## 3. Options Analyzed

### 3.1 python-pptx (Generate .pptx locally)

**What it is**: A pure-Python library for creating and modifying PowerPoint (.pptx) files. It operates entirely on the Open XML format, producing standard .pptx files that can be opened in PowerPoint, LibreOffice, or uploaded to Google Slides.

**Installation**: `pip install python-pptx`

**Dependencies**: `lxml`, `Pillow` (optional, for image handling), `XlsxWriter` (optional). The core dependency `lxml` is a compiled C extension but is widely available as a pre-built wheel on all major platforms.

**Dependency count**: 2 required runtime dependencies (`lxml`, `typing-extensions` on older Python). Total install size approximately 15-20 MB including `lxml`.

**Python version support**: Python 3.8+ (actively tested on 3.8 through 3.12).

**Maturity**: First released in 2013. Latest version 1.0.2 (2024). Over 4,800 GitHub stars. Used extensively in enterprise reporting. The project has a single primary maintainer (Steve Canny) but has been consistently maintained for over 10 years.

**License**: MIT -- fully compatible with any project.

**API surface for our use case**:

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()

# Title slide
slide = prs.slides.add_slide(prs.slide_layouts[0])
slide.shapes.title.text = "Daily Report -- 2026-02-12"
slide.placeholders[1].text = "username@github"

# Content slide with bullets
slide = prs.slides.add_slide(prs.slide_layouts[1])
slide.shapes.title.text = "platform"
body = slide.placeholders[1]
tf = body.text_frame
tf.text = "Authored PRs"
for pr in authored_prs:
    p = tf.add_paragraph()
    p.text = f"#{pr['number']} {pr['title']} -- {pr['status']}"
    p.level = 1
    p.font.size = Pt(14)

# Table slide
slide = prs.slides.add_slide(prs.slide_layouts[5])  # blank layout
table = slide.shapes.add_table(rows, cols, left, top, width, height).table
table.cell(0, 0).text = "Repo"
table.cell(0, 1).text = "PR"
# ...

prs.save("report.pptx")
```

**Template support**: Can load an existing .pptx as a template, inheriting its slide masters, layouts, color themes, and fonts. This allows users to provide a corporate-branded template file.

**Key capabilities**:
- Create slides with titles, subtitles, body text, bullet lists (with nesting levels)
- Add tables with cell formatting
- Control fonts, sizes, colors, alignment, bold/italic
- Use slide layouts from built-in or custom templates
- Add images, charts (via helper libraries)
- Manipulate slide masters for consistent branding

**Limitations**:
- No built-in chart generation (need `python-pptx` + data, or generate chart images separately)
- Template customization requires understanding PowerPoint's XML structure for advanced layouts
- No animation or transition support (not needed for this use case)

**Google Slides import**: Google Drive natively converts uploaded .pptx files to Google Slides format. The conversion preserves text, tables, bullet formatting, and basic styling. Fonts may fall back to Google-available equivalents. This is a well-established workflow used widely in organizations.

### 3.2 Google Slides API (google-api-python-client)

**What it is**: The official Google API client for Python, providing direct programmatic access to Google Slides. Creates presentations directly in Google Drive.

**Installation**: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`

**Dependencies**: Heavy dependency tree: `google-api-core`, `google-auth`, `googleapis-common-protos`, `protobuf`, `httplib2`, `uritemplate`, `pyasn1`, `rsa`, `cachetools`, and more. Total install size approximately 40-60 MB.

**Dependency count**: 15+ transitive dependencies.

**Python version support**: Python 3.7+.

**Maturity**: Maintained by Google. Very stable API. However, the Slides API specifically is less actively developed than Docs or Sheets APIs.

**License**: Apache 2.0 -- compatible.

**Auth complexity**: This is the major obstacle. Requires one of:
1. **OAuth 2.0 user flow**: Requires creating a Google Cloud project, enabling the Slides API, creating OAuth credentials, and going through a browser-based consent flow on first use. Produces a `credentials.json` and `token.json` that must be stored locally. On headless servers or CI environments, this flow is impractical.
2. **Service account**: Requires a service account JSON key file, domain-wide delegation setup if accessing user Drive. More complex to configure.
3. **API key**: Read-only; cannot create presentations.

**API surface for our use case**:

```python
from googleapiclient.discovery import build

service = build('slides', 'v1', credentials=creds)

# Create presentation
presentation = service.presentations().create(
    body={'title': 'Daily Report'}
).execute()
presentation_id = presentation['presentationId']

# Add a slide
requests = [
    {'createSlide': {
        'objectId': 'slide_1',
        'slideLayoutReference': {'predefinedLayout': 'TITLE_AND_BODY'},
    }},
    {'insertText': {
        'objectId': 'slide_1_title',
        'text': 'platform',
    }},
]
service.presentations().batchUpdate(
    presentationId=presentation_id,
    body={'requests': requests}
).execute()
```

**Key capabilities**:
- Create presentations directly in Google Slides
- Full control over slide elements, text, shapes, tables
- Real-time collaboration features
- Access to Google Fonts and Slides themes

**Limitations**:
- **Requires network access** to Google APIs (not just `gh`)
- **Auth is complex and invasive** for a CLI tool -- requires Google Cloud project setup, OAuth consent screen, credential files
- **Cannot work offline** -- every operation is an API call
- **Verbose API** -- the batch update API requires specifying object IDs and pixel-level positioning; creating a simple bulleted slide requires 10+ API requests
- **Rate limits** -- 60 requests per minute per user for write operations
- **Testing difficulty** -- mocking the Google API client is significantly more complex than testing file generation

### 3.3 reveal.js (HTML slides)

**What it is**: Generate an HTML file using the reveal.js presentation framework. The output is a self-contained HTML file that can be opened in any browser.

**Installation**: No Python package needed -- just generate HTML with embedded reveal.js from a CDN link, or bundle the JS/CSS.

**Dependencies**: Zero additional Python dependencies.

**API surface**: String templating / Jinja2 template rendering to produce HTML.

```python
html = f"""<!doctype html>
<html>
<head>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4/dist/theme/white.css">
</head>
<body>
  <div class="reveal"><div class="slides">
    <section><h2>Daily Report</h2><p>{date}</p></section>
    <section><h2>platform</h2><ul>
      {"".join(f"<li>{pr}</li>" for pr in prs)}
    </ul></section>
  </div></div>
  <script src="https://cdn.jsdelivr.net/npm/reveal.js@4/dist/reveal.js"></script>
  <script>Reveal.initialize();</script>
</body>
</html>"""
```

**Key capabilities**:
- Zero dependencies
- Full HTML/CSS customization
- Can be self-contained (embed JS/CSS inline)
- Renders in any browser
- Supports code syntax highlighting, markdown content

**Limitations**:
- **Cannot be imported into Google Slides** -- this is a disqualifier given the stated requirement
- Not a standard presentation format; cannot be opened in PowerPoint
- Requires a browser to view (not a standalone file in the traditional sense)
- PDF export requires a browser with print-to-PDF

### 3.4 PDF generation (reportlab, FPDF2, WeasyPrint)

**What it is**: Generate a PDF document with slide-like pages.

**Dependencies**: Varies. `fpdf2` is pure Python (~1 MB). `reportlab` requires C extensions. `WeasyPrint` requires system-level Cairo/Pango libraries.

**Key capabilities**:
- Universally viewable format
- Can produce "one page per slide" layouts
- Good for archival/printing

**Limitations**:
- **Cannot be imported into Google Slides** -- disqualifier
- PDFs are not editable presentations
- No native bullet list or slide layout abstractions -- must position everything manually
- Google Slides cannot convert PDF to editable slides

### 3.5 Markdown to PPTX via pandoc

**What it is**: Use pandoc (external binary) to convert Markdown to .pptx.

**Installation**: Requires `pandoc` system binary (not a Python package).

**Key capabilities**:
- Can reuse the existing Markdown output
- Supports `---` as slide separators
- Can use a reference .pptx template for styling

**Limitations**:
- Requires an external binary (`pandoc`) -- adds a non-Python system dependency
- Limited control over slide layout from Markdown alone
- Table formatting in converted slides is often poor
- Harder to customize per-slide content programmatically
- The Markdown output format would need restructuring with slide separators

---

## 4. Comparison Matrix

| Criterion | python-pptx | Google Slides API | reveal.js | PDF | pandoc |
|---|---|---|---|---|---|
| **Additional dependencies** | 2 (lxml, typing-ext) | 15+ | 0 | 1-3 | system binary |
| **Install size** | ~20 MB | ~50 MB | 0 | 1-15 MB | ~100 MB |
| **Auth complexity** | None | High (OAuth2) | None | None | None |
| **Offline capable** | Yes | No | Yes* | Yes | Yes |
| **CLI integration** | Excellent | Poor | Good | Good | Fair |
| **Google Slides import** | Native upload | Direct creation | Not possible | Not possible | Native upload |
| **Layout control** | High | Very high | High (CSS) | Medium | Low |
| **Template support** | Yes (.pptx) | Yes (Slides themes) | Yes (CSS) | Limited | Yes (.pptx) |
| **Table support** | Yes | Yes | HTML tables | Manual | Poor |
| **Bullet list support** | Yes (with levels) | Yes | HTML lists | Manual | Yes |
| **Font/color control** | Full | Full | Full (CSS) | Full | Limited |
| **Python 3.8+ support** | Yes | Yes | N/A | Yes | N/A |
| **Maturity** | 10+ years | Google-backed | 10+ years | Varies | 15+ years |
| **Testing ease** | Easy (file I/O) | Complex (API mock) | Easy (string) | Easy (file I/O) | Medium (subprocess) |

*reveal.js requires CDN access unless JS/CSS is bundled inline.

---

## 5. Risks and Mitigations

### python-pptx risks

| Risk | Severity | Mitigation |
|---|---|---|
| `lxml` compilation fails on exotic platforms | Low | Pre-built wheels available for all major platforms (Linux, macOS, Windows, ARM64). Fallback: use system package manager. |
| Single maintainer (bus factor) | Low | Library is mature and stable; the .pptx format does not change. Fork-ready if needed. |
| Google Slides conversion loses formatting | Low | Stick to basic formatting (text, bullets, tables, solid colors). Avoid advanced PowerPoint features. Test conversion with representative output. |
| Dependency conflicts with user environment | Low | `lxml` is a very common Python dependency; conflicts are rare. Can be installed in a virtualenv. |

### Google Slides API risks

| Risk | Severity | Mitigation |
|---|---|---|
| OAuth setup friction for CLI users | High | No good mitigation for a CLI tool. Users expect `pip install && run`, not Google Cloud Console setup. |
| Network dependency beyond `gh` | High | The tool's value proposition includes working with local git repos offline. Adding mandatory Google API access contradicts this. |
| Credential storage security | Medium | Must store OAuth tokens locally. Risks credential leakage. |
| API rate limits during batch generation | Medium | Implement request batching and backoff. |
| Google API deprecation / breaking changes | Low | Google maintains backward compatibility but has deprecated APIs before. |

---

## 6. Integration Architecture (python-pptx)

Given the recommendation below, here is how python-pptx would integrate with the existing codebase:

```
daily_report/__main__.py   (existing: pipeline + markdown output)
                            |
                            | report data (dicts)
                            v
daily_report/formatter.py   (new: format dispatch)
  |                         |
  v                         v
format_markdown()      format_pptx()
  (current logic,        (new: generates .pptx)
   extracted)
```

**Minimal changes to existing code**:
1. Extract the report-building data (lines 529-686 of `__main__.py`) into a data structure (dict or dataclass) before formatting.
2. Add a `--format` flag (`markdown` | `slides`) and `--output` flag for the file path.
3. The existing markdown formatting stays as the default path.
4. A new `format_pptx()` function generates the .pptx file using `python-pptx`.

**Slide structure per the requirements** (per-project pages):

- **Slide 1**: Title slide -- "Daily Report -- {date}" with user and org info
- **Slide 2-N**: One slide per repository with:
  - Repository name as title
  - Authored/Contributed PRs as bullet list
  - Reviewed PRs as bullet list
  - Status indicators (Merged, Open, Draft)
- **Final slide**: Summary slide with totals, key themes

**Optional template support**: Accept a `--template` flag pointing to a .pptx file. If provided, use it as the base presentation (inherits slide masters, fonts, colors). If not provided, use python-pptx defaults with reasonable styling.

**Dependency management**: Since `python-pptx` is an optional feature, it can be an optional dependency:
```
pip install daily-report[slides]
```
The import can be guarded:
```python
try:
    from pptx import Presentation
except ImportError:
    Presentation = None
    # raise helpful error only when --format slides is used
```

This means the core tool continues to work with zero additional dependencies when slides are not needed.

---

## 7. Recommendation

**Recommended approach: python-pptx**

**Rationale**:

1. **Minimal friction**: Install one package (`pip install python-pptx`), no auth setup, no cloud console, no credential management. This aligns with the project's current approach where the only external tool is `gh` CLI (already authenticated).

2. **Offline capability**: Generates a local .pptx file with no network access required (beyond the existing `gh` API calls for data gathering). This preserves the tool's ability to work in offline/restricted environments.

3. **Google Slides compatibility**: Google Drive natively imports .pptx files and converts them to Google Slides. This is a well-tested path used by millions of users. The conversion handles text, bullets, tables, and basic formatting reliably.

4. **Minimal code changes**: The existing report data can be consumed by a new formatter function. The current markdown output logic does not need to change. A new `--format slides` flag gates the new functionality.

5. **Optional dependency**: Can be structured as an optional install (`daily-report[slides]`), keeping the core tool dependency-free except for `pyyaml`.

6. **Testability**: Output is a file that can be inspected in tests by reading it back with `python-pptx` and asserting on slide count, text content, and structure. No API mocking needed.

**Why not Google Slides API**: The OAuth2 credential management is disproportionately complex for a CLI tool. It would require users to create a Google Cloud project, enable APIs, download credentials, and complete a browser-based OAuth flow -- all before generating their first slide. This contradicts the tool's current "install and run" philosophy. The Google Slides API is better suited for web applications with existing Google auth infrastructure, not standalone CLI tools.

**Why not reveal.js or PDF**: Neither format can be imported into Google Slides, which is a stated requirement.

**Why not pandoc**: Adds a system-level binary dependency and provides less control over slide layout than python-pptx.
