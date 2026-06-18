# Holiday Handling Rules

> Reference: `https://holidays-calendar.net/calendar_zh_cn/china_zh_cn.html`

## Chinese Statutory Holidays

| Holiday | 2026 Date | Days |
|---------|-----------|------|
| 元旦 | Jan 1 | 1 |
| 春节 | Lunar (Jan/Feb) | 7 |
| 清明节 | Lunar (Apr) | 1-3 |
| 劳动节 | May 1 | 1-5 |
| 端午节 | Lunar (May/Jun) | 1 |
| 中秋节 | Lunar (Sep/Oct) | 1 |
| 国庆节 | Oct 1-7 | 7 |

## Key Rules

### 1. 调休补班 Are Workdays
Makeup workdays (调休补班) are **workdays**, not holidays. Example: 2026-09-20 (Sun) and 2026-10-10 (Sat) are makeup workdays.

```python
makeup_workdays = {date(2026,9,20), date(2026,10,10)}

def is_workday(d):
    if d in makeup_workdays: return True
    if d.weekday() >= 5: return False
    return d not in holidays
```

### 2. Merge Consecutive Holidays
When holidays are adjacent (e.g., 中秋 on 9/25 followed by 国庆 10/1-7), merge them into a single continuous red strip in the Gantt chart.

```python
# After building individual strips, merge consecutive holiday strips
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
```

### 3. Weekends Within Holidays
Weekend days that fall within a holiday period (e.g., Oct 3-4, 2026 are Sat/Sun within 国庆) are classified as **holiday**, not weekend. The holiday strip takes priority.

### 4. Holiday Strip Rendering
Holiday strips use red-tinted background with higher z-index than weekend strips:

```python
# Holiday: z-index:1, red background
'background:rgba(229,57,53,0.10);border-left:2px solid rgba(229,57,53,0.30);z-index:1'

# Weekend: z-index:0, grey background
'background:rgba(148,163,184,0.06);z-index:0'

# Task bar: z-index:2, renders above both
```

### 5. 国庆节: Full 7 Days
国庆节 is Oct 1-7 (all 7 days), not 10/1-2 + 10/5-7. All 7 days are statutory holidays.

```python
# Correct
holidays = {
    date(2026,10,1), date(2026,10,2), date(2026,10,3),
    date(2026,10,4), date(2026,10,5), date(2026,10,6), date(2026,10,7),
}

# Wrong — do NOT use
holidays = {
    date(2026,10,1), date(2026,10,2),
    date(2026,10,5), date(2026,10,6), date(2026,10,7),
}
```
