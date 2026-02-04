/**
 * Chat Component - Message Bubbles & Input
 */

import { useState, useRef, useEffect } from 'react';
import type { FormEvent } from 'react';
import { useChatContext, type Message } from '../contexts/ChatContext';
import type { UserProfile } from '../types/api';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowUp } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatProps {
    profile: UserProfile;
}

export function Chat({ profile }: ChatProps) {
    const { messages, isStreaming, error, isLoadingMessages, sendMessage } =
        useChatContext();
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isStreaming]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        const query = input.trim();
        if (!query || isStreaming) return;

        // Clear input immediately to prevent double-submit
        setInput('');

        await sendMessage(query, {
            citizenshipStatus: profile.citizenshipStatus,
            nationality: profile.nationality || undefined,
            gpa: profile.gpa,
            major: profile.major,
            satScore: profile.satScore,
            actScore: profile.actScore,
            stateOfResidence: profile.stateOfResidence,
            householdIncomeTier: profile.householdIncomeTier,
            englishProficiencyScore: profile.englishProficiencyScore,
            englishTestType: profile.englishTestType,
            campusVibe: profile.campusVibe,
            isStudentAthlete: profile.isStudentAthlete,
            hasLegacyStatus: profile.hasLegacyStatus,
            legacyUniversities: profile.legacyUniversities,
            postGradGoal: profile.postGradGoal,
            isFirstGen: profile.isFirstGen,
            apClassCount: profile.apClassCount,
            apClasses: profile.apClasses
        });
    };

    return (
        <div className="h-full flex flex-col relative">
            {isLoadingMessages && (
                <div className="absolute inset-0 bg-zinc-950/80 flex items-center justify-center z-10">
                    <span className="text-zinc-400 animate-pulse">
                        Loading messages...
                    </span>
                </div>
            )}

            <div className="flex-1 overflow-y-auto px-4 flex flex-col">
                <div className="max-w-3xl w-full mx-auto pb-4">
                    <AnimatePresence>
                        {messages.length === 0 && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="text-center py-16 px-4"
                            >
                                <h2 className="text-2xl mb-2 text-zinc-200">
                                    Let's build your College List
                                </h2>
                                <p className="text-zinc-500 mb-8 max-w-md mx-auto">
                                    I'll help you find the perfect mix of Reach,
                                    Target, and Safety schools based on your
                                    academic profile and financial needs.
                                </p>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 w-full max-w-2xl px-4">
                                    {[
                                        {
                                            title: 'Strategic List',
                                            subtitle:
                                                'Get a balanced Reach / Target / Safety mix',
                                            prompt: 'Generate a strategic Reach, Target, and Safety college list for me'
                                        },
                                        {
                                            title: 'Hidden Gems',
                                            subtitle:
                                                'Discover underrated schools with great programs',
                                            prompt: 'Find "Hidden Gem" universities with strong programs in my major'
                                        },
                                        {
                                            title: 'Financial Deep Dive',
                                            subtitle:
                                                'Find high-aid schools & scholarships',
                                            prompt: 'Find schools with best financial aid and scholarships for my profile'
                                        }
                                    ].map(item => (
                                        <button
                                            key={item.title}
                                            onClick={() =>
                                                setInput(item.prompt)
                                            }
                                            className="flex flex-col items-start p-4 bg-white/5 border border-white/10 rounded-xl text-left cursor-pointer hover:bg-white/10 hover:border-white/20 hover:scale-[1.02] transition-all group shadow-sm"
                                        >
                                            <span className="text-zinc-200 font-medium text-sm mb-1 group-hover:text-white">
                                                {item.title}
                                            </span>
                                            <span className="text-zinc-500 text-xs">
                                                {item.subtitle}
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            </motion.div>
                        )}

                        {messages.map(message => (
                            <MessageItem key={message.id} message={message} />
                        ))}
                    </AnimatePresence>

                    {isStreaming && (
                        <div className="py-4">
                            <span className="font-mono text-xs text-zinc-400 animate-pulse">
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

            <div className="p-6 bg-zinc-950 z-20">
                <form
                    onSubmit={handleSubmit}
                    className="max-w-3xl mx-auto relative"
                >
                    <input
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        placeholder="Describe your ideal college (e.g., 'Urban campus with strong CS and financial aid')..."
                        className="glass-input w-full py-4 px-5 pr-14 rounded-3xl text-sm shadow-2xl bg-zinc-900 border border-white/10 text-white placeholder:text-zinc-400 focus:outline-none focus:border-white/20 focus:ring-1 focus:ring-white/20 transition-all"
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || isStreaming}
                        className={`absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full flex items-center justify-center transition-all border-none ${
                            input.trim()
                                ? 'bg-white text-black cursor-pointer hover:scale-105'
                                : 'bg-white/10 text-zinc-500 cursor-default'
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
            <div
                className={`${isUser ? 'max-w-[85%]' : 'max-w-[95%]'} ${
                    isUser
                        ? 'py-3 px-5 bg-white/10 rounded-2xl text-zinc-100'
                        : 'p-0 text-zinc-100'
                }`}
            >
                {!isUser && (
                    <span className="block text-xs text-zinc-500 mb-3 font-mono uppercase tracking-wider">
                        AI ADVISOR
                    </span>
                )}

                {isUser ? (
                    <div className="whitespace-pre-wrap leading-relaxed">
                        {message.content}
                    </div>
                ) : (
                    <div
                        className="prose prose-invert prose-sm max-w-none
            prose-headings:text-zinc-100 prose-headings:font-bold prose-headings:mt-6 prose-headings:mb-3
            prose-p:text-zinc-300 prose-p:my-3 prose-p:leading-relaxed
            prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
            prose-strong:text-white prose-strong:font-semibold
            prose-code:text-zinc-300 prose-code:bg-white/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm
            prose-pre:bg-white/5 prose-pre:border prose-pre:border-white/10 prose-pre:p-4 prose-pre:my-4
            prose-ul:text-zinc-300 prose-ul:my-4 prose-ul:space-y-2
            prose-ol:text-zinc-300 prose-ol:my-4 prose-ol:space-y-2
            prose-li:my-1.5 prose-li:leading-relaxed"
                    >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                        </ReactMarkdown>
                    </div>
                )}

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
            </div>
        </motion.div>
    );
}
