{{
    config(
        materialized='view',
        tags=['staging', 'calendar']
    )
}}

with source as (

    select * from {{ source('nfk_raw', 'helligdage') }}

)

select
    {{ nfk_parse_date('dato') }}            as holiday_date,
    trim(navn)                              as holiday_name,
    upper(trim(type))                       as holiday_type,
    case when upper(trim(lukkedag)) in ('J', 'JA') then 1 else 0 end as is_closing_day,
    {{ nfk_week_label(nfk_parse_date('dato')) }} as week_label
from source
