{% snapshot snap_butik_stamdata %}

{{
    config(
        target_schema='snapshots',
        unique_key='butik_id',
        strategy='check',
        check_cols=['region_kode', 'type', 'status', 'salgsareal_m2'],
        invalidate_hard_deletes=True
    )
}}

-- The store master is overwritten in full every Friday and the client keeps
-- no history. Refits and format changes are only visible here.

select
    butik_id,
    butik_navn,
    region_kode,
    type,
    status,
    salgsareal_m2,
    aabnet_dato,
    lukket_dato
from {{ source('nfk_raw', 'butik_stamdata') }}

{% endsnapshot %}
