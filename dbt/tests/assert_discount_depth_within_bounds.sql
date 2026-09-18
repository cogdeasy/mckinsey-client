-- Depth outside 0-70% means the normal price on the campaign file is wrong.
-- Anything above 70% has always been a data entry error, never a real offer.

select
    week_label,
    sku_id,
    discount_depth
from {{ ref('mart_sales_weekly') }}
where discount_depth < 0
   or discount_depth > 0.70
