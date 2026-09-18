{{
    config(
        materialized='view',
        tags=['staging', 'promotions']
    )
}}

-- One row per campaign x article. Campaigns run Monday to Sunday, so the
-- start date is enough to derive the promo week. Multi week campaigns are
-- exploded downstream in int_promo_weeks.

with source as (

    select * from {{ source('nfk_raw', 'kampagne_kalender') }}

)

select
    trim(kampagne_id)                                   as campaign_id,
    {{ nfk_sku_id('vare_nr') }}                         as sku_id,
    upper(trim(kampagne_kode))                          as promo_mechanic,
    upper(coalesce(nullif(trim(butik_gruppe), ''), 'ALLE')) as store_group,
    {{ nfk_parse_date('start_dato') }}                  as start_date,
    {{ nfk_parse_date('slut_dato') }}                   as end_date,
    cast(replace(cast(rabat_pct as varchar), ',', '.') as numeric) / 100.0 as discount_depth,
    cast(nullif(trim(cast(avis_side as varchar)), '') as integer) as leaflet_page,
    case when nullif(trim(cast(avis_side as varchar)), '') is not null then 1 else 0 end as is_leaflet
from source
where start_dato is not null
