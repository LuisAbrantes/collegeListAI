-- Cleanup Script for Duplicate/Legacy Universities
-- Execute in Supabase SQL Editor

-- Step 1: Delete major stats for colleges without IPEDS
DELETE FROM college_major_stats 
WHERE college_id IN (
    SELECT id FROM colleges WHERE ipeds_id IS NULL
);

-- Step 2: Delete colleges without IPEDS
DELETE FROM colleges WHERE ipeds_id IS NULL;

-- Verify remaining colleges
SELECT name, ipeds_id, acceptance_rate, state 
FROM colleges 
ORDER BY name 
LIMIT 20;
