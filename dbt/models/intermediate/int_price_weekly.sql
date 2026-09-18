{{
    config(
        materialized='ephemeral',
        tags=['intermediate', 'pricing']
    )
}}

-- Effective dated prices flattened onto the week grid. Prices are held per
-- store even though the client sets them centrally per region; the store
-- level rows are what the price file delivers.

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
        prices.store_id,
        prices.normal_price_dkk,
        prices.shelf_price_dkk,
        row_number() over (
            partition by calendar.week_label, prices.sku_id, prices.store_id
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
    store_id,
    normal_price_dkk,
    shelf_price_dkk,
    case
        when normal_price_dkk > 0 then 1 - (shelf_price_dkk / normal_price_dkk)
        else 0
    end as price_discount_depth
from spread
where price_rank = 1
