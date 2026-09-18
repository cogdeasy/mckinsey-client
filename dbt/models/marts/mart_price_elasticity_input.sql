{{
    config(
        materialized='table',
        tags=['mart', 'pricing']
    )
}}

-- Log log inputs for the elasticity fit. Weeks with a closing day or a
-- recent stock out are dropped: they bias the fit towards inelastic.

with sales as (

    select * from {{ ref('mart_sales_weekly') }}

)

select
    week_label,
    fiscal_year,
    fiscal_period,
    region_code,
    category_code,
    subcategory_code,
    sku_id,
    sum(units)                                          as units,
    sum(net_value_dkk)                                  as net_value_dkk,
    case when sum(units) > 0 then sum(net_value_dkk) / sum(units) end as realised_price_dkk,
    ln(nullif(sum(units), 0))                           as log_units,
    ln(nullif(case when sum(units) > 0 then sum(net_value_dkk) / sum(units) end, 0)) as log_price,
    max(discount_depth)                                 as discount_depth,
    max(promo_flag)                                     as promo_flag
from sales
where has_closing_day = 0
  and was_out_of_stock_recently = 0
  and units > 0
group by 1, 2, 3, 4, 5, 6, 7
