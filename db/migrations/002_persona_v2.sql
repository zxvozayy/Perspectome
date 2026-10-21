-- Perspectome database, version 2 (persona contract v2).
--
-- - personas carry values: religiosity_band and political_leaning_band are
--   conditioning fields now (schema.CONDITIONING_FIELDS);
-- - synthetic persona sets sit next to the real core: persona_sets.kind says
--   which, and a synthetic set points at the core it was drawn from;
-- - attached features (schema.SYNTHETIC_FIELDS: household, work, lifestyle,
--   concerns) go into personas.attrs, so adding one needs no migration;
-- - the panel no longer keeps chat history, so app.chats goes.

alter table personas.personas
    add column if not exists religiosity_band text,
    add column if not exists political_leaning_band text,
    add column if not exists attrs jsonb;

alter table personas.persona_sets
    add column if not exists kind text not null default 'core',
    add column if not exists core_set_hash text references personas.persona_sets;

do $$
begin
    if not exists (select 1 from pg_constraint where conname = 'persona_sets_kind_check') then
        alter table personas.persona_sets
            add constraint persona_sets_kind_check check (kind in ('core', 'synthetic'));
    end if;
end $$;

drop table if exists app.chats;
