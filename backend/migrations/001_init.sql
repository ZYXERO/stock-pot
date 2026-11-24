-- 001: recipes table with pgvector
create extension if not exists vector;

create table if not exists recipes (
  id bigint primary key,
  title text not null,
  ingredients text[] not null,
  steps text[] not null,
  cook_minutes int,
  tags text[] default '{}',
  embedding vector(1536)
);

-- Supabase exposes public tables over its REST API; with RLS on and no policies,
-- anon/publishable keys can't read or write. The backend connects as postgres and bypasses RLS.
alter table recipes enable row level security;