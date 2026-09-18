# nfk_analytics (dbt)

Warehouse models behind the Meridian forecasting asset. Runs against the
Nordfalk analytics Postgres (`nfk-dwh-dev.internal` / `nfk-dwh-prod.internal`).

## Layers

| Layer | Schema (prod) | Materialisation | Notes |
| --- | --- | --- | --- |
| staging | `nfk_staging` | view | 1:1 with the landing tables, typed and renamed |
| intermediate | - | ephemeral | business logic, not persisted |
| marts | `nfk_marts` | table | consumed by the asset and by the BI layer |

`mart_sales_weekly` is the contract with the Kedro asset. The catalog entry
of the same name reads it directly, so column renames have to be agreed with
the modelling team before they are merged.

## Running

    export NFK_DWH_USER=...
    export NFK_DWH_PASSWORD=...
    cd dbt
    dbt deps
    dbt seed
    dbt snapshot
    dbt run
    dbt test

The nightly job (Control-M `NFK_DBT_D`) runs `dbt run --exclude tag:dq`
followed by `dbt test --exclude tag:dq`, then the Kedro `weekly` pipeline.
The data quality mart is built on Monday only.

## Conventions

- Source tables keep the client's Danish names; staging models rename to the
  asset's column names and nothing downstream uses the Danish ones.
- Client business rules live in `macros/nfk_value.sql` (VAT, deposit, FX) and
  `macros/nfk_codes.sql` (store, region, article codes). The same rules exist
  in `src/meridian/utils/` for the parts of the asset that read the CSV drop
  rather than the warehouse.
- Variables in `dbt_project.yml` hold the rates and the scope exclusions.

## Known gaps

- `int_stock_weekly` carries the out of stock flag forward three weeks
  because the client only samples stock every fourth week. Overstates
  availability problems around Easter (raised 04/04, parked for wave 2).
- `mart_promo_performance` has no baseline for articles on permanent offer.
- The freshness block on `nfk_raw` assumes the SFTP drop lands by 04:00 CET.
  During the December peak it regularly lands at 06:30 and the warning fires.
