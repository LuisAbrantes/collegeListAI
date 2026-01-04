/**
 * College List AI - Main App
 * 
 * Main application with auth flow:
 * 1. Not authenticated -> AuthForm
 * 2. No profile -> ProfileForm
 * 3. Has profile -> Chat
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { useProfile } from './hooks/useProfile';
import { ChatProvider } from './contexts/ChatContext';
import { AuthForm } from './components/AuthForm';
import { ProfileForm } from './components/ProfileForm';
import { Home } from './components/Home';
import { Chat } from './components/Chat';
import { Profile } from './components/Profile';
import { MyList } from './components/MyList';
import { Layout } from './components/Layout';

function App() {
  const { user, loading: authLoading, signOut } = useAuth();
  const { profile, loading: profileLoading, createProfile, error } = useProfile();

  // Show loading state
  if (authLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-zinc-950 text-zinc-100">
        <div className="w-10 h-10 border-4 border-zinc-800 border-t-zinc-100 rounded-full animate-spin" />
        <p className="text-sm font-medium animate-pulse">Loading...</p>
      </div>
    );
  }

  // Not authenticated -> show auth form
  if (!user) {
    return <AuthForm />;
  }

  // Loading profile
  if (profileLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-zinc-950 text-zinc-100">
        <div className="w-10 h-10 border-4 border-zinc-800 border-t-zinc-100 rounded-full animate-spin" />
        <p className="text-sm font-medium animate-pulse">Loading profile...</p>
      </div>
    );
  }

  // Authenticated but no profile -> show onboarding
  if (!profile) {
    return (
      <ProfileForm 
        onSubmit={createProfile}
        loading={profileLoading}
        error={error}
      />
    );
  }

  // Has profile -> show app with routing
  return (
    <ChatProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout userProfile={profile} onSignOut={signOut} />}>
            <Route path="/" element={<Home />} />
            <Route path="/chat" element={<Chat profile={profile} />} />
            <Route path="/profile" element={<Profile currentProfile={profile} />} />
            <Route path="/my-list" element={<MyList />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ChatProvider>
  );
}

export default App;
