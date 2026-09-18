{{
    config(
        materialized='ephemeral',
        tags=['intermediate', 'sales']
    )
}}

-- Deposit and VAT stripped, returns netted into the sale week, out of scope
-- stores and the internal categories (98 catering, 99 non merchandise)
-- removed.

with sales as (

    select * from {{ ref('stg_nfk__sales') }}

),

articles as (

    select * from {{ ref('stg_nfk__articles') }}

),

stores as (

    select * from {{ ref('stg_nfk__stores') }}

),

joined as (

    select
        sales.store_id,
        sales.sku_id,
        sales.week_label,
        sales.calendar_year,
        sales.iso_week,
        sales.region_code,
        sales.units,
        sales.gross_value_dkk,
        sales.promo_code,
        sales.promo_flag,
        sales.source_key,
        articles.category_code,
        articles.subcategory_code,
        articles.deposit_type,
        articles.is_fresh,
        articles.case_pack,
        articles.supplier_id,
        stores.store_format,
        stores.store_status,
        stores.sales_area_sqm,
        stores.is_in_scope
    from sales
    inner join articles on articles.sku_id = sales.sku_id
    inner join stores on stores.store_id = sales.store_id

)

select
    store_id,
    sku_id,
    week_label,
    calendar_year,
    iso_week,
    region_code,
    category_code,
    subcategory_code,
    deposit_type,
    supplier_id,
    case_pack,
    is_fresh,
    store_format,
    sales_area_sqm,
    sum(units)                                                      as units,
    sum(gross_value_dkk)                                            as gross_value_dkk,
    sum({{ nfk_net_value('gross_value_dkk', 'deposit_type', 'units') }}) as net_value_dkk,
    sum({{ nfk_to_eur(nfk_net_value('gross_value_dkk', 'deposit_type', 'units')) }}) as net_value_eur,
    max(promo_flag)                                                 as promo_flag,
    max(promo_code)                                                 as promo_code,
    count(*)                                                        as line_count,
    sum(case when units < 0 then 1 else 0 end)                      as return_line_count
from joined
where is_in_scope = 1
  and store_format not in ({{ "'" ~ var('excluded_store_formats') | join("', '") ~ "'" }})
  and category_code not in ({{ "'" ~ var('excluded_category_codes') | join("', '") ~ "'" }})
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14
