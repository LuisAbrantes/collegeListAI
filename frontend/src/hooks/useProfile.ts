/**
 * useProfile Hook
 * 
 * Profile CRUD operations using the Supabase client.
 */

import { useState, useEffect, useCallback } from 'react';
import { profileService } from '../services/supabase';
import type { UserProfile, UserProfileCreate, UserProfileUpdate } from '../types/api';

interface ProfileState {
  profile: UserProfile | null;
  loading: boolean;
  error: string | null;
}

interface UseProfileReturn extends ProfileState {
  createProfile: (data: UserProfileCreate) => Promise<boolean>;
  updateProfile: (data: UserProfileUpdate) => Promise<boolean>;
  refreshProfile: () => Promise<void>;
}

export function useProfile(): UseProfileReturn {
  const [state, setState] = useState<ProfileState>({
    profile: null,
    loading: true,
    error: null,
  });

  const fetchProfile = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    const { data, error } = await profileService.getProfile();
    
    if (error) {
      // Profile not found is expected for new users
      if (error.error === 'NOT_FOUND') {
        setState({ profile: null, loading: false, error: null });
      } else {
        setState({ profile: null, loading: false, error: error.message });
      }
    } else {
      setState({ profile: data, loading: false, error: null });
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const createProfile = useCallback(async (data: UserProfileCreate): Promise<boolean> => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    const { data: profile, error } = await profileService.createProfile(data);
    
    if (error) {
      setState(prev => ({ ...prev, loading: false, error: error.message }));
      return false;
    }
    
    setState({ profile, loading: false, error: null });
    return true;
  }, []);

  const updateProfile = useCallback(async (data: UserProfileUpdate): Promise<boolean> => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    const { data: profile, error } = await profileService.updateProfile(data);
    
    if (error) {
      setState(prev => ({ ...prev, loading: false, error: error.message }));
      return false;
    }
    
    setState({ profile, loading: false, error: null });
    return true;
  }, []);

  return {
    ...state,
    createProfile,
    updateProfile,
    refreshProfile: fetchProfile,
  };
}
