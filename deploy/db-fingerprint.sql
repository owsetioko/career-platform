-- Each table's exact row count and content checksum, plus each sequence's position.
-- Compare the output from two databases with diff. Sorting uses collate "C" because
-- text order otherwise differs between servers (en_US.utf8 vs C.UTF-8).
select 'table' as kind, c.relname as name,
       (xpath('/row/n/text()', query_to_xml(format('select count(*) as n from public.%I', c.relname), false, true, '')))[1]::text as value,
       (xpath('/row/h/text()', query_to_xml(format('select md5(coalesce(string_agg(t::text, ''|'' order by t::text collate "C"), '''')) as h from public.%I t', c.relname), false, true, '')))[1]::text as checksum
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r'
union all
select 'sequence', sequencename, coalesce(last_value::text, 'unused'), ''
from pg_sequences where schemaname = 'public'
order by 1, 2;
