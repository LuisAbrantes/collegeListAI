# Database Migrations

This directory contains SQL migration files that are managed by the Supabase CLI.

## Usage

### Prerequisites

The Supabase CLI is available via npx:

```bash
npx supabase --version
```

### Link to Remote Project

First, link your local project to your Supabase remote project:

```bash
npx supabase link --project-ref <your-project-ref>
```

You'll need the database password which can be found in your Supabase dashboard.

### Create a New Migration

```bash
npx supabase migration new <migration_name>
```

This creates a new file with the timestamp prefix: `YYYYMMDDHHMMSS_migration_name.sql`

### Apply Migrations to Remote

```bash
npx supabase db push
```

### View Migration Status

```bash
npx supabase migration list
```

### Pull Schema from Remote

If you've made changes in the Supabase dashboard:

```bash
npx supabase db pull
```

## Current Migrations

| Version | Name | Description |
|---------|------|-------------|
| 20241201000000 | initial_setup | Base schema with user_profiles, colleges_cache, vector search |
| 20241202000000 | add_student_classification | Extended profile fields for international/domestic classification |

## Important Notes

- Never modify applied migrations - create new ones instead
- All migrations run in order by timestamp
- Always test migrations locally first using `npx supabase db reset`
