{{
    config(
        materialized='view',
        tags=['staging', 'pricing']
    )
}}

-- Effective dated shelf prices. One row per article, store and change date;
-- there is no end date on the file, the next row closes the previous one.

with source as (

    select * from {{ source('nfk_raw', 'pris_historik') }}

),

typed as (

    select
        {{ nfk_sku_id('vare_nr') }}                             as sku_id,
        {{ nfk_store_id('butik_id') }}                          as store_id,
        {{ nfk_parse_date('gyldig_fra') }}                      as valid_from,
        cast(replace(cast(normalpris as varchar), ',', '.') as numeric) as normal_price_dkk,
        cast(replace(cast(salgspris as varchar), ',', '.') as numeric)  as shelf_price_dkk
    from source

)

select
    typed.*,
    lead(valid_from) over (
        partition by sku_id, store_id order by valid_from
    ) - interval '1 day' as valid_to
from typed
