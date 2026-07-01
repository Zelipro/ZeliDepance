-- ZeliDepense — schema Supabase pour la synchronisation cloud.
-- A executer une seule fois dans : Supabase Dashboard > SQL Editor > New query.
--
-- Ce projet Supabase est deja utilise par l'application Version-3, qui
-- possede sa propre table "depenses" (colonnes liste_id, sans user_id).
-- Pour ne jamais toucher a cette structure existante, la version
-- multi-utilisateurs utilise un nom de table distinct : depenses_multiuser.
-- La table "users" est un nom neuf, Version-3 ne l'utilise pas (elle a une
-- table "utilisateur" au singulier, cote local uniquement, jamais synchronisee).

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

create table if not exists public.depenses_multiuser (
    id bigint generated always as identity primary key,
    user_id bigint references public.users(id) on delete cascade,
    description text,
    montant double precision,
    categorie text,
    date text
);

-- Row Level Security : necessaire des qu'une table est exposee via l'API REST.
-- L'application ne passe pas par Supabase Auth (elle gere ses propres comptes
-- et mots de passe), donc l'acces est ouvert a quiconque possede la cle "anon".
-- Ne partagez jamais cette cle en dehors de l'application, et ne l'affichez
-- jamais publiquement (dépôt de code, capture d'ecran, etc.). Dans ZeliDepense,
-- l'admin la saisit dans le panneau Administration ; elle n'est jamais
-- enregistree dans le code source.
alter table public.users enable row level security;
alter table public.depenses_multiuser enable row level security;

drop policy if exists "allow anon all users" on public.users;
create policy "allow anon all users" on public.users for all using (true) with check (true);

drop policy if exists "allow anon all depenses_multiuser" on public.depenses_multiuser;
create policy "allow anon all depenses_multiuser" on public.depenses_multiuser for all using (true) with check (true);
