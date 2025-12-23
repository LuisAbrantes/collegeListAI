/**
 * Layout Component
 * 
 * Main application layout with sidebar and content area.
 */

import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import type { UserProfile } from '../types/api';

interface LayoutProps {
  userProfile: UserProfile;
  onSignOut: () => void;
}

export function Layout({ userProfile, onSignOut }: LayoutProps) {
  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      <Sidebar userProfile={userProfile} onSignOut={onSignOut} />
      
      <main className="flex-1 flex flex-col h-full relative overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
