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
    trim(cast(uge as varchar))              as week_label,
    cast(replace(beholdning, ',', '.') as numeric) as stock_units,
    case when cast(replace(beholdning, ',', '.') as numeric) <= 0 then 1 else 0 end as is_out_of_stock
from source
