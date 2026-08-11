---
name: visualize-chart
description: "Chart skill. Decides when a chart helps, picks the type from the data shape, and renders exactly one chart per question."
tags: [chart, visualization]
version: "1.0.0"
---

# Visualize Chart (Trigger)

Routes chart requests to `visualize_chart`. Sibling to the analyst skill —
same SQL discipline, same filter and entity contract — but renders the
answer's data instead of only tabulating it.

Load the project's entity/filter context files before building chart SQL,
exactly as the analyst skill requires. A chart built on the wrong entity or
the wrong filter code is not a chart problem, it is a wrong answer with a
picture attached.

## CAPTURE
Lock `{widget_type, widget_title, source of rows}`.

- The chart's rows are the **answer's own rows**. Never write a second,
  differently-filtered query for the picture.
- Column order is the axis contract: X first, Y second, an optional series
  third. `SELECT periode, jumlah` charts `periode` on X and `jumlah` on Y.
- **A chart reads exactly three columns.** There is no fourth. More than three
  is refused, not truncated.
- Title in the answer's language, describing the data rather than the request.

Pick the source by what the data *is*:

1. **The SQL you already ran** — the default. `sql=` reuses the cached result
   of that exact query, so the chart shows the numbers your text quotes.
2. **The CSV this turn exported** — for values a query cannot return, such as a
   forecast's projection. Pass no `sql=` and no `data=`, and name the columns
   to plot. Nothing is retyped, so chart, download and text cannot disagree.
3. **`data=`+`columns=`** — last resort, for values neither exported nor
   queryable.

**An export failure never cancels the chart.** The CSV and the chart are
separate outcomes. If the export fails, say so about the *download* and chart
from SQL anyway. Never report "no chart" because a file could not be written.

## RUN
Call `visualize_chart(widget_type, widget_title, sql=...)` **once**.

Trigger rules — **a chart is part of a data answer, not an extra**. Treat this
the way `run_forecast` is treated: the user does not ask for the tool by name,
the skill decides from the question. Default to charting.

- **Any answer that carries data** — counts over time, comparisons across
  categories, breakdowns, rankings, compositions, distributions — gets exactly
  one chart, whether or not the user said "grafik".
- **Explicit request** — the user says grafik, chart, plot, visual, diagram.
  Always chart; never answer such a request with a table alone.
- **Skip the chart only when there is nothing to draw**:
  - the answer is definitional or explanatory — what a term means, how two
    things differ, how a process works — prose, with no data behind it
  - the answer is a single figure with nothing to compare it against, and the
    figure reads better as a sentence than as a `big_number` tile
  - the result is a record lookup or an identifier listing the user will read
    row by row
  - zero rows, or a shape no chart type fits honestly
- **When in doubt, chart it.** A redundant chart costs a glance; a missing one
  costs the reader the shape of their own data.

Type selection — read the question for the intent, then the data for the shape:

| What the answer is about | Type |
|---|---|
| a trend over periods | `line_chart` |
| several trends over periods | `grouped_line_chart` |
| cumulative or volume over time | `area_chart` |
| comparison across categories | `bar_chart` |
| the same categories split by a second dimension | `grouped_bar_chart` |
| categories with long labels | `horizontal_bar_chart` |
| share of one whole, few slices | `pie_chart` |
| a value across two dimensions at once | `heatmap` |
| two quantitative columns compared | `scatter_plot` |
| spread within categories | `box_plot` |
| nested part-of-whole | `treemap` |
| a single scalar | `big_number` |

**Each type fixes its X axis.** `line_chart`, `area_chart` and
`grouped_line_chart` plot X as a *date*, so periods must be ISO — `2024-01-01`,
or `2024-01` for months. A label like a month name or `Q1` collapses that axis;
put it on a `bar_chart`, whose X takes any text. `scatter_plot` needs a number
on X.

### Charting more than one series

When the answer covers several codes, statuses or segments, the chart shows
**all of them**, not just the total. Charting one metric out of five throws
away most of what the answer says.

The third column does this: it splits the chart into one series per distinct
value, each in its own colour with a legend naming it. One line becomes several.

That requires **long** form. Answers are usually written wide, one column per
code:

| periode | kode A | kode B | kode C | total |
|---|---|---|---|---|

That shape cannot be charted — only three columns are read, so everything past
the third would vanish. Reshape so each code becomes rows tagged in one series
column:

```sql
SELECT periode, 'kode A' AS seri, kode_a AS jumlah FROM t
UNION ALL
SELECT periode, 'kode B' AS seri, kode_b AS jumlah FROM t
ORDER BY 1, 2
```

Then chart `[periode, jumlah, seri]` as `grouped_line_chart` over periods, or
`grouped_bar_chart` across categories. Usually the long form is the *natural*
query — a `GROUP BY periode, kode` — and the wide table is only how it was
written up for reading.

Chart the total **or** the breakdown, never both in one chart: a total plotted
beside its own parts dwarfs them. Beyond roughly eight series the tool keeps
the largest and says so.

If the tool returns `## Kesalahan` → the shape or the SQL is wrong, and the
message names which. Act on the reason; do not retry the same call. A shape
refusal means the chart would have rendered *wrong*, not that it failed.
If it returns `No rows to chart.` → answer in text, do not force a chart.

## PRESENT
- Lead with the finding in words, as the analyst skill requires. The chart
  supports the sentence; it does not replace it.
- Do **not** repeat the chart's table as markdown. If exact figures matter,
  a short table of the key rows is fine — not the full dataset twice.
- Mention any limit the tool reported (top-N bucketing, downsampling) when it
  changes how the chart should be read.

## Hard rules

- **One chart per question — but one chart carries many series.** "One chart"
  is a limit on pictures, never on content: a single `grouped_line_chart`
  showing four codes is one chart. Choose the most informative chart, then make
  it as complete as its three columns allow. A second call is refused by the
  tool.
- **Never re-type tool output into `data=`/`columns=`.** Transcribing numbers
  risks a picture that disagrees with the text — the same rule the CSV store
  contract already applies to `upload_to_s3`. Chart computed results by
  charting the **exported CSV** instead: those rows are the exact ones the
  download carries, so nothing is retyped and the computed values still appear.
  If no CSV was exported, chart the queryable part from SQL and say plainly
  which part the picture covers — never drop the chart entirely.
- **Chart follows the answer's filters.** Same counting entity, same status and
  category codes, same date range. If you cannot reuse the answer's rows, do
  not chart.
- **The chart is not the export.** The CSV store contract is unchanged: a chart
  never replaces `upload_to_s3`, and calling one does not excuse skipping the
  other when the answer carries data.
