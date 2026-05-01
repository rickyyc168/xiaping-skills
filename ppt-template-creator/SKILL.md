---
name: PPT Template Creator
slug: ppt-template-creator
version: 3.0.0
description: "Complete PPT design system + toolkit. Parse existing templates to JSON, generate from declarative specs, inject content into templates. Includes 5 standard page types with layout options, 5-color theme contract, 4 visual style recipes, typography hierarchy, page badges, QA verification loop. Use when creating, editing, or analyzing PowerPoint presentations."
metadata:
  clawdbot:
    emoji: "🎨"
    requires:
      bins: [python3]
      pip: [python-pptx]
    os: [linux, darwin, win32]
---

# PPT Template Creator — Design System + Toolkit

## Core Workflow (Mandatory)

```
1. Requirement Analysis  →  topic, audience, purpose, tone, slide count
2. Outline Planning      →  classify each slide as ONE of 5 page types
3. Style Selection       →  pick palette + visual style recipe
4. Generate              →  build slides following design system
5. QA Verification       →  extract text → review → fix → re-verify
```

**Skip steps = bad output. Follow the flow.**

---

## 1. Requirement Analysis (Before Any Code)

Answer these before touching code:
- **Topic**: What is this about?
- **Audience**: Who reads this? (executives / clients / students / public)
- **Purpose**: Persuade / inform / report / pitch / teach
- **Tone**: Corporate / creative / minimal / bold
- **Slide count**: How many pages?
- **Visual assets**: Any images, charts, data available?

---

## 2. Five Standard Page Types

**Classify EVERY slide as exactly ONE type.** Plan content before building.

### Type A: Cover Page
- **Purpose**: Opening + tone setting
- **Content**: Big title, subtitle/presenter, date, strong visual
- **Font sizes**: Title 40-48pt, subtitle 18-24pt, meta 12-14pt
- **Layouts**: Asymmetric (text+image), Center-aligned, Full-bleed background
- **Rules**: Title must be 2x+ larger than subtitle. No page badge.

### Type B: Table of Contents
- **Purpose**: Navigation + expectation setting
- **Content**: 3-6 section list (optional icons/page numbers)
- **Font sizes**: Page title 28-36pt, section number 24-28pt, section title 18-22pt
- **Layouts**: Numbered vertical list, Two-column grid, Sidebar navigation, Card grid
- **Rules**: Section numbers visually prominent. Scannable in 2-3 seconds.

### Type C: Section Divider
- **Purpose**: Clear transitions between major parts
- **Content**: Section number + title + optional 1-2 line intro
- **Font sizes**: Number 48-72pt, title 28-36pt, intro 14-16pt
- **Layouts**: Bold center, Left with accent block, Split background, Full-bleed
- **Rules**: Number is most prominent. Minimal content — generous whitespace.
- **Must differ from content slides** (different bg color, more whitespace).

### Type D: Content Page
- **Purpose**: Deliver information
- **Subtypes** (pick one per slide):
  - **Text**: Bullets/quotes — MUST add icons or shapes, never plain text only
  - **Mixed media**: Two-column text + image
  - **Data viz**: Chart + key takeaways + source citation
  - **Comparison**: Side-by-side cards (A vs B, pros/cons)
  - **Timeline/Process**: Steps with arrows or flow
  - **Image showcase**: Hero image + caption
- **Font sizes**: Title 28-36pt, body 14-16pt, captions 10-12pt, stat callouts 48-60pt
- **Rules**:
  - Body text LEFT-ALIGNED, never center
  - Title must be 36pt+ to stand out from 14-16pt body
  - **Every content slide needs at least one non-text visual element** (icon, shape, chart, image)
  - Min margins 0.5", min gap between blocks 0.3"
  - **Vary layouts** — never repeat same layout on consecutive slides

### Type E: Summary / Closing
- **Purpose**: Wrap-up + action
- **Content**: Key takeaways, CTA/next steps, contact, thank-you
- **Font sizes**: Title 36-48pt, items 16-20pt, contact 14-16pt
- **Layouts**: Key takeaways list, CTA/next steps, Thank you/contact, Split recap
- **Rules**: Strong closing statement. Items scannable (one line each).
- **Energy should match cover page.**

---

## 3. Theme Contract — 5-Color System

**Always define these 5 keys. Never use other names.**

| Key | Role | Example |
|---|---|---|
| `primary` | Darkest — titles, headers | `1A1A2E` |
| `secondary` | Dark accent — body text, borders | `4A4E69` |
| `accent` | Mid highlight — badges, dividers, icons | `E94560` |
| `light` | Light accent — backgrounds, cards | `C9ADA7` |
| `bg` | Page background | `F2E9E4` |

Color format: 6-char hex **WITHOUT** `#` (e.g., `"FF0000"` not `"#FF0000"`).
Reason: `#` causes file corruption in some PPT generators.

### Palette Suggestions by Tone

| Tone | primary | secondary | accent | light | bg |
|---|---|---|---|---|---|
| Corporate | `1A1A2E` | `16213E` | `0F3460` | `E8E8E8` | `FFFFFF` |
| Creative | `22223B` | `4A4E69` | `9A8C98` | `C9ADA7` | `F2E9E4` |
| Bold | `0D0D0D` | `1A1A2E` | `E94560` | `F5F5F5` | `FFFFFF` |
| Nature | `2D5016` | `3E6B23` | `E8A838` | `E8F0E0` | `F8FBF5` |
| Ocean | `0B2545` | `13315C` | `137CBD` | `A8DADC` | `EDF6F9` |

---

## 4. Visual Style Recipes

Pick ONE style and use consistently:

### Sharp (Corporate / Professional)
- Rectangles, no rounded corners
- Thin borders (1-2pt), clean lines
- Bold sans-serif headers
- Structured grids, strict alignment

### Soft (Modern / Approachable)
- Rounded rectangles (rectRadius 0.1-0.15)
- Soft shadows, generous whitespace
- Medium-weight headers
- Flexible layouts, more breathing room

### Minimal (Clean / Elegant)
- Minimal shapes — mostly text + whitespace
- Thin accent lines (not under titles!), subtle dividers
- Light font weights for body
- Large whitespace ratios

### Bold (Creative / Impactful)
- Large blocks of color
- Thick borders, strong contrast
- Extra-bold headers, large stat callouts
- Asymmetric layouts, visual weight shifts

---

## 5. Typography Hierarchy

| Element | Size Range | Weight | Alignment |
|---|---|---|---|
| Cover title | 40-48pt | Bold | Center |
| Slide title | 28-36pt | Bold | Left |
| Section header | 20-24pt | Bold | Left |
| Body text | 14-16pt | Regular | **Left** (never center) |
| Caption/source | 10-12pt | Regular/Muted | Left |
| Stat callout | 48-60pt | Extra Bold | Center or Left |

**Font pairing**:
- Chinese: 微软雅黑 (Microsoft YaHei)
- English: Arial (default), Helvetica, Inter
- Use ONE font family per presentation. Vary weight/size for hierarchy.

**Critical rules**:
- Title vs body contrast: title must be **2x+ body size**
- Never let adjacent text be within 20% size of each other
- Body paragraphs NEVER center-aligned

---

## 6. Page Number Badges

All slides **except Cover** MUST include a page badge (bottom-right).

```
Circle badge:  x: 9.3", y: 5.1", w: 0.4", h: 0.4"
Pill badge:    x: 9.1", y: 5.15", w: 0.6", h: 0.35"
```

Use `accent` color background, white text, bold, 11-12pt.
Show current number only (`3`), NOT `3/12`.

---

## 7. QA Verification Loop (Mandatory)

**Assume there are problems. Your job is to find them.**

### Content QA
```bash
python -m markitdown output.pptx    # extract text
python -m markitdown output.pptx | grep -iE "lorem|ipsum|placeholder|xxxx"
```

### Visual QA
- [ ] No repeated layouts on consecutive slides
- [ ] Every content slide has a non-text visual element
- [ ] Titles 36pt+ body 14-16pt — clear size contrast
- [ ] Body text left-aligned
- [ ] No leftover placeholder text
- [ ] Page badges present (except cover)
- [ ] Colors consistent with theme contract
- [ ] Margins ≥ 0.5", gaps ≥ 0.3"
- [ ] Aspect ratio correct (16:9 default)

### Fix-and-Verify Loop
1. Generate → Extract text → Review
2. List ALL issues found (if zero, look harder)
3. Fix issues
4. **Re-verify affected slides** (one fix often breaks another)
5. Repeat until clean pass

**Do not declare success until at least one fix-verify cycle completed.**

---

## 8. Anti-Patterns — DO NOT

- ❌ Repeat same layout across slides — vary columns, cards, callouts
- ❌ Center body text — left-align paragraphs and lists
- ❌ Skip size contrast — titles 36pt+ vs body 14pt
- ❌ Default to blue — pick colors matching topic
- ❌ Mix spacing randomly — pick 0.3" or 0.5" and stick with it
- ❌ Plain text-only slides — add icons, shapes, charts
- ❌ Accent lines under titles — "hallmark of AI-generated slides"
- ❌ `#` with hex colors — corrupts PPTX files
- ❌ One layout per slide — wasteful, no consistency
- ❌ Ignore aspect ratio — 16:9 vs 4:3 shifts everything

---

## 9. Toolkit Commands

```bash
TOOLKIT="python3 SKILL_DIR/ppt_toolkit.py"

# Parse existing PPT → JSON (extract all styles)
$TOOLKIT parse template.pptx -o styles.json

# Generate from JSON spec
$TOOLKIT generate spec.json -o output.pptx

# Inject content into template (preserve styles)
$TOOLKIT inject template.pptx content.json -o result.pptx

# Demo (7-slide Chinese presentation with all page types)
$TOOLKIT demo -o demo.pptx

# QA: extract and verify text
python -m markitdown output.pptx
```

### JSON Spec Format

```json
{
  "name": "My Deck",
  "width_inches": 13.333,
  "height_inches": 7.5,
  "theme": {
    "primary": "1A1A2E", "secondary": "16213E",
    "accent": "E94560", "light": "F5F5F5", "bg": "FFFFFF"
  },
  "layouts": [
    {
      "name": "Cover",
      "type": "cover",
      "bg": "1A1A2E",
      "text_color": "FFFFFF",
      "elements": [
        {"type": "title", "left": 0.8, "top": 2.0, "width": 11.7, "height": 1.5,
         "font_size": 44, "bold": true, "align": "center"},
        {"type": "subtitle", "left": 0.8, "top": 3.8, "width": 11.7, "height": 0.8,
         "font_size": 20, "align": "center"}
      ]
    }
  ],
  "slides": [
    {"layout": 0, "title": "Title", "subtitle": "Sub | Date"}
  ]
}
```

Element types: `title`, `subtitle`, `body` (text or list), `text`, `rect`, `divider`, `image`, `table`

### Inject Content Modes

**By shape name** (precise):
```json
{"slides": [{"shapes": [{"name": "TextBox 1", "text": "New title"}]}]}
```

**By index** (simple):
```json
{"slides": [{"texts": ["New title", "New body"]}]}
```

---

## 10. Integration

- **powerpoint-pptx**: Edit/QA existing decks
- **This skill**: Design system + template creation + content injection
- **Flow**: User sends template → parse → plan layouts → generate/inject → QA → deliver
