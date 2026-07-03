-- ZeliDepense (version multi-utilisateurs) — schema Supabase.
--
-- ⚠️ SI TU UTILISES LE PROJET SUPABASE DE VERSION-3 : RIEN A EXECUTER.
-- L'application reutilise telles quelles les tables existantes de Version-3
-- (listes_depenses et depenses) et la table users deja creee. Aucune
-- modification de structure n'est necessaire ni effectuee.
--
-- Ce script ne sert QUE pour un projet Supabase entierement NEUF (vide).
-- Il recree alors le meme schema que celui attendu :

create table if not exists public.users (
    id bigint generated always as identity primary key,
    username text unique not null,
    nom text,
    password_hash text not null,
    salt text not null,
    role text default 'user',
    is_approved integer default 0,
    section_pin_hash text,
    section_pin_salt text,
    created_at text
);

create table if not exists public.listes_depenses (
    id bigint generated always as identity primary key,
    nom text unique not null,
    date_creation text
);

create table if not exists public.depenses (
    id bigint generated always as identity primary key,
    liste_id bigint references public.listes_depenses(id) on delete cascade,
    description text,
    montant double precision,
    categorie text,
    date text
);

-- Row Level Security : l'application gere ses propres comptes (pas de
-- Supabase Auth), donc l'acces est ouvert a quiconque possede la cle "anon".
-- Ne partagez jamais cette cle publiquement. Dans ZeliDepense, l'admin la
-- saisit dans le panneau Administration ; elle n'est jamais dans le code.
alter table public.users enable row level security;
alter table public.listes_depenses enable row level security;
alter table public.depenses enable row level security;

drop policy if exists "allow anon all users" on public.users;
create policy "allow anon all users" on public.users for all using (true) with check (true);

drop policy if exists "allow anon all listes_depenses" on public.listes_depenses;
create policy "allow anon all listes_depenses" on public.listes_depenses for all using (true) with check (true);

drop policy if exists "allow anon all depenses" on public.depenses;
create policy "allow anon all depenses" on public.depenses for all using (true) with check (true);
