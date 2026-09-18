-- Four digit stores only. The 2023 master file arrived with a leading
-- apostrophe on some rows after the client changed their export tool.

select store_id
from {{ ref('stg_nfk__stores') }}
where store_id !~ '^[0-9]{4}$'
