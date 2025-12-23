/**
 * College List AI - Supabase Client Service
 *
 * Type-safe Supabase client with connection pooling configuration.
 * Provides typed wrappers for common operations.
 */

import { createClient } from '@supabase/supabase-js';
import type {
  UserProfile,
  UserProfileCreate,
  UserProfileUpdate,
  CollegeSearchResult,
  UserExclusion,
  ApiResponse,
} from '../types/api';

// ============================================================================
// Environment Configuration
// ============================================================================

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  throw new Error(
    'Missing Supabase environment variables. ' +
    'Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY'
  );
}

// ============================================================================
// Supabase Client Singleton
// ============================================================================

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
  global: {
    headers: {
      'x-client-info': 'college-list-ai',
    },
  },
  db: {
    schema: 'public',
  },
});

/**
 * Get the Supabase client instance
 */
export function getSupabaseClient() {
  return supabase;
}

// ============================================================================
// Error Handling Utilities
// ============================================================================

/**
 * Wrap Supabase errors in a consistent format
 */
function handleError(error: unknown): ApiResponse<never> {
  const err = error as { message?: string; code?: string; details?: string; hint?: string };
  return {
    data: null,
    error: {
      error: err.code ?? 'UNKNOWN_ERROR',
      message: err.message ?? 'An unexpected error occurred',
    },
  };
}

// ============================================================================
// Profile Service
// ============================================================================

export const profileService = {
  /**
   * Get the current user's profile
   */
  async getProfile(): Promise<ApiResponse<UserProfile>> {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return {
        data: null,
        error: { error: 'UNAUTHORIZED', message: 'User not authenticated' },
      };
    }

    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', user.id)
      .maybeSingle(); // Use maybeSingle() to avoid 406 when no profile exists

    if (error) {
      return handleError(error);
    }

    if (!data) {
      return {
        data: null,
        error: { error: 'NOT_FOUND', message: 'Profile not found' },
      };
    }

    return {
      data: {
        id: data.id,
        userId: data.id,
        citizenshipStatus: data.citizenship_status,
        nationality: data.nationality,
        gpa: data.gpa,
        major: data.major,
        satScore: data.sat_score,
        actScore: data.act_score,
        stateOfResidence: data.state_of_residence,
        householdIncomeTier: data.household_income_tier,
        englishProficiencyScore: data.english_proficiency_score,
        englishTestType: data.english_test_type,
        campusVibe: data.campus_vibe,
        isStudentAthlete: data.is_student_athlete ?? false,
        hasLegacyStatus: data.has_legacy_status ?? false,
        legacyUniversities: data.legacy_universities,
        postGradGoal: data.post_grad_goal,
        isFirstGen: data.is_first_gen ?? false,
        apClassCount: data.ap_class_count,
        apClasses: data.ap_classes,
        createdAt: data.created_at,
        updatedAt: data.updated_at,
      },
      error: null,
    };
  },

  /**
   * Create a new profile for the current user
   */
  async createProfile(
    profile: UserProfileCreate
  ): Promise<ApiResponse<UserProfile>> {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return {
        data: null,
        error: { error: 'UNAUTHORIZED', message: 'User not authenticated' },
      };
    }

    const { data, error } = await supabase
      .from('profiles')
      .insert({
        id: user.id,
        citizenship_status: profile.citizenshipStatus,
        nationality: profile.nationality,
        gpa: profile.gpa,
        major: profile.major,
        sat_score: profile.satScore,
        act_score: profile.actScore,
        state_of_residence: profile.stateOfResidence,
        household_income_tier: profile.householdIncomeTier,
        english_proficiency_score: profile.englishProficiencyScore,
        english_test_type: profile.englishTestType,
        campus_vibe: profile.campusVibe,
        is_student_athlete: profile.isStudentAthlete ?? false,
        has_legacy_status: profile.hasLegacyStatus ?? false,
        legacy_universities: profile.legacyUniversities,
        post_grad_goal: profile.postGradGoal,
        is_first_gen: profile.isFirstGen ?? false,
        ap_class_count: profile.apClassCount,
        ap_classes: profile.apClasses,
        financial_need: false,
      })
      .select()
      .single();

    if (error) {
      return handleError(error);
    }

    if (!data) {
      return {
        data: null,
        error: { error: 'INSERT_FAILED', message: 'Failed to create profile' },
      };
    }

    return {
      data: {
        id: data.id,
        userId: data.id,
        citizenshipStatus: data.citizenship_status,
        nationality: data.nationality,
        gpa: data.gpa,
        major: data.major,
        satScore: data.sat_score,
        actScore: data.act_score,
        stateOfResidence: data.state_of_residence,
        householdIncomeTier: data.household_income_tier,
        englishProficiencyScore: data.english_proficiency_score,
        englishTestType: data.english_test_type,
        campusVibe: data.campus_vibe,
        isStudentAthlete: data.is_student_athlete ?? false,
        hasLegacyStatus: data.has_legacy_status ?? false,
        legacyUniversities: data.legacy_universities,
        postGradGoal: data.post_grad_goal,
        isFirstGen: data.is_first_gen ?? false,
        apClassCount: data.ap_class_count,
        apClasses: data.ap_classes,
        createdAt: data.created_at,
        updatedAt: data.updated_at,
      },
      error: null,
    };
  },

  /**
   * Update the current user's profile
   */
  async updateProfile(
    updates: UserProfileUpdate
  ): Promise<ApiResponse<UserProfile>> {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return {
        data: null,
        error: { error: 'UNAUTHORIZED', message: 'User not authenticated' },
      };
    }

    const updateData: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
    };

    // Handle string fields - convert empty strings to null for enum fields
    if (updates.citizenshipStatus !== undefined) {
      updateData.citizenship_status = updates.citizenshipStatus || null;
    }
    if (updates.nationality !== undefined) {
      updateData.nationality = updates.nationality || null;
    }
    if (updates.gpa !== undefined) updateData.gpa = updates.gpa;
    if (updates.major !== undefined) updateData.major = updates.major;
    if (updates.satScore !== undefined) updateData.sat_score = updates.satScore;
    if (updates.actScore !== undefined) updateData.act_score = updates.actScore;
    if (updates.stateOfResidence !== undefined) {
      updateData.state_of_residence = updates.stateOfResidence || null;
    }
    if (updates.householdIncomeTier !== undefined) {
      updateData.household_income_tier = updates.householdIncomeTier || null;
    }
    if (updates.englishProficiencyScore !== undefined) {
      updateData.english_proficiency_score = updates.englishProficiencyScore;
    }
    if (updates.englishTestType !== undefined) {
      updateData.english_test_type = updates.englishTestType || null;
    }
    if (updates.campusVibe !== undefined) {
      updateData.campus_vibe = updates.campusVibe || null;
    }
    if (updates.isStudentAthlete !== undefined) updateData.is_student_athlete = updates.isStudentAthlete;
    if (updates.hasLegacyStatus !== undefined) updateData.has_legacy_status = updates.hasLegacyStatus;
    if (updates.legacyUniversities !== undefined) updateData.legacy_universities = updates.legacyUniversities;
    if (updates.postGradGoal !== undefined) {
      updateData.post_grad_goal = updates.postGradGoal || null;
    }
    if (updates.isFirstGen !== undefined) updateData.is_first_gen = updates.isFirstGen;
    if (updates.apClassCount !== undefined) updateData.ap_class_count = updates.apClassCount || null;
    if (updates.apClasses !== undefined) {
      updateData.ap_classes = updates.apClasses && updates.apClasses.length > 0 ? updates.apClasses : null;
    }

    const { data, error } = await supabase
      .from('profiles')
      .update(updateData)
      .eq('id', user.id)
      .select()
      .single();

    if (error) {
      return handleError(error);
    }

    if (!data) {
      return {
        data: null,
        error: { error: 'UPDATE_FAILED', message: 'Failed to update profile' },
      };
    }

    return {
      data: {
        id: data.id,
        userId: data.id,
        citizenshipStatus: data.citizenship_status,
        nationality: data.nationality,
        gpa: data.gpa,
        major: data.major,
        satScore: data.sat_score,
        actScore: data.act_score,
        stateOfResidence: data.state_of_residence,
        householdIncomeTier: data.household_income_tier,
        englishProficiencyScore: data.english_proficiency_score,
        englishTestType: data.english_test_type,
        campusVibe: data.campus_vibe,
        isStudentAthlete: data.is_student_athlete ?? false,
        hasLegacyStatus: data.has_legacy_status ?? false,
        legacyUniversities: data.legacy_universities,
        postGradGoal: data.post_grad_goal,
        isFirstGen: data.is_first_gen ?? false,
        apClassCount: data.ap_class_count,
        apClasses: data.ap_classes,
        createdAt: data.created_at,
        updatedAt: data.updated_at,
      },
      error: null,
    };
  },
};

// ============================================================================
// Exclusion Service
// ============================================================================

export const exclusionService = {
  /**
   * Get all exclusions for the current user
   */
  async getExclusions(): Promise<ApiResponse<UserExclusion[]>> {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return {
        data: null,
        error: { error: 'UNAUTHORIZED', message: 'User not authenticated' },
      };
    }

    const { data, error } = await supabase
      .from('user_exclusions')
      .select('*')
      .eq('user_id', user.id);

    if (error) {
      return handleError(error);
    }

    return {
      data: (data || []).map((row: any) => ({
        id: `${row.user_id}-${row.college_name}`,
        userId: row.user_id,
        collegeId: row.college_name,
        createdAt: row.created_at,
      })),
      error: null,
    };
  },

  /**
   * Add a college to the exclusion list
   */
  async addExclusion(collegeName: string): Promise<ApiResponse<UserExclusion>> {
    const {
      data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
      return {
        data: null,
        error: { error: 'UNAUTHORIZED', message: 'User not authenticated' },
      };
    }

    const { data, error } = await supabase
      .from('user_exclusions')
      .insert({
        user_id: user.id,
        college_name: collegeName,
      })
      .select()
      .single();

    if (error) {
      return handleError(error);
    }

    if (!data) {
      return {
        data: null,
        error: { error: 'INSERT_FAILED', message: 'Failed to add exclusion' },
      };
    }

    return {
      data: {
        id: `${data.user_id}-${data.college_name}`,
        userId: data.user_id,
        collegeId: data.college_name,
        createdAt: data.created_at,
      },
      error: null,
    };
  },

  /**
   * Remove a college from the exclusion list
   */
  async removeExclusion(userId: string, collegeName: string): Promise<ApiResponse<boolean>> {
    const { error } = await supabase
      .from('user_exclusions')
      .delete()
      .eq('user_id', userId)
      .eq('college_name', collegeName);

    if (error) {
      return handleError(error);
    }

    return { data: true, error: null };
  },
};

// ============================================================================
// Search Service (for vector similarity)
// ============================================================================

export const searchService = {
  /**
   * Search for similar colleges using the backend API
   * Note: Vector operations are handled server-side
   */
  async searchColleges(
    query: string,
    _options?: { threshold?: number; limit?: number }
  ): Promise<ApiResponse<CollegeSearchResult[]>> {
    // This would typically call your backend API
    // which handles embedding generation and vector search
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        ...(_options ?? {}),
      }),
    });

    if (!response.ok) {
      return {
        data: null,
        error: {
          error: 'SEARCH_ERROR',
          message: 'Failed to search colleges',
        },
      };
    }

    const data = await response.json();
    return { data, error: null };
  },
};

// ============================================================================
// Export default client
// ============================================================================

export { supabase };
export default supabase;
