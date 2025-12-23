-- ============================================================================
-- College List AI: Add Student Classification & Fit Factors
-- ============================================================================
-- This migration adds:
-- 1. Citizenship status enum for domestic vs international determination
-- 2. Test scores (SAT/ACT) and English proficiency
-- 3. Financial info (income tier)
-- 4. Fit factors (campus vibe, athlete status, legacy, post-grad goals)
--
-- Run this in Supabase SQL Editor after the initial complete_setup.sql
-- ============================================================================

-- ============================================================================
-- STEP 1: Create new enum types
-- ============================================================================

-- Citizenship status for financial aid branching
CREATE TYPE citizenship_status AS ENUM (
    'US_CITIZEN',
    'PERMANENT_RESIDENT',
    'INTERNATIONAL',
    'DACA'
);

-- Household income tier for aid estimation
CREATE TYPE household_income_tier AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH'
);

-- Campus environment preference
CREATE TYPE campus_vibe AS ENUM (
    'URBAN',
    'SUBURBAN',
    'RURAL'
);

-- Post-graduation career focus
CREATE TYPE post_grad_goal AS ENUM (
    'JOB_PLACEMENT',
    'GRADUATE_SCHOOL',
    'ENTREPRENEURSHIP',
    'UNDECIDED'
);

-- ============================================================================
-- STEP 2: Add new columns to profiles table
-- ============================================================================

-- Core identification
ALTER TABLE profiles ADD COLUMN citizenship_status citizenship_status;

-- Make nationality optional (was required before)
ALTER TABLE profiles ALTER COLUMN nationality DROP NOT NULL;

-- Academic test scores
ALTER TABLE profiles ADD COLUMN sat_score INTEGER CHECK (sat_score >= 400 AND sat_score <= 1600);
ALTER TABLE profiles ADD COLUMN act_score INTEGER CHECK (act_score >= 1 AND act_score <= 36);

-- US-specific: state for in-state tuition calculation
ALTER TABLE profiles ADD COLUMN state_of_residence TEXT;

-- Financial info
ALTER TABLE profiles ADD COLUMN household_income_tier household_income_tier;

-- International-specific: English proficiency (TOEFL/IELTS converted to 0-120 scale)
ALTER TABLE profiles ADD COLUMN english_proficiency_score INTEGER CHECK (english_proficiency_score >= 0 AND english_proficiency_score <= 120);

-- Fit factors
ALTER TABLE profiles ADD COLUMN campus_vibe campus_vibe;
ALTER TABLE profiles ADD COLUMN is_student_athlete BOOLEAN DEFAULT FALSE;
ALTER TABLE profiles ADD COLUMN has_legacy_status BOOLEAN DEFAULT FALSE;
ALTER TABLE profiles ADD COLUMN legacy_universities TEXT[];
ALTER TABLE profiles ADD COLUMN post_grad_goal post_grad_goal;

-- ============================================================================
-- STEP 3: Create indexes for new columns
-- ============================================================================

CREATE INDEX idx_profiles_citizenship ON profiles(citizenship_status);
CREATE INDEX idx_profiles_state ON profiles(state_of_residence);
CREATE INDEX idx_profiles_income_tier ON profiles(household_income_tier);

-- ============================================================================
-- STEP 4: Add comments for documentation
-- ============================================================================

COMMENT ON COLUMN profiles.citizenship_status IS 'Student citizenship/residency status for financial aid branching';
COMMENT ON COLUMN profiles.state_of_residence IS 'US state for in-state tuition calculation (US residents only)';
COMMENT ON COLUMN profiles.sat_score IS 'SAT score (400-1600)';
COMMENT ON COLUMN profiles.act_score IS 'ACT score (1-36)';
COMMENT ON COLUMN profiles.household_income_tier IS 'Income tier for financial aid estimation';
COMMENT ON COLUMN profiles.english_proficiency_score IS 'TOEFL/IELTS score for internationals (0-120 scale)';
COMMENT ON COLUMN profiles.campus_vibe IS 'Preferred campus environment (urban/suburban/rural)';
COMMENT ON COLUMN profiles.is_student_athlete IS 'Whether pursuing athletic recruitment';
COMMENT ON COLUMN profiles.has_legacy_status IS 'Whether has family alumni connections';
COMMENT ON COLUMN profiles.legacy_universities IS 'Array of universities with legacy status';
COMMENT ON COLUMN profiles.post_grad_goal IS 'Post-graduation career focus';

-- ============================================================================
-- Migration complete!
-- ============================================================================
