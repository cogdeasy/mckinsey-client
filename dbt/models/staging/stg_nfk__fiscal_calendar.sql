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
    trim(uge_label)                             as week_label,
    {{ nfk_parse_date('uge_start') }}           as week_start_date,
    cast(regnskabsaar as integer)               as fiscal_year,
    cast(regnskabsperiode as integer)           as fiscal_period,
    cast(regnskabsuge as integer)               as fiscal_week,
    cast(periode_uge as integer)                as week_in_period
from source
