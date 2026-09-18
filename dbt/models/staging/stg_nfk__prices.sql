{{
    config(
        materialized='view',
        tags=['staging', 'pricing']
    )
}}

-- Effective dated shelf prices. Prices are held per region, not per store.

with source as (

    select * from {{ source('nfk_raw', 'pris_historik') }}

)

select
    {{ nfk_sku_id('vare_nr') }}             as sku_id,
    lpad(trim(cast(region_kode as varchar)), 2, '0') as region_code,
    {{ nfk_parse_date('gyldig_fra') }}      as valid_from,
    {{ nfk_parse_date('gyldig_til') }}      as valid_to,
    cast(replace(pris_dkk, ',', '.') as numeric) as shelf_price_dkk
from source
