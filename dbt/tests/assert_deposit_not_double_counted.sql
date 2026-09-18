-- Net value must always be below the gross value for deposit bearing
-- articles, and the gap must be at least the deposit itself. Catches the
-- case where the deposit is stripped after the VAT division.

select
    store_id,
    sku_id,
    week_label,
    gross_value_dkk,
    net_value_dkk
from {{ ref('mart_sales_weekly') }}
where deposit_type is not null
  and units > 0
  and net_value_dkk > gross_value_dkk / (1 + {{ var('vat_rate') }})
