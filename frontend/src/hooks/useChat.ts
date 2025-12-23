/**
 * useChat Hook
 * 
 * Chat state management with SSE streaming support.
 */

import { useState, useCallback, useRef } from 'react';
import type { CollegeRecommendation } from '../types/api';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  recommendations?: CollegeRecommendation[];
  sources?: Array<{ title: string; url: string }>;
  timestamp: Date;
}

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  error: string | null;
}

interface UseChatReturn extends ChatState {
  sendMessage: (
    query: string,
    profile: { nationality: string; gpa: number; major: string },
    options?: { mode: 'text' | 'card' }
  ) => Promise<void>;
  clearMessages: () => void;
  clearError: () => void;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function useChat(): UseChatReturn {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isStreaming: false,
    error: null,
  });
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (
    query: string,
    profile: { nationality: string; gpa: number; major: string },
    options: { mode: 'text' | 'card' } = { mode: 'text' }
  ) => {
    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: new Date(),
    };

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isStreaming: true,
      error: null,
    }));

    // Create assistant message placeholder
    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '', // Empty initially
      timestamp: new Date(),
    };

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, assistantMessage],
    }));

    try {
      // Abort any existing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      const endpoint = options.mode === 'card' 
        ? `${API_BASE}/api/recommend`
        : `${API_BASE}/api/recommend/stream`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': options.mode === 'card' ? 'application/json' : 'text/event-stream',
        },
        body: JSON.stringify({
          query,
          nationality: profile.nationality,
          gpa: profile.gpa,
          major: profile.major,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (options.mode === 'card') {
        // Handle JSON response
        const data = await response.json();
        
        setState(prev => ({
          ...prev,
          isStreaming: false,
          messages: prev.messages.map(msg =>
            msg.id === assistantMessage.id
              ? { 
                  ...msg, 
                  content: "Here are the recommended universities based on your profile:",
                  recommendations: data.recommendations,
                  sources: data.grounding_sources
                }
              : msg
          ),
        }));
      } else {
        // Handle Streaming response
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        let fullContent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.text) {
                  fullContent += data.text;
                  
                  // Update message content
                  setState(prev => ({
                    ...prev,
                    messages: prev.messages.map(msg =>
                      msg.id === assistantMessage.id
                        ? { ...msg, content: fullContent }
                        : msg
                    ),
                  }));
                }
                
                if (data.status === 'done') {
                  break;
                }
              } catch {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }
        setState(prev => ({ ...prev, isStreaming: false }));
      }
      
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        return;
      }
      
      setState(prev => ({
        ...prev,
        isStreaming: false,
        error: (error as Error).message,
        messages: prev.messages.filter(msg => msg.id !== assistantMessage.id),
      }));
    }
  }, []);

  const clearMessages = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setState({ messages: [], isStreaming: false, error: null });
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    sendMessage,
    clearMessages,
    clearError,
  };
}
