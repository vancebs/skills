---
name: html-gantt
description: Use when creating or modifying an HTML Gantt chart for project scheduling — tasks with start dates, durations, weekend/holiday markers, and department color coding. Triggers on "make a Gantt chart", "add a project timeline in HTML", "create a schedule visualization", or building hand-crafted CSS Gantt.
---

# HTML Gantt Chart

## Overview

Create self-contained, hand-crafted HTML Gantt charts that render correctly without external JS dependencies. Calendar-based timeline with weekend grey strips, holiday red strips, and color-coded task bars by category.

## Core Principles

1. **Calendar-based timeline**: Task bars span from start date to end date (inclusive of non-workdays in between).
2. **No gaps between tasks**: The next task starts on the next workday after the previous task ends.
3. **Non-workday strips as overlays**: Weekend (grey) and holiday (red) strips overlay the timeline.
4. **Holiday priority**: Holiday strips merge into continuous blocks and render above weekend strips.
5. **Color coding by category**: Each department/team gets distinct fill + text + border colors.

## When to Use

- Creating a project schedule Gantt chart embedded in an HTML page
- Replacing a mermaid.js Gantt with native HTML/CSS for offline/Teams compatibility
- Visualizing tasks with start dates, durations, and department/category color coding
- Building a timeline that accurately shows weekend and holiday non-workday strips

**Do NOT use for:**
- Interactive Gantt charts requiring drag-and-drop or real-time editing
- Simple text-based task lists that don't need a timeline visualization
- Charts that can use mermaid.js in a live-rendering environment (e.g., GitHub markdown)

## Holiday Data

Reference holiday calendar at `https://holidays-calendar.net/calendar_zh_cn/china_zh_cn.html`. Key rules:

- Chinese statutory holidays: 元旦(1/1), 春节(lunar), 清明节(lunar), 劳动节(5/1), 端午节(lunar), 中秋节(lunar), 国庆节(10/1-7)
- 调休补班 (makeup workdays) are **workdays**, NOT holidays
- Consecutive holidays merge into a single red strip
- Weekends within a holiday period are classified as holiday, not weekend

See `references/holiday-handling.md` for detailed rules and examples.

## Quick Reference

| Concept | Implementation |
|---------|----------------|
| Task definition | `(name, category, workday_count)` tuple |
| Calendar positioning | `position_pct(d) = (d - first_start).days / total_calendar_days * 100` |
| Task bar width | Calendar days from start to end (includes non-workdays between) |
| Weekend strip | `background:rgba(148,163,184,0.06)` at z-index:0 |
| Holiday strip | `background:rgba(229,57,53,0.10)` at z-index:1 |
| Task bar | z-index:2, `border-radius:5px`, category-specific colors |

## Core Algorithm

See `references/implementation-guide.md` for the complete Python generation script.

### Workday Calculation

```python
def is_workday(d):
    if d in makeup_workdays: return True
    if d.weekday() >= 5: return False
    return d not in holidays

def add_workdays(start, n):
    d, count = start, 0
    while count < n:
        if is_workday(d): count += 1
        if count < n: d += timedelta(days=1)
    return d
```

### Schedule Calculation

```python
current = start_date
for name, dept, days in tasks:
    end = add_workdays(current, days)
    task_dates.append((name, dept, days, current, end))
    current = end + timedelta(days=1)
    while not is_workday(current):
        current += timedelta(days=1)
```

### HTML Row Template

Each task row uses a flex container with two columns:
```
[170px label | flex timeline with positioned bars and strips]
```

See `references/implementation-guide.md` for the complete HTML template.

## Category Color Palette

```python
dept_colors = {
    'PMO':     ('#DBEAFE', '#1E40AF', '#2563EB'),  # (bg, text, border) - blue
    'VAL':     ('#D1FAE5', '#065F46', '#059669'),  # green
    'HW':      ('#FEF3C7', '#92400E', '#D97706'),  # amber
    'ME':      ('#EDE9FE', '#6D28D9', '#7C3AED'),  # purple
    'Quality': ('#CCFBF1', '#134E4A', '#0D9488'),  # teal
    'NPI':     ('#FEE2E2', '#991B1B', '#DC2626'),  # red
    'General': ('#DBEAFE', '#1E40AF', '#2563EB'),  # blue
}
```

## Integration Into HTML Page

```python
with open('page.html', 'r') as f:
    html = f.read()

old_start = '<div class="mermaid"'
old_end = '<!-- 关键风险 -->'
s = html.index(old_start)
e = html.index(old_end)

html = html[:s] + gantt_html + '\n</div>\n\n' + html[e:]

assert html.count('<div') == html.count('</div'), "UNBALANCED DIV TAGS"
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using mermaid.js for Gantt in HTML | Hand-craft HTML/CSS — mermaid fails in offline/Teams scenarios |
| Workday-only timeline positioning | Use calendar-based timeline; task bars span all days from start to end |
| Holiday strips don't overlap weekends | Holiday z-index:1, weekend z-index:0, task bar z-index:2 |
| 国庆节 written as 10/1-2, 10/5-7 | Use full 10/1-7 (all 7 days are statutory) |
| 调休补班 marked as holiday | Makeup workdays are workdays, not holidays |
| Div tags unbalanced after replacement | Verify `html.count('<div') == html.count('</div')` after replacement |
