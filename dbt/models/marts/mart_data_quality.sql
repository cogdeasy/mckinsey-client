{{
    config(
        materialized='table',
        tags=['mart', 'dq']
    )
}}

-- Feeds the data quality page of the app. One row per week per check.

with sales as (

    select * from {{ ref('stg_nfk__sales') }}

),

in_scope as (

    select * from {{ ref('int_sales_normalised') }}

),

checks as (

    select
        week_label,
        'raw_rows'          as check_name,
        count(*)::numeric   as check_value
    from sales
    group by 1

    union all

    select
        week_label,
        'negative_unit_lines',
        sum(case when units < 0 then 1 else 0 end)::numeric
    from sales
    group by 1

    union all

    select
        week_label,
        'zero_value_lines',
        sum(case when gross_value_dkk = 0 then 1 else 0 end)::numeric
    from sales
    group by 1

    union all

    select
        week_label,
        'unmapped_store_lines',
        sum(case when store_id not in (select store_id from {{ ref('stg_nfk__stores') }}) then 1 else 0 end)::numeric
    from sales
    group by 1

    union all

    select
        week_label,
        'in_scope_rows',
        count(*)::numeric
    from in_scope
    group by 1

    union all

    select
        week_label,
        'net_value_dkk',
        sum(net_value_dkk)
    from in_scope
    group by 1

)

select
    checks.week_label,
    checks.check_name,
    checks.check_value,
    calendar.fiscal_year,
    calendar.fiscal_period,
    current_timestamp as generated_at
from checks
left join {{ ref('stg_nfk__fiscal_calendar') }} calendar
    on calendar.week_label = checks.week_label
