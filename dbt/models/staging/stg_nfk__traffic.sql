{{
    config(
        materialized='view',
        tags=['staging']
    )
}}

with source as (

    select * from {{ source('nfk_raw', 'kunde_trafik') }}

)

select
    {{ nfk_store_id('butik_id') }}              as store_id,
    trim(cast(uge as varchar))                  as week_label,
    cast(transaktioner as numeric)              as transactions,
    cast(replace(gns_kurv_dkk, ',', '.') as numeric) as avg_basket_dkk
from source
