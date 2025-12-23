/**
 * Chat Component - Modern Message Bubbles & Floating Input
 */

import { useState, useRef, useEffect } from 'react';
import type { FormEvent } from 'react';
import { useChat } from '../hooks/useChat';
import type { Message } from '../hooks/useChat';
import type { UserProfile } from '../types/api';
import { CollegeCard } from './CollegeCard';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatProps {
  profile: UserProfile;
  onSignOut: () => void;
}

export function Chat({ profile, onSignOut }: ChatProps) {
  const { messages, isStreaming, error, sendMessage } = useChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    sendMessage(input.trim(), {
      nationality: profile.nationality,
      gpa: profile.gpa,
      major: profile.major,
    });
    
    setInput('');
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      
      {/* Navbar */}
      <header className="glass-card m-4 px-6 py-4 flex justify-between items-center rounded-xl z-10">
        <div className="flex items-center gap-4">
          <h1 className="text-base font-semibold m-0">College List AI</h1>
          <span className="text-xs font-mono text-zinc-400 pl-4 border-l border-white/10">
            {profile.major} • GPA {profile.gpa}
          </span>
        </div>
        <button 
          onClick={onSignOut} 
          className="bg-none border-none text-zinc-500 text-sm cursor-pointer hover:text-white transition-colors"
        >
          Sign out
        </button>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 flex flex-col">
        <div className="max-w-3xl w-full mx-auto pb-32">
          
          <AnimatePresence>
            {messages.length === 0 && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center py-16 px-4"
              >
                <h2 className="text-2xl mb-4 text-zinc-200">Ready to plan your future?</h2>
                <div className="flex gap-4 justify-center flex-wrap">
                  {['Reach schools for me', 'Good CS programs', 'Financial aid options'].map(text => (
                    <button
                      key={text}
                      onClick={() => setInput(text)}
                      className="px-4 py-2 bg-white/5 border border-white/10 rounded-full text-zinc-400 cursor-pointer text-sm hover:bg-white/10 hover:text-zinc-200 transition-all"
                    >
                      {text}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}
          </AnimatePresence>

          {isStreaming && (
            <div className="py-4">
               <span className="font-mono text-xs text-zinc-500 animate-pulse">
                 Thinking...
               </span>
            </div>
          )}

          {error && (
            <div className="p-4 text-red-400 bg-red-500/10 rounded-lg my-4 border border-red-500/20">
              Error: {error}
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="fixed bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-zinc-950 via-zinc-950/90 to-transparent z-20">
        <form 
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto relative"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about universities, majors, or financial aid..."
            className="glass-input w-full py-4 px-5 pr-14 rounded-3xl text-base shadow-2xl bg-zinc-900/90 border-white/10"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className={`absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full flex items-center justify-center transition-all ${
              input.trim() ? 'bg-white text-black cursor-pointer hover:scale-105' : 'bg-white/10 text-zinc-500 cursor-default'
            }`}
          >
            ↑
          </button>
        </form>
      </div>
    </div>
  );
}

function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`my-6 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
    >
      <div className={`max-w-[85%] ${
        isUser 
          ? 'py-3 px-5 bg-white/10 rounded-2xl text-zinc-100' 
          : 'p-0 text-zinc-100'
      }`}>
        {!isUser && (
           <span className="block text-xs text-zinc-500 mb-2 font-mono uppercase tracking-wider">
             AI ADVISOR
           </span>
        )}
        
        {/* Render clean text */}
        <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-4 flex gap-2 flex-wrap">
            {message.sources.map((source, i) => (
              <a 
                key={i} 
                href={source.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-[0.65rem] text-zinc-400 no-underline bg-white/5 py-1 px-3 rounded-xl border border-white/5 flex items-center gap-1 hover:bg-white/10 hover:text-zinc-200 transition-colors"
              >
                🔗 {source.title.slice(0, 20)}...
              </a>
            ))}
          </div>
        )}
        
        {/* Recommendations Grid */}
        {!isUser && message.recommendations && message.recommendations.length > 0 && (
           <div className="mt-6">
             {message.recommendations.map(college => (
               <CollegeCard key={college.id} {...college} />
             ))}
           </div>
        )}
      </div>
    </motion.div>
  );
}
