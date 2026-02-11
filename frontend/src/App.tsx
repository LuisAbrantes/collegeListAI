/**
 * College List AI - Main App
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { useProfile } from './hooks/useProfile';
import { ChatProvider } from './contexts/ChatContext';
import { ProfileForm } from './components/ProfileForm';
import { Layout } from './components/Layout';
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Home } from './pages/Home';
import { Chat } from './pages/Chat';
import { Profile } from './pages/Profile';
import { MyList } from './pages/MyList';
import { Pricing } from './pages/Pricing';

function ProtectedRoutes() {
    const { user, loading: authLoading, signOut } = useAuth();
    const {
        profile,
        loading: profileLoading,
        createProfile,
        error
    } = useProfile();

    if (authLoading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-zinc-950 text-zinc-100">
                <div className="w-10 h-10 border-4 border-zinc-800 border-t-zinc-100 rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/app/login" replace />;
    }

    if (profileLoading) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-zinc-950 text-zinc-100">
                <div className="w-10 h-10 border-4 border-zinc-800 border-t-zinc-100 rounded-full animate-spin" />
            </div>
        );
    }

    if (!profile) {
        return (
            <ProfileForm
                onSubmit={createProfile}
                loading={profileLoading}
                error={error}
            />
        );
    }

    return (
        <ChatProvider>
            <Routes>
                <Route
                    element={
                        <Layout userProfile={profile} onSignOut={signOut} />
                    }
                >
                    <Route index element={<Home />} />
                    <Route path="chat" element={<Chat profile={profile} />} />
                    <Route
                        path="profile"
                        element={<Profile currentProfile={profile} />}
                    />
                    <Route path="my-list" element={<MyList />} />
                </Route>
                <Route path="*" element={<Navigate to="/app" replace />} />
            </Routes>
        </ChatProvider>
    );
}

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
            <Route path="/" element={<Landing />} />
                <Route path="/pricing" element={<Pricing />} />
                <Route path="/app/login" element={<Login />} />
                <Route path="/app/*" element={<ProtectedRoutes />} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    );
}
