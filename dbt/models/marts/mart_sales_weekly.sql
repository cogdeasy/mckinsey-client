{{
    config(
        materialized='table',
        tags=['mart', 'sales'],
        indexes=[
            {'columns': ['store_id', 'sku_id', 'week_label'], 'unique': true}
        ]
    )
}}

-- Primary mart consumed by the forecasting asset. One row per store x
-- article x week, with promo, price, stock and calendar attached.
-- The asset reads this table through the kedro catalog entry
-- mart_sales_weekly; do not rename the columns without telling the
-- modelling team (JLB).

with sales as (

    select * from {{ ref('int_sales_normalised') }}

),

promo as (

    select * from {{ ref('int_promo_weeks') }}

),

price as (

    select * from {{ ref('int_price_weekly') }}

),

stock as (

    select * from {{ ref('int_stock_weekly') }}

),

calendar as (

    select * from {{ ref('stg_nfk__fiscal_calendar') }}

),

holidays as (

    select
        week_label,
        count(*)                        as holiday_count,
        max(is_closing_day)             as has_closing_day
    from {{ ref('stg_nfk__holidays') }}
    group by 1

)

select
    sales.store_id,
    sales.sku_id,
    sales.week_label,
    calendar.week_start_date,
    calendar.fiscal_year,
    calendar.fiscal_period,
    calendar.fiscal_week,
    sales.calendar_year,
    sales.iso_week,
    sales.region_code,
    sales.category_code,
    sales.subcategory_code,
    sales.supplier_id,
    sales.deposit_type,
    sales.is_fresh,
    sales.case_pack,
    sales.store_format,
    sales.sales_area_sqm,
    sales.units,
    sales.gross_value_dkk,
    sales.net_value_dkk,
    sales.net_value_eur,
    case when sales.units > 0 then sales.net_value_dkk / sales.units end as realised_price_dkk,
    price.shelf_price_dkk,
    price.normal_price_dkk,
    coalesce(promo.discount_depth, price.price_discount_depth, 0) as discount_depth,
    coalesce(promo.is_leaflet, 0)                   as is_leaflet,
    coalesce(promo.is_multibuy, 0)                  as is_multibuy,
    coalesce(promo.is_coupon, 0)                    as is_coupon,
    greatest(sales.promo_flag, case when promo.sku_id is not null then 1 else 0 end) as promo_flag,
    promo.promo_mechanics,
    coalesce(stock.was_out_of_stock_recently, 0)    as was_out_of_stock_recently,
    coalesce(holidays.holiday_count, 0)             as holiday_count,
    coalesce(holidays.has_closing_day, 0)           as has_closing_day,
    sales.return_line_count
from sales
inner join calendar on calendar.week_label = sales.week_label
left join promo
    on promo.sku_id = sales.sku_id
    and promo.week_label = sales.week_label
    and promo.store_group = 'ALLE'
left join price
    on price.sku_id = sales.sku_id
    and price.week_label = sales.week_label
    and price.store_id = sales.store_id
left join stock
    on stock.store_id = sales.store_id
    and stock.sku_id = sales.sku_id
    and stock.week_label = sales.week_label
left join holidays on holidays.week_label = sales.week_label
