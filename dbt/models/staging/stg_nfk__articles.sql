{{
    config(
        materialized='view',
        tags=['staging', 'master_data']
    )
}}

with source as (

    select * from {{ source('nfk_raw', 'vare_hierarki') }}

)

select
    {{ nfk_sku_id('vare_nr') }}                         as sku_id,
    trim(vare_tekst)                                    as article_name,
    lpad(trim(cast(underkategori as varchar)), 4, '0')  as subcategory_code,
    {{ nfk_category_code('underkategori') }}            as category_code,
    upper(nullif(trim(pant_type), ''))                  as deposit_type,
    nullif(trim(leverandoer_id), '')                    as supplier_id,
    cast(nullif(trim(kolli), '') as integer)            as case_pack,
    cast(replace(nullif(trim(vejl_pris_dkk), ''), ',', '.') as numeric) as list_price_dkk,
    case when upper(trim(ferskvare)) in ('J', 'JA', 'Y') then 1 else 0 end as is_fresh
from source
