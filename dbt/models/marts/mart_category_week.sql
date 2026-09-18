{{
    config(
        materialized='table',
        tags=['mart', 'reporting']
    )
}}

with sales as (

    select * from {{ ref('mart_sales_weekly') }}

)

select
    week_label,
    fiscal_year,
    fiscal_period,
    region_code,
    category_code,
    sum(units)                                      as units,
    sum(net_value_dkk)                              as net_value_dkk,
    sum(net_value_eur)                              as net_value_eur,
    sum(case when promo_flag = 1 then net_value_dkk else 0 end) as promo_value_dkk,
    case
        when sum(net_value_dkk) > 0
            then sum(case when promo_flag = 1 then net_value_dkk else 0 end) / sum(net_value_dkk)
    end                                             as promo_share,
    count(distinct store_id)                        as stores,
    count(distinct sku_id)                          as articles
from sales
group by 1, 2, 3, 4, 5
