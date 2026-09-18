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
    trim(navn)                                      as store_name,
    coalesce(
        lpad(nullif(trim(cast(region_kode as varchar)), ''), 2, '0'),
        {{ nfk_region_from_store_id('butik_id') }}
    )                                               as region_code,
    upper(trim(type))                               as store_format,
    upper(trim(status))                             as store_status,
    cast(nullif(trim(cast(kvm as varchar)), '') as numeric) as sales_area_sqm,
    lpad(trim(cast(postnr as varchar)), 4, '0')     as postal_code,
    {{ nfk_parse_date('aabningsdato') }}            as opened_date,
    case when substring({{ nfk_store_id('butik_id') }} from 1 for 1) = '9' then 1 else 0 end as is_depot,
    case when substring({{ nfk_store_id('butik_id') }} from 3 for 2) = '99' then 1 else 0 end as is_test_store,
    case when {{ nfk_is_real_store('butik_id') }} then 1 else 0 end as is_in_scope
from source
