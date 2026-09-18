{{
    config(
        materialized='view',
        tags=['staging', 'master_data']
    )
}}

-- Store master. Depots, the HQ test store and the franchise estate are
-- flagged but not filtered here; the marts do the filtering so that the data
-- quality model can still count them.

with source as (

    select * from {{ source('nfk_raw', 'butik_stamdata') }}

)

select
    {{ nfk_store_id('butik_id') }}                  as store_id,
    trim(butik_navn)                                as store_name,
    coalesce(nullif(trim(region_kode), ''), {{ nfk_region_from_store_id('butik_id') }}) as region_code,
    upper(trim(type))                               as store_format,
    upper(trim(status))                             as store_status,
    cast(nullif(trim(salgsareal_m2), '') as numeric) as sales_area_sqm,
    {{ nfk_parse_date('aabnet_dato') }}             as opened_date,
    {{ nfk_parse_date('lukket_dato') }}             as closed_date,
    case when substring({{ nfk_store_id('butik_id') }} from 1 for 1) = '9' then 1 else 0 end as is_depot,
    case when substring({{ nfk_store_id('butik_id') }} from 3 for 2) = '99' then 1 else 0 end as is_test_store,
    case when {{ nfk_is_real_store('butik_id') }} then 1 else 0 end as is_in_scope
from source
