/**
 * Login Page
 */

import { Navigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { AuthForm } from '../components/AuthForm';

export function Login() {
    const { user, loading } = useAuth();
    const [searchParams] = useSearchParams();
    const returnTo = searchParams.get('returnTo') || '/app';

    // Show loading while checking auth
    if (loading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-zinc-950 text-zinc-100">
                <div className="w-10 h-10 border-4 border-zinc-800 border-t-zinc-100 rounded-full animate-spin" />
            </div>
        );
    }

    // Already logged in -> redirect to intended destination
    if (user) {
        return <Navigate to={returnTo} replace />;
    }

    return <AuthForm returnTo={returnTo} />;
}

