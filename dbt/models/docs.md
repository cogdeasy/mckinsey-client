{% docs nfk_sales_grain %}

Weekly sales at store x article grain as delivered by the client's SAP
extract. One line per store, article and calendar week, gross of 25% VAT
and of the container deposit on drinks lines.

Returns arrive as separate lines with negative units and negative value in
the week the return was taken, not the week of the original sale.

{% enddocs %}


{% docs nfk_fiscal_calendar %}

Nordfalk run a 4-4-5 fiscal calendar. The fiscal year starts on the first
Monday of October and is numbered by the calendar year it ends in, so the
week of 03/10/2022 is FY2023 period 1 week 1. Every fourth year carries a
53rd week, which Finance add to period 14.

The mapping is published once a year by Finance and loaded as-is. It is
never derived in code: two of the years do not follow the 4-4-5 pattern
exactly because of the Easter shift.

{% enddocs %}


{% docs nfk_mart_sales_weekly %}

The primary mart behind the forecasting asset. One row per store, article
and week with the promotion, shelf price, stock availability and calendar
attributes attached.

Values are net of VAT and deposit. Stores outside engagement scope
(franchise, partner, depots and the HQ test store), and the internal
categories 98 and 99, are already excluded here.

{% enddocs %}
