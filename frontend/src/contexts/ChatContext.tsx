/**
 * ChatContext - Centralized chat state management
 * 
 * SOLID: Provides chat state to both Sidebar and Chat via context.
 */

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { supabase } from '../services/supabase';
import { trackSearch } from '../services/analyticsApi';
import type { CollegeRecommendation } from '../types/api';

// Types
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  recommendations?: CollegeRecommendation[];
  sources?: Array<{ title: string; url: string }>;
  timestamp: Date;
}

export interface ChatThread {
  id: string;
  title: string | null;
  createdAt: string;
  updatedAt: string;
}

interface ChatContextValue {
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
  threadId: string | null;
  threads: ChatThread[];
  isLoadingThreads: boolean;
  isLoadingMessages: boolean;
  sendMessage: (query: string, profile: ProfileData) => Promise<void>;
  loadThreads: () => Promise<void>;
  loadThread: (threadId: string) => Promise<void>;
  createThread: () => Promise<string | null>;
  deleteThread: (threadId: string) => Promise<void>;
  newChat: () => void;
  clearError: () => void;
}

interface ProfileData {
  citizenshipStatus?: string;
  nationality?: string;
  gpa: number;
  major: string;
  satScore?: number;
  actScore?: number;
  stateOfResidence?: string;
  householdIncomeTier?: string;
  englishProficiencyScore?: number;
  englishTestType?: string;
  campusVibe?: string;
  isStudentAthlete?: boolean;
  hasLegacyStatus?: boolean;
  legacyUniversities?: string[];
  postGradGoal?: string;
  isFirstGen?: boolean;
  apClassCount?: number;
  apClasses?: string[];
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChatContext must be used within ChatProvider');
  return ctx;
}

interface ChatProviderProps {
  children: ReactNode;
}

export function ChatProvider({ children }: ChatProviderProps) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const getAuthHeaders = useCallback(async (): Promise<HeadersInit> => {
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      return { 'Authorization': `Bearer ${user.id}`, 'Content-Type': 'application/json' };
    }
    return { 'Content-Type': 'application/json' };
  }, []);

  const loadThreads = useCallback(async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    setIsLoadingThreads(true);
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/api/chats`, { headers });
      if (response.ok) {
        const data = await response.json();
        setThreads(data.threads.map((t: { id: string; title: string | null; created_at: string; updated_at: string }) => ({
          id: t.id, title: t.title, createdAt: t.created_at, updatedAt: t.updated_at,
        })));
      }
    } catch (e) {
      console.error('Failed to load threads:', e);
    } finally {
      setIsLoadingThreads(false);
    }
  }, [getAuthHeaders]);

  const loadThread = useCallback(async (id: string) => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    setIsLoadingMessages(true);
    setThreadId(id);
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/api/chats/${id}/messages`, { headers });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages.map((m: { id: string; role: string; content: string; sources: Array<{ title: string; url: string }> | null; created_at: string }) => ({
          id: m.id, role: m.role as 'user' | 'assistant', content: m.content, sources: m.sources, timestamp: new Date(m.created_at),
        })));
      }
    } catch (e) {
      console.error('Failed to load messages:', e);
    } finally {
      setIsLoadingMessages(false);
    }
  }, [getAuthHeaders]);

  const createThread = useCallback(async (): Promise<string | null> => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      setError('Please sign in to create a chat thread.');
      return null;
    }

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/api/chats`, { method: 'POST', headers, body: JSON.stringify({}) });
      if (response.ok) {
        const data = await response.json();
        setThreadId(data.id);
        setMessages([]);
        setError(null);
        await loadThreads();
        return data.id;
      } else {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.detail || 'Failed to create chat thread.');
      }
    } catch (e) {
      console.error('Failed to create thread:', e);
      setError('Failed to create chat thread.');
    }
    return null;
  }, [getAuthHeaders, loadThreads]);

  const deleteThread = useCallback(async (id: string) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/api/chats/${id}`, { method: 'DELETE', headers });
      if (response.ok) {
        setThreads(prev => prev.filter(t => t.id !== id));
        if (threadId === id) { setThreadId(null); setMessages([]); }
      }
    } catch (e) {
      console.error('Failed to delete thread:', e);
    }
  }, [getAuthHeaders, threadId]);

  const saveMessage = useCallback(async (id: string, role: 'user' | 'assistant', content: string, sources?: Array<{ title: string; url: string }>) => {
    try {
      const headers = await getAuthHeaders();
      await fetch(`${API_BASE}/api/chats/${id}/messages`, { method: 'POST', headers, body: JSON.stringify({ role, content, sources }) });
    } catch (e) {
      console.error('Failed to save message:', e);
    }
  }, [getAuthHeaders]);

  const sendMessage = useCallback(async (query: string, profile: ProfileData) => {
    let currentThreadId = threadId;
    if (!currentThreadId) {
      currentThreadId = await createThread();
      if (!currentThreadId) return;
    }

    const userMessage: Message = { id: crypto.randomUUID(), role: 'user', content: query, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setIsStreaming(true);
    setError(null);
    saveMessage(currentThreadId, 'user', query);

    const assistantMessage: Message = { id: crypto.randomUUID(), role: 'assistant', content: '', timestamp: new Date() };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Build conversation history for context (last 6 messages, excluding the one we just added)
      const conversationHistory = messages.map(m => ({ 
        role: m.role, 
        content: m.content 
      }));

      const requestBody = {
        query,
        citizenship_status: profile.citizenshipStatus || 'INTERNATIONAL',
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
        is_student_athlete: profile.isStudentAthlete,
        has_legacy_status: profile.hasLegacyStatus,
        legacy_universities: profile.legacyUniversities,
        post_grad_goal: profile.postGradGoal,
        is_first_gen: profile.isFirstGen,
        ap_class_count: profile.apClassCount,
        ap_classes: profile.apClasses,
        thread_id: currentThreadId,
        conversation_history: conversationHistory,  // For LLM context
      };

      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE}/api/recommend/stream`, {
        method: 'POST',
        headers: { ...headers, 'Accept': 'text/event-stream' },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error('No response body');

      let fullContent = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.text) {
                fullContent += data.text;
                setMessages(prev => prev.map(m => m.id === assistantMessage.id ? { ...m, content: fullContent } : m));
              }
              if (data.status === 'done') break;
            } catch { /* ignore */ }
          }
        }
      }

      if (fullContent) await saveMessage(currentThreadId, 'assistant', fullContent);
      await loadThreads();
      
      // Fire-and-forget analytics tracking
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        trackSearch(user.id, query, 1, profile.major);
      }
    } catch (e) {
      setError((e as Error).message);
      setMessages(prev => prev.filter(m => m.id !== assistantMessage.id));
    } finally {
      setIsStreaming(false);
    }
  }, [threadId, createThread, saveMessage, loadThreads]);

  const newChat = useCallback(() => {
    setThreadId(null);
    setMessages([]);
    setError(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  useEffect(() => { loadThreads(); }, [loadThreads]);

  return (
    <ChatContext.Provider value={{
      messages, isStreaming, error, threadId, threads, isLoadingThreads, isLoadingMessages,
      sendMessage, loadThreads, loadThread, createThread, deleteThread, newChat, clearError,
    }}>
      {children}
    </ChatContext.Provider>
  );
}
