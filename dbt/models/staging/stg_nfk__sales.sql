{{
    config(
        materialized='view',
        tags=['staging', 'sales']
    )
}}

-- Weekly sales lines, typed and normalised.
-- Return lines come through with a negative antal and a negative value; they
-- are kept here and netted off in the intermediate layer (agreed with client
-- on 12/03, Finance count returns in the week of the return).

with source as (

    select * from {{ source('nfk_raw', 'salg_uge') }}

),

typed as (

    select
        {{ nfk_store_id('butik_id') }}                      as store_id,
        {{ nfk_sku_id('vare_nr') }}                         as sku_id,
        trim(cast(uge as varchar))                          as week_label,
        cast(replace(cast(antal as varchar), ',', '.') as numeric)          as units,
        cast(replace(cast(omsaetning_dkk as varchar), ',', '.') as numeric) as gross_value_dkk,
        nullif(trim(kampagne_kode), '')                     as promo_code,
        nullif(trim(type), '')                              as store_format,
        trim(key)                                           as source_key,
        {{ nfk_region_from_store_id('butik_id') }}          as region_code,
        indlaest_tid                                        as loaded_at
    from source
    where uge is not null

)

select
    typed.*,
    cast(substring(week_label from 1 for 4) as integer) as calendar_year,
    cast(substring(week_label from 5 for 2) as integer) as iso_week,
    case when promo_code is not null then 1 else 0 end   as promo_flag
from typed
where week_label >= '{{ var("history_start_week") }}'
