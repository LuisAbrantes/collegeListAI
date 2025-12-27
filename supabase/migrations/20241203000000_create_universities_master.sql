-- Universities Master Table
-- Verified university data for scoring engine
-- Migration: 20241203000000_create_universities_master.sql

-- Create universities_master table
CREATE TABLE IF NOT EXISTS universities_master (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic Info
    name TEXT NOT NULL UNIQUE,
    ipeds_id TEXT,  -- IPEDS Unit ID
    official_url TEXT,
    state TEXT,
    campus_setting TEXT CHECK (campus_setting IN ('URBAN', 'SUBURBAN', 'RURAL', 'TOWN')),
    
    -- Admission Statistics
    acceptance_rate DECIMAL(5,4),  -- 0.0000-1.0000
    median_gpa DECIMAL(3,2),  -- 0.00-4.00
    sat_25th INTEGER CHECK (sat_25th >= 400 AND sat_25th <= 1600),
    sat_75th INTEGER CHECK (sat_75th >= 400 AND sat_75th <= 1600),
    act_25th INTEGER CHECK (act_25th >= 1 AND act_25th <= 36),
    act_75th INTEGER CHECK (act_75th >= 1 AND act_75th <= 36),
    
    -- Tuition (USD per year)
    tuition_in_state DECIMAL(10,2),
    tuition_out_of_state DECIMAL(10,2),
    tuition_international DECIMAL(10,2),
    
    -- Financial Aid
    need_blind_domestic BOOLEAN DEFAULT TRUE,
    need_blind_international BOOLEAN DEFAULT FALSE,
    meets_full_need BOOLEAN DEFAULT FALSE,
    avg_aid_package DECIMAL(10,2),
    
    -- Metadata
    data_source TEXT DEFAULT 'manual',  -- IPEDS, Common_Data_Set, Gemini_Verified
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_universities_master_name 
    ON universities_master USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_universities_master_state 
    ON universities_master(state);

-- Create university_majors table for major-specific data
CREATE TABLE IF NOT EXISTS university_majors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    university_id UUID REFERENCES universities_master(id) ON DELETE CASCADE,
    
    major_name TEXT NOT NULL,
    major_ranking INTEGER,  -- 1-based ranking in this field
    ranking_source TEXT,  -- e.g., 'US News 2024', 'QS 2024'
    program_size TEXT CHECK (program_size IN ('SMALL', 'MEDIUM', 'LARGE')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(university_id, major_name)
);

CREATE INDEX IF NOT EXISTS idx_university_majors_major 
    ON university_majors USING gin(to_tsvector('english', major_name));

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_universities_master_updated_at
    BEFORE UPDATE ON universities_master
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_university_majors_updated_at
    BEFORE UPDATE ON university_majors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Seed data: Need-blind schools for international students
INSERT INTO universities_master (name, acceptance_rate, need_blind_international, meets_full_need, campus_setting, state, data_source)
VALUES 
    ('Harvard University', 0.032, TRUE, TRUE, 'URBAN', 'MA', 'Common_Data_Set'),
    ('Yale University', 0.045, TRUE, TRUE, 'URBAN', 'CT', 'Common_Data_Set'),
    ('Princeton University', 0.040, TRUE, TRUE, 'SUBURBAN', 'NJ', 'Common_Data_Set'),
    ('Massachusetts Institute of Technology', 0.039, TRUE, TRUE, 'URBAN', 'MA', 'Common_Data_Set'),
    ('Amherst College', 0.070, TRUE, TRUE, 'SUBURBAN', 'MA', 'Common_Data_Set')
ON CONFLICT (name) DO UPDATE SET
    acceptance_rate = EXCLUDED.acceptance_rate,
    need_blind_international = EXCLUDED.need_blind_international,
    meets_full_need = EXCLUDED.meets_full_need,
    last_verified_at = NOW();

-- RLS policies
ALTER TABLE universities_master ENABLE ROW LEVEL SECURITY;
ALTER TABLE university_majors ENABLE ROW LEVEL SECURITY;

-- Allow read access to all authenticated users
CREATE POLICY "Allow read access to universities" ON universities_master
    FOR SELECT USING (true);

CREATE POLICY "Allow read access to university majors" ON university_majors
    FOR SELECT USING (true);

-- Comment the tables
COMMENT ON TABLE universities_master IS 'Verified university data for scoring engine';
COMMENT ON TABLE university_majors IS 'Major-specific rankings and program data';
