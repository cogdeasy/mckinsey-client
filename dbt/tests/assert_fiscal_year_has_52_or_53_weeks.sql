select
    fiscal_year,
    count(distinct week_label) as weeks
from {{ ref('stg_nfk__fiscal_calendar') }}
group by 1
having count(distinct week_label) not in (52, 53)
