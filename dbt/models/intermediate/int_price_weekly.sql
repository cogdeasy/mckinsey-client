{{
    config(
        materialized='ephemeral',
        tags=['intermediate', 'pricing']
    )
}}

-- Effective dated prices flattened to a week grid at region level.

with prices as (

    select * from {{ ref('stg_nfk__prices') }}

),

calendar as (

    select distinct week_label, week_start_date
    from {{ ref('stg_nfk__fiscal_calendar') }}

),

spread as (

    select
        calendar.week_label,
        prices.sku_id,
        prices.region_code,
        prices.shelf_price_dkk,
        row_number() over (
            partition by calendar.week_label, prices.sku_id, prices.region_code
            order by prices.valid_from desc
        ) as price_rank
    from calendar
    inner join prices
        on prices.valid_from <= calendar.week_start_date
        and coalesce(prices.valid_to, date '2099-12-31') >= calendar.week_start_date

)

select
    week_label,
    sku_id,
    region_code,
    shelf_price_dkk
from spread
where price_rank = 1
