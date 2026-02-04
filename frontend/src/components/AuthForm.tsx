/**
 * AuthForm Component - Minimalist Design
 */

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../hooks/useAuth';
import { motion, AnimatePresence } from 'framer-motion';

export function AuthForm() {
    const { loading, error, signIn, signUp, clearError } = useAuth();
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        clearError();
        if (isLogin) await signIn(email, password);
        else await signUp(email, password);
    };

    const toggleMode = () => {
        setIsLogin(prev => !prev);
        clearError();
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-zinc-950">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="glass-card w-full max-w-md p-12 relative overflow-hidden"
            >
                {/* Ambient Glow */}
                <div className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] bg-[radial-gradient(circle,rgba(255,255,255,0.03)_0%,transparent_50%)] pointer-events-none" />

                <div className="relative z-10">
                    <h1 className="text-3xl font-bold mb-2 tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                        College List AI
                    </h1>
                    <p className="text-zinc-400 mb-10 text-sm">
                        {isLogin ? 'Welcome back.' : 'Your future starts here.'}
                    </p>

                    <form
                        onSubmit={handleSubmit}
                        className="flex flex-col gap-5"
                    >
                        <div>
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="Email"
                                required
                                disabled={loading}
                                className="glass-input"
                            />
                        </div>

                        <div>
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="Password"
                                required
                                minLength={6}
                                disabled={loading}
                                className="glass-input"
                            />
                        </div>

                        <AnimatePresence>
                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="text-red-400 text-sm"
                                >
                                    {error.message}
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <motion.button
                            type="submit"
                            disabled={loading}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="mt-2 w-full py-3 px-4 bg-zinc-100 text-zinc-950 rounded-lg text-base font-semibold transition-all hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading
                                ? 'Processing...'
                                : isLogin
                                  ? 'Sign In'
                                  : 'Create Account'}
                        </motion.button>
                    </form>

                    <div className="mt-8 text-center">
                        <button
                            onClick={toggleMode}
                            className="bg-none border-none text-zinc-400 text-sm cursor-pointer font-sans hover:text-zinc-200 transition-colors"
                        >
                            {isLogin ? 'No account? ' : 'Have an account? '}
                            <span className="text-zinc-100 underline decoration-zinc-600 underline-offset-4">
                                {isLogin ? 'Sign up' : 'Sign in'}
                            </span>
                        </button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
