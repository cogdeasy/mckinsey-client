{% snapshot snap_vare_hierarki %}

{{
    config(
        target_schema='snapshots',
        unique_key='vare_nr',
        strategy='check',
        check_cols=['underkategori', 'pant_type', 'leverandoer_id', 'kolli'],
        invalidate_hard_deletes=True
    )
}}

-- Articles are re-hierarchised a couple of times a year. Without this
-- snapshot the category mix restates and the year on year numbers in the
-- steerco pack move.

select
    vare_nr,
    vare_tekst,
    underkategori,
    pant_type,
    leverandoer_id,
    kolli,
    vejl_pris_dkk,
    ferskvare
from {{ source('nfk_raw', 'vare_hierarki') }}

{% endsnapshot %}
