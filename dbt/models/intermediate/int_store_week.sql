{{
    config(
        materialized='ephemeral',
        tags=['intermediate']
    )
}}

with traffic as (

    select * from {{ ref('stg_nfk__traffic') }}

),

stores as (

    select * from {{ ref('stg_nfk__stores') }}

)

select
    traffic.store_id,
    traffic.week_label,
    traffic.transactions,
    traffic.avg_basket_dkk,
    traffic.transactions * traffic.avg_basket_dkk as till_value_dkk,
    stores.region_code,
    stores.store_format,
    stores.sales_area_sqm,
    case
        when stores.sales_area_sqm < 400 then 'S'
        when stores.sales_area_sqm < 900 then 'M'
        else 'L'
    end as store_size_band
from traffic
inner join stores on stores.store_id = traffic.store_id
where stores.is_in_scope = 1
