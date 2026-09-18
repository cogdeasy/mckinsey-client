{{
    config(
        materialized='table',
        tags=['mart', 'promotions']
    )
}}

-- Promo uplift against the four non promo weeks before the campaign.
-- Baseline weeks that themselves contained a campaign are excluded, which
-- is why articles on permanent offer end up with a null baseline.

with sales as (

    select * from {{ ref('mart_sales_weekly') }}

),

baseline as (

    select
        sku_id,
        region_code,
        week_label,
        avg(units) over (
            partition by sku_id, region_code
            order by week_label
            rows between 4 preceding and 1 preceding
        ) as baseline_units
    from (
        select
            sku_id,
            region_code,
            week_label,
            sum(case when promo_flag = 0 then units end) as units
        from sales
        group by 1, 2, 3
    ) non_promo

),

promo_weeks as (

    select
        sales.sku_id,
        sales.region_code,
        sales.week_label,
        sales.category_code,
        max(sales.discount_depth)   as discount_depth,
        max(sales.is_leaflet)       as is_leaflet,
        max(sales.promo_mechanics)  as promo_mechanics,
        sum(sales.units)            as promo_units,
        sum(sales.net_value_dkk)    as promo_value_dkk
    from sales
    where sales.promo_flag = 1
    group by 1, 2, 3, 4

)

select
    promo_weeks.*,
    baseline.baseline_units,
    case
        when baseline.baseline_units > 0
            then promo_weeks.promo_units / baseline.baseline_units - 1
    end as uplift_pct
from promo_weeks
left join baseline
    on baseline.sku_id = promo_weeks.sku_id
    and baseline.region_code = promo_weeks.region_code
    and baseline.week_label = promo_weeks.week_label
