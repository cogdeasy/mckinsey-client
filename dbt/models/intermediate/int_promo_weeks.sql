{{
    config(
        materialized='ephemeral',
        tags=['intermediate', 'promotions']
    )
}}

-- Campaigns exploded to one row per article x week. A campaign that starts
-- on a Thursday still belongs to the ISO week of its start date; the client
-- plans in leaflet weeks, not in days.

with promotions as (

    select * from {{ ref('stg_nfk__promotions') }}

),

calendar as (

    select distinct week_label, week_start_date
    from {{ ref('stg_nfk__fiscal_calendar') }}

),

exploded as (

    select
        promotions.campaign_id,
        promotions.sku_id,
        promotions.promo_mechanic,
        promotions.store_group,
        promotions.is_leaflet,
        promotions.promo_price_dkk,
        promotions.normal_price_dkk,
        calendar.week_label,
        calendar.week_start_date
    from promotions
    inner join calendar
        on calendar.week_start_date >= date_trunc('week', promotions.start_date)
        and calendar.week_start_date <= promotions.end_date

)

select
    week_label,
    sku_id,
    store_group,
    max(is_leaflet)                                                     as is_leaflet,
    max(case when promo_mechanic = '3F2' then 1 else 0 end)             as is_multibuy,
    max(case when promo_mechanic = 'KUPON' then 1 else 0 end)           as is_coupon,
    min(promo_price_dkk)                                                as promo_price_dkk,
    max(normal_price_dkk)                                               as normal_price_dkk,
    case
        when max(normal_price_dkk) > 0
            then 1 - (min(promo_price_dkk) / max(normal_price_dkk))
        else 0
    end                                                                 as discount_depth,
    count(distinct campaign_id)                                         as campaign_count,
    string_agg(distinct promo_mechanic, '+')                            as promo_mechanics
from exploded
group by 1, 2, 3
