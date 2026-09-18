# 0001 - Kedro as the pipeline framework

Status: accepted (wave 1)

## Context

The delivery had eight weeks to a first forecast pack and two data scientists
who would rotate off. The client's platform team can run a Python job on a
scheduler but will not host Airflow for us.

## Decision

Use Kedro for the analytics pipelines, with the data catalog as the only place
file paths and formats are declared, and dbt for everything that can be done in
the warehouse.

## Consequences

- The split is not clean: the marts are exported to CSV nightly and read back
  in as raw inputs, because the Kedro runtime has no warehouse credentials.
- Pinning to the Kedro version the client's platform image ships with (0.17.5)
  means the newer dataset and session APIs are unavailable.
- Node functions are plain pandas, so they can be lifted out if the framework
  is dropped later.
