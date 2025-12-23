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
import { ArrowUp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatProps {
  profile: UserProfile;
}

export function Chat({ profile }: ChatProps) {
  const { messages, isStreaming, error, sendMessage } = useChat();
  const [input, setInput] = useState('');
  const [viewMode, setViewMode] = useState<'text' | 'card'>('text');
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
    }, { mode: viewMode });
    
    setInput('');
  };

  return (
    <div className="h-full flex flex-col relative">
      
      {/* Top Bar (View Mode Toggle) */}
      <div className="flex justify-end p-4 absolute top-0 right-0 z-20">
          <div className="flex bg-zinc-900 rounded-lg p-1 border border-white/10">
            <button
              onClick={() => setViewMode('text')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
                viewMode === 'text' 
                  ? 'bg-zinc-800 text-white shadow-sm' 
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setViewMode('card')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer ${
                viewMode === 'card' 
                  ? 'bg-zinc-800 text-white shadow-sm' 
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              Cards
            </button>
          </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 flex flex-col">
        <div className="max-w-3xl w-full mx-auto pb-4">
          
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
               <span className="font-mono text-xs text-zinc-400 animate-pulse">
                 {viewMode === 'card' ? 'Finding best matches...' : 'Thinking...'}
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
      <div className="p-6 bg-zinc-950 z-20">
        <form 
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto relative"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about universities, majors, or financial aid..."
            className="glass-input w-full py-4 px-5 pr-14 rounded-3xl text-sm shadow-2xl bg-zinc-900 border border-white/10 text-white placeholder:text-zinc-400 focus:outline-none focus:border-white/20 focus:ring-1 focus:ring-white/20 transition-all"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className={`absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full flex items-center justify-center transition-all border-none ${
              input.trim() ? 'bg-white text-black cursor-pointer hover:scale-105' : 'bg-white/10 text-zinc-500 cursor-default'
            }`}
          >
            <ArrowUp size={18} />
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
      <div className={`${isUser ? 'max-w-[85%]' : 'max-w-[95%]'} ${
        isUser 
          ? 'py-3 px-5 bg-white/10 rounded-2xl text-zinc-100' 
          : 'p-0 text-zinc-100'
      }`}>
        {!isUser && (
           <span className="block text-xs text-zinc-500 mb-3 font-mono uppercase tracking-wider">
             AI ADVISOR
           </span>
        )}
        
        
        {/* Render message content */}
        {isUser ? (
          <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none
            prose-headings:text-zinc-100 prose-headings:font-bold prose-headings:mt-6 prose-headings:mb-3
            prose-p:text-zinc-300 prose-p:my-3 prose-p:leading-relaxed
            prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
            prose-strong:text-white prose-strong:font-semibold
            prose-code:text-zinc-300 prose-code:bg-white/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm
            prose-pre:bg-white/5 prose-pre:border prose-pre:border-white/10 prose-pre:p-4 prose-pre:my-4
            prose-ul:text-zinc-300 prose-ul:my-4 prose-ul:space-y-2
            prose-ol:text-zinc-300 prose-ol:my-4 prose-ol:space-y-2
            prose-li:my-1.5 prose-li:leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

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
           <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
             {message.recommendations.map(college => (
               <CollegeCard key={college.id} {...college} />
             ))}
           </div>
        )}
      </div>
    </motion.div>
  );
}
