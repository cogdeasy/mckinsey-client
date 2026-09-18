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
    lpad(trim(cast(kategori_kode as varchar)), 2, '0')  as category_code,
    upper(nullif(trim(pant_type), ''))                  as deposit_type,
    nullif(trim(leverandoer_nr), '')                    as supplier_id,
    upper(trim(enhed))                                  as sales_unit,
    cast(nullif(trim(cast(kolli as varchar)), '') as integer) as case_pack,
    case when lpad(trim(cast(kategori_kode as varchar)), 2, '0') in ('10', '11', '12')
        then 1 else 0 end                               as is_fresh
from source
