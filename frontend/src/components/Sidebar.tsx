/**
 * Sidebar Component
 * 
 * Vertical navigation menu with user profile and sign out.
 */

import { Link, useLocation } from 'react-router-dom';
import { MessageSquarePlus, User, LogOut } from 'lucide-react';
import type { UserProfile } from '../types/api';

interface SidebarProps {
  userProfile: UserProfile;
  onSignOut: () => void;
}

export function Sidebar({ userProfile, onSignOut }: SidebarProps) {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;

  return (
    <aside className="w-64 h-screen flex flex-col bg-zinc-950 border-r border-white/10 shrink-0">
      {/* App Header */}
      <div className="p-6">
        <h1 className="text-lg font-semibold text-white m-0">
          College List AI
        </h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-1">
        <Link
          to="/"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors no-underline ${
            isActive('/') 
              ? 'bg-white/10 text-white font-medium' 
              : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <MessageSquarePlus size={18} />
          New Chat
        </Link>
        <Link
          to="/profile"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors no-underline ${
            isActive('/profile') 
              ? 'bg-white/10 text-white font-medium' 
              : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <User size={18} />
          My Profile
        </Link>
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 mb-4 px-2">
          <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center text-xs font-bold text-white">
            {(userProfile.nationality || 'US').slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-sm font-medium text-white truncate m-0">
              User
            </p>
            <p className="text-xs text-zinc-500 truncate m-0">
              GPA: {userProfile.gpa} • {userProfile.major}
            </p>
          </div>
        </div>
        
        <button
          onClick={onSignOut}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors bg-transparent border-none cursor-pointer"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
