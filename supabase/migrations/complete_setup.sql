-- ============================================================================
-- College List AI: Complete Database Setup (Fresh Start)
-- ============================================================================
-- This script will:
-- 1. Drop all existing tables and functions
-- 2. Create tables with correct structure
-- 3. Create vector search functions
-- 4. Set up RLS policies
-- 5. Create indexes for performance
--
-- Run this ONCE in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- STEP 1: Clean slate - Drop everything
-- ============================================================================

-- Drop functions first
DROP FUNCTION IF EXISTS match_colleges_for_user CASCADE;
DROP FUNCTION IF EXISTS get_user_exclusions CASCADE;
DROP FUNCTION IF EXISTS match_colleges_excluding CASCADE;
DROP FUNCTION IF EXISTS match_colleges CASCADE;

-- Drop tables (in reverse dependency order)
DROP TABLE IF EXISTS user_exclusions CASCADE;
DROP TABLE IF EXISTS colleges_cache CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;

-- ============================================================================
-- STEP 2: Enable extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- STEP 3: Create tables
-- ============================================================================

-- Profiles table (linked to auth.users)
CREATE TABLE profiles (
  id uuid REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  nationality text NOT NULL,
  gpa float CHECK (gpa >= 0 AND gpa <= 4.0),
  major text NOT NULL,
  financial_need boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

-- Colleges cache with embeddings
CREATE TABLE colleges_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text UNIQUE NOT NULL,
  content text, -- JSON string with college data
  embedding vector(768), -- Gemini text-embedding-004
  last_updated timestamp with time zone DEFAULT now()
);

-- User exclusions (blacklist)
CREATE TABLE user_exclusions (
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  college_name text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (user_id, college_name)
);

-- ============================================================================
-- STEP 4: Create vector search functions
-- ============================================================================

-- Basic similarity search
CREATE OR REPLACE FUNCTION match_colleges(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    name text,
    content text,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cc.id,
        cc.name,
        cc.content,
        (1 - (cc.embedding <=> query_embedding))::float AS similarity
    FROM 
        colleges_cache cc
    WHERE 
        (1 - (cc.embedding <=> query_embedding)) > match_threshold
    ORDER BY 
        cc.embedding <=> query_embedding
    LIMIT 
        match_count;
END;
$$;

-- Search with exclusions
CREATE OR REPLACE FUNCTION match_colleges_excluding(
    query_embedding vector(768),
    excluded_names text[],
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    name text,
    content text,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cc.id,
        cc.name,
        cc.content,
        (1 - (cc.embedding <=> query_embedding))::float AS similarity
    FROM 
        colleges_cache cc
    WHERE 
        (1 - (cc.embedding <=> query_embedding)) > match_threshold
        AND cc.name != ALL(excluded_names)
    ORDER BY 
        cc.embedding <=> query_embedding
    LIMIT 
        match_count;
END;
$$;

-- Get user's excluded college names
CREATE OR REPLACE FUNCTION get_user_exclusions(
    p_user_id uuid
)
RETURNS text[]
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    exclusion_names text[];
BEGIN
    SELECT ARRAY_AGG(college_name)
    INTO exclusion_names
    FROM user_exclusions
    WHERE user_id = p_user_id;
    
    RETURN COALESCE(exclusion_names, ARRAY[]::text[]);
END;
$$;

-- Combined search for user (with automatic exclusions)
CREATE OR REPLACE FUNCTION match_colleges_for_user(
    query_embedding vector(768),
    p_user_id uuid,
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    name text,
    content text,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    excluded_names text[];
BEGIN
    excluded_names := get_user_exclusions(p_user_id);
    
    RETURN QUERY
    SELECT * FROM match_colleges_excluding(
        query_embedding,
        excluded_names,
        match_threshold,
        match_count
    );
END;
$$;

-- ============================================================================
-- STEP 5: Create indexes for performance
-- ============================================================================

-- Vector similarity index (IVFFlat for fast approximate search)
CREATE INDEX idx_colleges_embedding_ivfflat
ON colleges_cache
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Regular indexes
CREATE INDEX idx_colleges_name ON colleges_cache(name);
CREATE INDEX idx_colleges_updated ON colleges_cache(last_updated);
CREATE INDEX idx_profiles_updated_at ON profiles(updated_at);
CREATE INDEX idx_user_exclusions_user_id ON user_exclusions(user_id);
CREATE INDEX idx_user_exclusions_college ON user_exclusions(college_name);
CREATE INDEX idx_user_exclusions_lookup ON user_exclusions(user_id, college_name);

-- ============================================================================
-- STEP 6: Enable Row Level Security (RLS)
-- ============================================================================

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE colleges_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_exclusions ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can delete own profile"
  ON profiles FOR DELETE
  USING (auth.uid() = id);

-- Colleges cache policies (read-only for users)
CREATE POLICY "Anyone can view colleges"
  ON colleges_cache FOR SELECT
  TO authenticated
  USING (true);

-- User exclusions policies
CREATE POLICY "Users can view own exclusions"
  ON user_exclusions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own exclusions"
  ON user_exclusions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own exclusions"
  ON user_exclusions FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================================================
-- STEP 7: Grant permissions
-- ============================================================================

-- Grant function execution to authenticated users
GRANT EXECUTE ON FUNCTION match_colleges TO authenticated;
GRANT EXECUTE ON FUNCTION match_colleges_excluding TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_exclusions TO authenticated;
GRANT EXECUTE ON FUNCTION match_colleges_for_user TO authenticated;

-- Grant to service role for backend operations
GRANT EXECUTE ON FUNCTION match_colleges TO service_role;
GRANT EXECUTE ON FUNCTION match_colleges_excluding TO service_role;
GRANT EXECUTE ON FUNCTION get_user_exclusions TO service_role;
GRANT EXECUTE ON FUNCTION match_colleges_for_user TO service_role;

-- ============================================================================
-- STEP 8: Insert sample data (optional - for testing)
-- ============================================================================

-- Uncomment to insert test data:
/*
INSERT INTO colleges_cache (name, content) VALUES
  ('MIT', '{"acceptance_rate": 3.9, "avg_gpa": 3.9, "location": "Cambridge, MA"}'),
  ('Stanford', '{"acceptance_rate": 3.7, "avg_gpa": 3.95, "location": "Stanford, CA"}'),
  ('Harvard', '{"acceptance_rate": 3.4, "avg_gpa": 3.9, "location": "Cambridge, MA"}');
*/

-- ============================================================================
-- Setup complete!
-- ============================================================================
