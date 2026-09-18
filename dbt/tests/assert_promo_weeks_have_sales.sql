-- Every planned campaign week should show at least one sales line for the
-- article. Where it does not, the article was delisted after the leaflet
-- went to print and the campaign file was never corrected.

with planned as (

    select distinct sku_id, week_label
    from {{ ref('int_promo_weeks') }}
    where store_group = 'ALLE'

),

actual as (

    select distinct sku_id, week_label
    from {{ ref('int_sales_normalised') }}

)

select planned.*
from planned
left join actual
    on actual.sku_id = planned.sku_id
    and actual.week_label = planned.week_label
where actual.sku_id is null
