{#
    Line value normalisation for the Nordfalk extract.

    The till value carries 25% VAT and, on drinks lines, the container
    deposit. The deposit is not VAT bearing in the client's till system, so
    it comes off the gross value *before* the VAT division. Getting this the
    wrong way round understates net sales on drinks by about 0.6% and the
    reconciliation against Finance fails on category 20.
#}

{% macro nfk_deposit_dkk(pant_type, antal) %}
    case
        when {{ pant_type }} = 'A' then {{ var('deposit_a_dkk') }} * greatest({{ antal }}, 0)
        when {{ pant_type }} = 'B' then {{ var('deposit_b_dkk') }} * greatest({{ antal }}, 0)
        when {{ pant_type }} = 'C' then {{ var('deposit_c_dkk') }} * greatest({{ antal }}, 0)
        else 0
    end
{% endmacro %}


{% macro nfk_net_value(gross_dkk, pant_type, antal) %}
    (({{ gross_dkk }} - {{ nfk_deposit_dkk(pant_type, antal) }}) / (1 + {{ var('vat_rate') }}))
{% endmacro %}


{% macro nfk_to_eur(value_dkk) %}
    ({{ value_dkk }} / {{ var('dkk_per_eur') }})
{% endmacro %}
