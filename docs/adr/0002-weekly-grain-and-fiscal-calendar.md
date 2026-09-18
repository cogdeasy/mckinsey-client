# 0002 - Weekly grain and the client fiscal calendar

Status: accepted (wave 1), revisited in wave 2

## Context

Sales arrive daily but replenishment plans weekly, and the client's own
planning pack is built on their 4-4-5 fiscal calendar starting the first Monday
of October. Their week label is `YYYYWW` using the fiscal year, which does not
line up with ISO weeks in five years out of seven.

## Decision

Model at store / article / fiscal week. Carry both the fiscal week label and
the ISO week number, and derive calendar features from the ISO week.

## Consequences

- Every join in the pipeline and in dbt keys on `week_label`, so the label
  format is load bearing.
- Year on year features use a 52 week lag, which drifts against the fiscal
  calendar in the 53 week years. Accepted for wave 1, never revisited.
- Comparisons back to the client's finance reporting need the fiscal period,
  which is why `fiscal_period` is carried through to the marts.
