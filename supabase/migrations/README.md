# Supabase Migrations

This directory contains SQL migration files for the College List AI database.

## Files

- **`complete_setup.sql`** - Complete database setup (run this first)
  - Creates all tables (profiles, colleges_cache, user_exclusions)
  - Creates vector search functions
  - Sets up RLS policies
  - Creates indexes for performance

## How to apply migrations

1. Open your Supabase project dashboard
2. Go to SQL Editor
3. Copy the contents of `complete_setup.sql`
4. Run the SQL
5. ✅ Done!

## Schema Overview

### Tables
- `profiles` - User profiles (nationality, GPA, major)
- `colleges_cache` - Colleges with embeddings for vector search
- `user_exclusions` - User's blacklisted colleges

### Functions
- `match_colleges()` - Basic vector similarity search
- `match_colleges_excluding()` - Search with exclusions
- `get_user_exclusions()` - Get user's blacklist
- `match_colleges_for_user()` - Combined search with auto-exclusions
