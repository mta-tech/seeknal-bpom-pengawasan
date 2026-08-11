---
name: visualize-chart
description: "Chart skill. Decides when a chart helps, picks the type from the data shape, and renders exactly one chart per question."
tags: [chart, visualization]
version: "2.0.0"
---

# Visualize Chart (Trigger)

Routes chart requests to `visualize_chart`. Sibling to the analyst skill — same SQL discipline, same
entity and filter contract — but renders the answer's data instead of only tabulating it.
A chart built on the wrong entity or the wrong filter code is not a chart problem; it is a wrong
answer with a picture attached.

## CAPTURE

Lock `{widget_type, widget_title, source of rows}`.

- The chart's rows are the **answer's own rows**. Never write a second, differently-filtered query
  for the picture.
- Column order is the axis contract: X first, Y second, an optional series third.
  **Exactly three columns are read** — a fourth is refused, not truncated.
- Title in the answer's language, describing the data rather than the request.

Source, in order of preference:

1. **`sql=` of the query you already ran** — the default; reuses that query's cached result, so the
   picture shows the numbers the text quotes.
2. **The CSV this turn exported** — for values a query cannot return (a forecast's projection).
   No `sql=`, no `data=`; just name the columns to plot.
3. **`data=`+`columns=`** — last resort only, for values neither exported nor queryable.

**Never re-type tool output into `data=`.** Transcribing risks a picture that disagrees with the
text. Chart the exported CSV instead; if there is no CSV, chart the queryable part and say which
part the picture covers — never drop the chart entirely.

## RUN

Call `visualize_chart(widget_type, widget_title, sql=...)` **once**, after the headline number is
settled. The chart draws the answer; it never comes before the counting query or stands in for it.

**A chart is part of a data answer, not an extra** — like `run_forecast`, the user does not ask for
the tool by name. Default to charting.

- **Any answer carrying data** — counts over time, comparisons, breakdowns, rankings, compositions,
  distributions — gets exactly one chart, whether or not the user said "grafik".
- **Explicit request** (grafik, chart, plot, visual, diagram) → always chart; never answer with a
  table alone.
- **Skip only when there is nothing to draw**: definitional or explanatory prose · a lone figure
  with nothing to compare against · a record lookup read row by row · zero rows · a shape no type
  fits honestly.
- **When in doubt, chart it.** A redundant chart costs a glance; a missing one costs the reader the
  shape of their own data.

| What the answer is about | Type |
|---|---|
| a trend over periods | `line_chart` |
| several trends over periods | `grouped_line_chart` |
| cumulative or volume over time | `area_chart` |
| comparison across categories | `bar_chart` |
| same categories split by a second dimension | `grouped_bar_chart` |
| categories with long labels | `horizontal_bar_chart` |
| share of one whole, few slices | `pie_chart` |
| a value across two dimensions | `heatmap` |
| two quantitative columns | `scatter_plot` |
| spread within categories | `box_plot` |
| nested part-of-whole | `treemap` |
| a single scalar | `big_number` |

**Each type fixes its X axis.** `line_chart` / `area_chart` / `grouped_line_chart` plot X as a
*date*, so periods must be ISO (`2024-01-01`, or `2024-01` for months). A month name or `Q1`
collapses that axis — put it on a `bar_chart`, whose X takes any text. `scatter_plot` needs a
number on X.

### Several series

When the answer covers several codes, statuses or segments, the chart shows **all of them**, not
just the total — charting one metric out of five throws away most of what the answer says. The
third column splits the chart into one series per distinct value, each with a legend entry.

That requires **long** form. A wide answer table (one column per code) cannot be charted, because
everything past the third column vanishes. Reshape:

```sql
SELECT periode, 'kode A' AS seri, kode_a AS jumlah FROM t
UNION ALL
SELECT periode, 'kode B' AS seri, kode_b AS jumlah FROM t
ORDER BY 1, 2
```

Then chart `[periode, jumlah, seri]`. Usually the long form is the *natural* query
(`GROUP BY periode, kode`) and the wide table is only how it was written up for reading.

Chart the total **or** the breakdown, never both in one chart — a total plotted beside its own parts
dwarfs them. Beyond roughly eight series the tool keeps the largest and says so.

## When the tool answers back

- `## Kesalahan` → the shape or the SQL is wrong and the message names which. Act on the reason;
  **do not retry the same call.** A shape refusal means the chart would have rendered *wrong*.
- `No rows to chart.` → answer in text, do not force a chart.
- **Call succeeded but nothing appears on screen → the answer still stands.** Rendering happens
  outside this skill; a payload too large, a transport hiccup or a dropped widget touches none of
  the numbers, which came from SQL and are already settled. So: write the full answer with every
  figure and labelled split · say **once** that the chart could not be displayed, plainly ·
  **never call again** (a second call is refused anyway and spends budget) · never trim the answer
  to compensate · never report it as a missing number — "grafik tidak dapat ditampilkan" is a
  display note, "angkanya tidak tersedia" would be false.
- **An export failure never cancels the chart**, and the same rules apply to `run_forecast`:
  a projection whose chart did not render is still a projection.

## PRESENT & hard rules

- Lead with the finding in words; the chart supports the sentence, it does not replace it.
- Do **not** repeat the chart's table as markdown — a short table of key rows is fine, not the full
  dataset twice. Mention any limit the tool reported (top-N, downsampling) when it changes the reading.
- **One chart per question — but one chart carries many series.** "One chart" limits pictures, never
  content: a `grouped_line_chart` showing four codes is one chart.
- **Chart follows the answer's filters** — same entity, same status and category codes, same date
  range. Cannot reuse the answer's rows → do not chart.
- **The chart is not the export.** It never replaces `upload_to_s3`; the CSV contract stays as in
  `bpom-analyst/SKILL.md`.
