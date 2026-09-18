{{
    config(
        materialized='view',
        tags=['staging']
    )
}}

-- Till transaction counts. The client call these "kunder"; they are baskets,
-- not people, and the two numbers are used interchangeably in their own
-- reporting.

with source as (

    select * from {{ source('nfk_raw', 'kunde_trafik') }}

)

select
    {{ nfk_store_id('butik_id') }}              as store_id,
    trim(cast(uge_label as varchar))            as week_label,
    cast(kunder as numeric)                     as transactions
from source
