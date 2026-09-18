{% snapshot snap_pris_historik %}

{{
    config(
        target_schema='snapshots',
        unique_key="vare_nr || '-' || region_kode",
        strategy='check',
        check_cols=['pris_dkk', 'gyldig_fra', 'gyldig_til']
    )
}}

select
    vare_nr,
    region_kode,
    pris_dkk,
    gyldig_fra,
    gyldig_til
from {{ source('nfk_raw', 'pris_historik') }}

{% endsnapshot %}
