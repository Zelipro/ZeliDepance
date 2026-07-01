-- ZeliDepense — schema Supabase pour la synchronisation cloud.
-- A executer une seule fois dans : Supabase Dashboard > SQL Editor > New query.

create table if not exists public.users (
    uuid text primary key,
    username text unique not null,
    nom text,
    password_hash text not null,
    salt text not null,
    role text default 'user',
    is_approved integer default 0,
    section_pin_hash text,
    section_pin_salt text,
    created_at text,
    updated_at text,
    deleted integer default 0
);

create table if not exists public.depenses (
    uuid text primary key,
    user_uuid text references public.users(uuid),
    description text,
    montant double precision,
    categorie text,
    date text,
    updated_at text,
    deleted integer default 0
);

create table if not exists public.user_preferences (
    user_uuid text primary key references public.users(uuid),
    wallpaper_path text,
    updated_at text
);

-- Row Level Security : necessaire des qu'une table est exposee via l'API REST.
-- L'application ne passe pas par Supabase Auth (elle gere ses propres comptes
-- et mots de passe), donc l'acces est ouvert a quiconque possede la cle "anon".
-- Ne partagez jamais cette cle en dehors de l'application, et ne l'affichez
-- jamais publiquement (dépôt de code public, capture d'ecran, etc.).
alter table public.users enable row level security;
alter table public.depenses enable row level security;
alter table public.user_preferences enable row level security;

drop policy if exists "allow anon all users" on public.users;
create policy "allow anon all users" on public.users for all using (true) with check (true);

drop policy if exists "allow anon all depenses" on public.depenses;
create policy "allow anon all depenses" on public.depenses for all using (true) with check (true);

drop policy if exists "allow anon all user_preferences" on public.user_preferences;
create policy "allow anon all user_preferences" on public.user_preferences for all using (true) with check (true);
