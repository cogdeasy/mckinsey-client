# Re-pointing Meridian at a new client

Written after the wave-2 handover (JHK/ML). It is not a complete runbook - the
last two engagements both needed changes that are not listed here - but it is
the closest thing we have to one. Update it as you go.

## Before you start

Get the following from the client before touching the code:

- a sample of every extract, with real volumes for at least one full year
- the fiscal calendar definition (period pattern, first week of the year)
- the store master, including which formats are in and out of scope
- the article hierarchy with the category codes actually used in reporting
- the promotional mechanics list and what each one means commercially
- the accuracy definition the client's own planners use

Without the last two the model trains fine and the numbers are meaningless.

## Roughly what has to change

1. **Config.** `conf/base/parameters.yml` carries the client block (code,
   currency, VAT, deposit rates, FX) and the calendar block. Most of the other
   `parameters_*.yml` files carry at least one client-shaped value.
2. **Catalog.** `conf/base/catalog.yml` names the extract files and encodes the
   delimiter, encoding and decimal separator of the current delivery. New client
   means new filenames and usually a different dialect.
3. **Column mapping.** The rename map in
   `conf/base/parameters_data_engineering.yml` maps the extract headers to the
   internal names. Internal names are stable; only the left hand side changes.
4. **Codes.** `src/meridian/utils/nordfalk_codes.py` holds region, category,
   format and deposit lookups plus the store id rules. This module is
   client-specific end to end and is the main piece of work.
5. **Fiscal calendar.** `src/meridian/utils/fiscal_calendar.py` assumes a 4-4-5
   year starting in October. A 13-period or an ISO-week client needs the whole
   module revisited, not a constant changed.
6. **dbt.** `dbt/models/staging` is written against the current source columns;
   the seeds in `dbt/seeds` are the same lookups again, kept separately because
   the warehouse team cannot import the Python package.
7. **Front end.** The app has its own copies of the region and category names
   (`app/components/formatting.py`) and its labels are in Danish.
8. **Tests.** The fixtures in `tests/conftest.py` are built from the current
   client's extract shape, so a re-point breaks them in a useful way. Fix the
   fixtures first, then the code.

## Things that have caught people out

- Store id length is assumed to be four characters in a regex, and region is
  taken as the first two characters of the id. Both assumptions appear in
  Python, in SQL and in the app.
- `type` is used as a column name in the extract and means store format. A
  blanket rename of it will break unrelated code.
- Dates in the extract parse as `DD/MM/YYYY`. Several of them are ambiguous, so
  a wrong format fails silently rather than loudly.
- Deposit is inside the gross line value and has to come out before any price
  or elasticity work. If the new client does not run a deposit scheme, the
  removal has to be switched off rather than zeroed - see the pricing helpers.
- The Danish holiday list is loaded from a seed file and also referenced by
  name in the feature parameters.
- The export interface (column order, separators, decimal comma) is fixed by
  the current client's interface note and will not be what the next client
  wants.

## Order of work that has worked before

1. Land the new extracts in `data/01_raw` and get the data engineering pipeline
   to run, ignoring whether the numbers are right.
2. Fix the codes module and the calendar, then re-run and reconcile totals
   against the client's own weekly sales report.
3. Re-point dbt, then the features, then the model.
4. Leave the app until last; it reads outputs only.

## Still missing from this document

- how to migrate the snapshots when the source system changes
- what to do with the manual uplift table, which has never been re-derived
- anything about the scoring hand-off file beyond the interface note
