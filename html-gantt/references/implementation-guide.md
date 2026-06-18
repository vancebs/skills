# Implementation Guide — HTML Gantt Chart

> Complete Python script for generating hand-crafted HTML Gantt charts.

## Full Generation Script

```python
from datetime import date, timedelta

# ===== CONFIGURATION =====
tasks = [
    ("Task Name", "Category", workday_count),
    # ...
]

holidays = {
    date(2026,6,19),   # 端午节
    date(2026,9,25),   # 中秋节
    date(2026,10,1), date(2026,10,2), date(2026,10,3),
    date(2026,10,4), date(2026,10,5), date(2026,10,6), date(2026,10,7),
}
makeup = {date(2026,9,20), date(2026,10,10)}  # 调休补班

def is_workday(d):
    if d in makeup: return True
    if d.weekday() >= 5: return False
    return d not in holidays

def is_holiday(d): return d in holidays

def add_workdays(start, n):
    d, count = start, 0
    while count < n:
        if is_workday(d): count += 1
        if count < n: d += timedelta(days=1)
    return d

# ===== SCHEDULE CALCULATION =====
start_date = date(2026, 6, 22)
current = start_date
task_dates = []
for name, dept, days in tasks:
    end = add_workdays(current, days)
    task_dates.append((name, dept, days, current, end))
    current = end + timedelta(days=1)
    while not is_workday(current):
        current += timedelta(days=1)

first_start = task_dates[0][3]
last_end = task_dates[-1][4]
total_calendar_days = (last_end - first_start).days + 1

def position_pct(d):
    """Calendar day as percentage of total timeline."""
    return ((d - first_start).days / total_calendar_days) * 100

def width_pct(days):
    """Calendar day span as percentage of total timeline."""
    return (days / total_calendar_days) * 100

# ===== CATEGORY COLORS =====
dept_colors = {
    'CategoryA': ('#DBEAFE', '#1E40AF', '#2563EB'),  # (bg, text, border)
    'CategoryB': ('#D1FAE5', '#065F46', '#059669'),
    # Add more as needed
}

# ===== BUILD NON-WORKDAY STRIPS =====
strips = []
d = first_start
while d <= last_end:
    if not is_workday(d):
        kind = 'holiday' if is_holiday(d) else 'weekend'
        start = d
        while d <= last_end and not is_workday(d) and (is_holiday(d) if kind == 'holiday' else not is_holiday(d)):
            d += timedelta(days=1)
        strips.append((kind, start, d - timedelta(days=1)))
    else:
        d += timedelta(days=1)

# Merge consecutive holiday strips
merged = []
i = 0
while i < len(strips):
    kind, s, e = strips[i]
    if kind == 'holiday':
        j = i + 1
        while j < len(strips) and strips[j][0] == 'holiday':
            e = strips[j][2]
            j += 1
        merged.append(('holiday', s, e))
        i = j
    else:
        merged.append(('weekend', s, e))
        i += 1

# ===== GENERATE STRIP HTML =====
strip_html = []
for kind, s, e in merged:
    left = position_pct(s)
    width = width_pct((e - s).days + 1)
    days_str = ' '.join((s + timedelta(days=x)).strftime('%m/%d') for x in range((e - s).days + 1))
    if kind == 'holiday':
        strip_html.append(
            f'<div title="{days_str} 节假日" '
            f'style="position:absolute;left:{left:.3f}%;width:{width:.3f}%;'
            f'top:0;bottom:0;background:rgba(229,57,53,0.10);'
            f'border-left:2px solid rgba(229,57,53,0.30);'
            f'z-index:1;pointer-events:none"></div>'
        )
    else:
        strip_html.append(
            f'<div title="{days_str} 周末" '
            f'style="position:absolute;left:{left:.3f}%;width:{width:.3f}%;'
            f'top:0;bottom:0;background:rgba(148,163,184,0.06);'
            f'z-index:0;pointer-events:none"></div>'
        )

# ===== MONTH HEADERS =====
month_labels = []
month_dividers = []
m = date(first_start.year, first_start.month, 1)
while m <= last_end:
    month_labels.append(
        f'<div style="position:absolute;left:{position_pct(m):.3f}%;'
        f'transform:translateX(-2px);font-size:11px;font-weight:600;'
        f'color:#5f6368;letter-spacing:.3px">{m.month}月</div>'
    )
    month_dividers.append(
        f'<div style="position:absolute;left:{position_pct(m):.3f}%;'
        f'top:0;bottom:0;border-left:1px dashed #d0d4da;z-index:0"></div>'
    )
    m = date(m.year + (1 if m.month == 12 else 0), (m.month % 12) + 1, 1)

# ===== GENERATE TASK ROWS =====
task_rows = []
for name, dept, days, start, end in task_dates:
    bg, tc, border = dept_colors.get(dept, ('#F3F4F6', '#374151', '#9CA3AF'))
    left = position_pct(start)
    width = width_pct((end - start).days + 1)

    task_rows.append(f'''      <div style="display:flex;height:36px;margin-bottom:3px;border-radius:6px;background:#fff;border:1px solid #e8eaf0;overflow:hidden">
        <div style="width:170px;min-width:170px;display:flex;flex-direction:column;justify-content:center;padding:0 8px 0 12px;border-left:4px solid {border};gap:1px">
          <span style="font-size:12px;font-weight:700;color:{tc};line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{name}</span>
          <span style="font-size:10px;color:#9aa0a6">（{dept} · {days}d）</span>
        </div>
        <div style="flex:1;position:relative;overflow:hidden;background:#fafbfe">
          {"".join(month_dividers)}
          {"".join(strip_html)}
          <div title="{name}  {start.strftime('%m/%d')} ~ {end.strftime('%m/%d')}" style="position:absolute;left:{left:.3f}%;width:{width:.3f}%;top:6px;bottom:6px;background:{bg};border:1.5px solid {border};border-radius:5px;display:flex;align-items:center;justify-content:center;z-index:2;overflow:hidden;cursor:default">
            <span style="font-size:10px;font-weight:700;color:{tc};white-space:nowrap;padding:0 4px">{days}d</span>
          </div>
        </div>
      </div>''')

# ===== ASSEMBLE GANTT BLOCK =====
gantt_html = f'''  <div style="overflow-x:auto;margin-top:4px">
    <div style="min-width:860px">

      <div style="display:flex;height:26px;margin-bottom:2px">
        <div style="width:170px;min-width:170px"></div>
        <div style="flex:1;position:relative">{"".join(month_labels)}</div>
      </div>

{"".join(task_rows)}

    </div>
  </div>'''

# ===== INTEGRATE INTO HTML PAGE =====
with open('page.html', 'r') as f:
    html = f.read()

old_start = '<div class="mermaid"'
old_end = '<!-- 关键风险 -->'
s = html.index(old_start)
e = html.index(old_end)

html = html[:s] + gantt_html + '\n</div>\n\n' + html[e:]

assert html.count('<div') == html.count('</div'), "UNBALANCED DIV TAGS"

with open('page.html', 'w') as f:
    f.write(html)
```
