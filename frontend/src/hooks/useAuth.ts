/**
 * useAuth Hook
 *
 * Supabase authentication wrapper with session management.
 */

import { useState, useEffect, useCallback } from 'react';
import type { User, Session, AuthError } from '@supabase/supabase-js';
import { supabase } from '../services/supabase';

interface AuthState {
    user: User | null;
    session: Session | null;
    loading: boolean;
    error: AuthError | null;
}

interface UseAuthReturn extends AuthState {
    signIn: (email: string, password: string) => Promise<void>;
    signUp: (email: string, password: string) => Promise<void>;
    signOut: () => Promise<void>;
    clearError: () => void;
}

export function useAuth(): UseAuthReturn {
    const [state, setState] = useState<AuthState>({
        user: null,
        session: null,
        loading: true,
        error: null
    });

    useEffect(() => {
        // Get initial session
        supabase.auth.getSession().then(({ data: { session } }) => {
            setState(prev => ({
                ...prev,
                user: session?.user ?? null,
                session,
                loading: false
            }));
        });

        // Listen for auth changes
        const {
            data: { subscription }
        } = supabase.auth.onAuthStateChange((_event, session) => {
            setState(prev => ({
                ...prev,
                user: session?.user ?? null,
                session,
                loading: false
            }));
        });

        return () => subscription.unsubscribe();
    }, []);

    const signIn = useCallback(async (email: string, password: string) => {
        setState(prev => ({ ...prev, error: null }));

        const { error } = await supabase.auth.signInWithPassword({
            email,
            password
        });

        if (error) {
            setState(prev => ({ ...prev, error }));
        }
    }, []);

    const signUp = useCallback(async (email: string, password: string) => {
        setState(prev => ({ ...prev, error: null }));

        const { error, data } = await supabase.auth.signUp({
            email,
            password
        });

        if (error) {
            setState(prev => ({ ...prev, error }));
        } else if (data.user && !data.session) {
            // Email confirmation required
            setState(prev => ({
                ...prev,
                error: {
                    message: 'Check your email to confirm your account',
                    name: 'info'
                } as any
            }));
        }
    }, []);

    const signOut = useCallback(async () => {
        const { error } = await supabase.auth.signOut();

        if (error) {
            setState(prev => ({ ...prev, error }));
        }
    }, []);

    const clearError = useCallback(() => {
        setState(prev => ({ ...prev, error: null }));
    }, []);

    return {
        ...state,
        signIn,
        signUp,
        signOut,
        clearError
    };
}
