{#
    Store, region and article code handling.

    Store numbers are four characters and the first two are the old amt
    number Nordfalk still use as a region. Depots share the numbering space
    and start with a 9; the HQ test store is 1199.
#}

{% macro nfk_store_id(butik_id) %}
    lpad(trim(cast({{ butik_id }} as varchar)), 4, '0')
{% endmacro %}


{% macro nfk_region_from_store_id(butik_id) %}
    substring({{ nfk_store_id(butik_id) }} from 1 for 2)
{% endmacro %}


{% macro nfk_is_real_store(butik_id) %}
    (
        {{ nfk_store_id(butik_id) }} ~ '^[0-9]{4}$'
        and substring({{ nfk_store_id(butik_id) }} from 1 for 1) <> '9'
        and substring({{ nfk_store_id(butik_id) }} from 3 for 2) <> '99'
    )
{% endmacro %}


{% macro nfk_sku_id(vare_nr) %}
    lpad(trim(cast({{ vare_nr }} as varchar)), 5, '0')
{% endmacro %}


{% macro nfk_category_code(underkategori) %}
    substring(lpad(trim(cast({{ underkategori }} as varchar)), 4, '0') from 1 for 2)
{% endmacro %}
