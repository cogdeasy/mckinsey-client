-- Ad hoc for the sprint 6 steerco: how much of the leaflet uplift on a
-- promoted article is taken from the rest of its subcategory in the same
-- store. Not productionised; the subcategory baseline is too noisy on the
-- fresh categories to publish.

with promoted as (

    select
        store_id,
        week_label,
        subcategory_code,
        sku_id,
        units,
        net_value_dkk
    from {{ ref('mart_sales_weekly') }}
    where promo_flag = 1
      and is_leaflet = 1

),

rest_of_subcategory as (

    select
        sales.store_id,
        sales.week_label,
        sales.subcategory_code,
        sum(sales.units)            as other_units,
        sum(sales.net_value_dkk)    as other_value_dkk
    from {{ ref('mart_sales_weekly') }} sales
    where sales.promo_flag = 0
    group by 1, 2, 3

)

select
    promoted.week_label,
    promoted.subcategory_code,
    sum(promoted.units)                 as promo_units,
    sum(rest_of_subcategory.other_units) as other_units,
    sum(promoted.net_value_dkk)         as promo_value_dkk,
    sum(rest_of_subcategory.other_value_dkk) as other_value_dkk
from promoted
left join rest_of_subcategory
    on rest_of_subcategory.store_id = promoted.store_id
    and rest_of_subcategory.week_label = promoted.week_label
    and rest_of_subcategory.subcategory_code = promoted.subcategory_code
group by 1, 2
