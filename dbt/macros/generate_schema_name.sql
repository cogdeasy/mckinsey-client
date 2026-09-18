{#
    Custom schema naming. On prod the mart schemas are flat (nfk_marts,
    nfk_staging), because the client's BI tool cannot see nested schemas.
    On dev everything is prefixed with the developer's own schema.
#}

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- elif target.name == 'prod' -%}
        nfk_{{ custom_schema_name | trim }}
    {%- else -%}
        {{ default_schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
