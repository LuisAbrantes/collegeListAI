/**
 * Sidebar Component
 * 
 * Vertical navigation with chat history and user profile.
 */

import { Link, useLocation } from 'react-router-dom';
import { MessageSquarePlus, User, LogOut, MessageSquare, Trash2, Clock, ListChecks } from 'lucide-react';
import type { UserProfile } from '../types/api';
import { useChatContext } from '../contexts/ChatContext';

interface SidebarProps {
  userProfile: UserProfile;
  onSignOut: () => void;
}

export function Sidebar({ userProfile, onSignOut }: SidebarProps) {
  const location = useLocation();
  const isActive = (path: string) => location.pathname === path;
  const isHome = location.pathname === '/';

  const { threads, threadId, isLoadingThreads, newChat, loadThread, deleteThread } = useChatContext();

  const formatRelativeTime = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <aside className="w-64 h-screen flex flex-col bg-zinc-950 border-r border-white/10 shrink-0">
      {/* App Header */}
      <div className="p-6">
        <h1 className="text-lg font-semibold text-white m-0">College List AI</h1>
      </div>

      {/* Navigation */}
      <nav className="px-3 space-y-1">
        <button
          onClick={newChat}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors bg-transparent border-none cursor-pointer text-left ${
            isActive('/') && !threadId ? 'bg-white/10 text-white font-medium' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <MessageSquarePlus size={18} />
          New Chat
        </button>
        <Link
          to="/my-list"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors no-underline ${
            isActive('/my-list') ? 'bg-white/10 text-white font-medium' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <ListChecks size={18} />
          My College List
        </Link>
        <Link
          to="/profile"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors no-underline ${
            isActive('/profile') ? 'bg-white/10 text-white font-medium' : 'text-zinc-400 hover:text-white hover:bg-white/5'
          }`}
        >
          <User size={18} />
          My Profile
        </Link>
      </nav>

      {/* Chat History (only on home) */}
      {isHome && (
        <div className="flex-1 overflow-y-auto px-3 mt-4">
          <p className="text-xs text-zinc-600 uppercase tracking-wider px-3 mb-2">Recent Chats</p>
          
          {isLoadingThreads ? (
            <div className="px-3 py-4 text-center">
              <span className="text-zinc-500 text-xs animate-pulse">Loading...</span>
            </div>
          ) : threads.length === 0 ? (
            <div className="px-3 py-4 text-center">
              <p className="text-zinc-600 text-xs">No conversations yet</p>
            </div>
          ) : (
            <div className="space-y-1">
              {threads.map((thread) => (
                <div
                  key={thread.id}
                  className={`group relative rounded-lg transition-colors ${threadId === thread.id ? 'bg-white/10' : 'hover:bg-white/5'}`}
                >
                  <button
                    onClick={() => loadThread(thread.id)}
                    className="w-full p-2.5 text-left bg-transparent border-none cursor-pointer"
                  >
                    <div className="flex items-start gap-2">
                      <MessageSquare size={14} className={`mt-0.5 flex-shrink-0 ${threadId === thread.id ? 'text-white' : 'text-zinc-500'}`} />
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs truncate m-0 ${threadId === thread.id ? 'text-white' : 'text-zinc-300'}`}>
                          {thread.title || 'New conversation'}
                        </p>
                        <div className="flex items-center gap-1 mt-0.5">
                          <Clock size={8} className="text-zinc-600" />
                          <span className="text-[10px] text-zinc-600">{formatRelativeTime(thread.updatedAt)}</span>
                        </div>
                      </div>
                    </div>
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteThread(thread.id); }}
                    className="absolute right-1 top-1/2 -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded transition-all bg-transparent border-none cursor-pointer"
                    title="Delete chat"
                  >
                    <Trash2 size={12} className="text-zinc-500 hover:text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          )}
          
          {threads.length > 0 && (
            <p className="text-[10px] text-zinc-600 text-center px-3 mt-3">{threads.length}/5 conversations</p>
          )}
        </div>
      )}

      {!isHome && <div className="flex-1" />}

      {/* User Section */}
      <div className="p-4 border-t border-white/10">
        <div className="flex items-center gap-3 mb-4 px-2">
          <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center text-xs font-bold text-white">
            {(userProfile.nationality || 'US').slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="text-sm font-medium text-white truncate m-0">{userProfile.name || 'User'}</p>
            <p className="text-xs text-zinc-500 truncate m-0">GPA: {userProfile.gpa} • {userProfile.major}</p>
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
