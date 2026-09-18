{{
    config(
        materialized='view',
        tags=['staging']
    )
}}

with source as (

    select * from {{ source('nfk_raw', 'lager_beholdning') }}

)

select
    {{ nfk_store_id('butik_id') }}          as store_id,
    {{ nfk_sku_id('vare_nr') }}             as sku_id,
    {{ nfk_parse_date('dato') }}            as sample_date,
    {{ nfk_week_label(nfk_parse_date('dato')) }} as week_label,
    cast(replace(cast(beholdning as varchar), ',', '.') as numeric) as stock_units,
    cast(nullif(trim(cast(kolli as varchar)), '') as integer)       as case_pack,
    case when cast(replace(cast(beholdning as varchar), ',', '.') as numeric) <= 0
        then 1 else 0 end                   as is_out_of_stock
from source
