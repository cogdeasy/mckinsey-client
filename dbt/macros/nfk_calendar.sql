{#
    Calendar helpers.

    Week labels are calendar ISO labels (YYYYWW) because that is what the
    sales extract carries. The fiscal week comes from the client's own
    calendar table, never derived here: their 4-4-5 year starts on the first
    Monday of October and Finance publish the mapping once a year.

    Dates on the extract are DD/MM/YYYY strings.
#}

{% macro nfk_parse_date(column_name) %}
    to_date({{ column_name }}, 'DD/MM/YYYY')
{% endmacro %}


{% macro nfk_week_label(date_column) %}
    (
        to_char({{ date_column }}, 'IYYY') || to_char({{ date_column }}, 'IW')
    )
{% endmacro %}


{% macro nfk_week_start(date_column) %}
    date_trunc('week', {{ date_column }})::date
{% endmacro %}


{% macro nfk_fiscal_year_from_date(date_column) %}
    case
        when extract(month from {{ date_column }}) >= {{ var('fiscal_year_start_month') }}
            then extract(year from {{ date_column }}) + 1
        else extract(year from {{ date_column }})
    end
{% endmacro %}
