{{
    config(
        materialized='view',
        tags=['staging', 'calendar']
    )
}}

-- The client's own 4-4-5 calendar. Never derive these columns: FY starts on
-- the first Monday of October and period 14 exists in the 53 week years.

with source as (

    select * from {{ source('nfk_raw', 'finanskalender') }}

)

select
    trim(cast(uge_label as varchar))            as week_label,
    {{ nfk_parse_date('uge_start_dato') }}      as week_start_date,
    {{ nfk_parse_date('uge_slut_dato') }}       as week_end_date,
    cast(fin_aar as integer)                    as fiscal_year,
    cast(periode as integer)                    as fiscal_period,
    cast(fin_uge as integer)                    as fiscal_week,
    cast(uge_i_periode as integer)              as week_in_period
from source
