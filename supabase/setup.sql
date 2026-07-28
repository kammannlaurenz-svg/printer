-- ============================================================
--  Bondrucker – Supabase Setup
--  Im Supabase-Dashboard unter  SQL Editor  ausführen.
--  Die Abschnitte 1 und 2 kannst du JETZT ausführen.
--  Abschnitt 3 (RLS) erst NACH dem neuen Agent (Schritt B).
-- ============================================================


-- ------------------------------------------------------------
-- ABSCHNITT 1 – Fehlende Spalten ergänzen  (jetzt ausführen)
--   Ändert vorhandene Daten nicht. Fügt nur Spalten hinzu,
--   falls sie noch fehlen.
-- ------------------------------------------------------------
alter table print_jobs add column if not exists error_message text;
alter table print_jobs add column if not exists filename      text;
alter table print_jobs add column if not exists printed_at    timestamptz;


-- ------------------------------------------------------------
-- ABSCHNITT 2 – Verstecktes Passwort  (jetzt ausführen)
--   Das Passwort wird GEHASHT gespeichert und steht nirgends
--   im Frontend-Code. Die App prüft es über die Funktion
--   verify_web_password().
--
--   >>> WICHTIG: 'DEIN_PASSWORT_HIER' unten durch dein
--       gewünschtes Passwort ersetzen (z. B. 1234 oder neu).
-- ------------------------------------------------------------
-- Supabase installiert pgcrypto ins Schema "extensions".
-- Deshalb werden crypt()/gen_salt() unten mit "extensions." aufgerufen.
create extension if not exists pgcrypto with schema extensions;

create table if not exists app_secrets (
  name  text primary key,
  value text not null
);

-- Nur per Funktion lesbar (RLS an, absichtlich KEINE Policy):
alter table app_secrets enable row level security;

-- Passwort setzen / ändern (gehasht):
insert into app_secrets (name, value)
values ('web_password', extensions.crypt('DEIN_PASSWORT_HIER', extensions.gen_salt('bf')))
on conflict (name) do update set value = excluded.value;

-- Prüf-Funktion: gibt true/false zurück:
create or replace function verify_web_password(pw text)
returns boolean
language sql
security definer
set search_path = public, extensions
as $$
  select exists (
    select 1 from app_secrets
    where name = 'web_password'
      and value = extensions.crypt(pw, value)
  );
$$;

revoke all on function verify_web_password(text) from public;
grant execute on function verify_web_password(text) to anon, authenticated;


-- ============================================================
-- ABSCHNITT 3 – Sicherheit (RLS)
--   >>> ERST AUSFÜHREN, wenn der NEUE Agent (Schritt B) läuft
--       und den geheimen service_role-Key benutzt!
--
--   Grund: service_role umgeht RLS und darf weiter alles.
--   Der ALTE Agent benutzt aber nur den öffentlichen Key –
--   sobald RLS an ist, kann er Aufträge nicht mehr auf
--   "printed" setzen. Deshalb erst nach dem Umstieg.
-- ============================================================
-- alter table print_jobs enable row level security;
--
-- -- Handy/Frontend darf neue Aufträge anlegen:
-- drop policy if exists "anon insert jobs" on print_jobs;
-- create policy "anon insert jobs" on print_jobs
--   for insert to anon
--   with check (status = 'pending');
--
-- -- Handy/Frontend darf Aufträge lesen (für den Verlauf):
-- drop policy if exists "anon read jobs" on print_jobs;
-- create policy "anon read jobs" on print_jobs
--   for select to anon
--   using (true);
