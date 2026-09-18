-- Sales must never arrive for a week the client's fiscal calendar does not
-- know about. Happens when Finance forget to publish the new FY calendar in
-- September; it has broken the Monday run twice.

select
    sales.week_label,
    count(*) as line_count
from {{ ref('stg_nfk__sales') }} sales
left join {{ ref('stg_nfk__fiscal_calendar') }} calendar
    on calendar.week_label = sales.week_label
where calendar.week_label is null
group by 1
