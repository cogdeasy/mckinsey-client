{{
    config(
        materialized='table',
        tags=['mart']
    )
}}

with store_week as (

    select * from {{ ref('int_store_week') }}

),

sales as (

    select
        store_id,
        week_label,
        sum(net_value_dkk)  as net_value_dkk,
        sum(units)          as units
    from {{ ref('int_sales_normalised') }}
    group by 1, 2

)

select
    store_week.store_id,
    store_week.week_label,
    store_week.region_code,
    store_week.store_format,
    store_week.store_size_band,
    store_week.sales_area_sqm,
    store_week.transactions,
    store_week.avg_basket_dkk,
    store_week.till_value_dkk,
    sales.net_value_dkk,
    sales.units,
    case
        when store_week.sales_area_sqm > 0
            then sales.net_value_dkk / store_week.sales_area_sqm
    end as sales_density_dkk_per_sqm
from store_week
left join sales
    on sales.store_id = store_week.store_id
    and sales.week_label = store_week.week_label
