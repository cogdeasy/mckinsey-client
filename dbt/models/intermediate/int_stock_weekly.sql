{{
    config(
        materialized='ephemeral',
        tags=['intermediate']
    )
}}

-- Stock is only sampled every fourth week, so the flag is carried forward
-- to the following three weeks. Known to overstate availability problems
-- around Easter; raised with the client, parked for wave 2.

with stock as (

    select * from {{ ref('stg_nfk__stock') }}

)

select
    store_id,
    sku_id,
    week_label,
    sample_date,
    stock_units,
    case_pack,
    is_out_of_stock,
    max(is_out_of_stock) over (
        partition by store_id, sku_id
        order by week_label
        rows between 3 preceding and current row
    ) as was_out_of_stock_recently
from stock
