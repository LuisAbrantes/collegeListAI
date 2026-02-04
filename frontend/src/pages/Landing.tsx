/**
 * Landing Page Placeholder
 *
 * Public entry point. Replace with real marketing content later.
 */

import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight } from 'lucide-react';

export function Landing() {
    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col">
            {/* Header */}
            <header className="flex items-center justify-between px-8 py-6">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-6 h-6 text-zinc-400" />
                    <span className="font-semibold text-lg">
                        College List AI
                    </span>
                </div>
                <Link
                    to="/app"
                    className="px-4 py-2 text-sm font-medium text-zinc-300 hover:text-white transition-colors"
                >
                    Sign In
                </Link>
            </header>

            {/* Hero */}
            <main className="flex-1 flex items-center justify-center p-8">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="text-center max-w-2xl"
                >
                    <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                        Build Your College List
                        <br />
                        <span className="text-zinc-500">with AI Guidance</span>
                    </h1>
                    <p className="text-zinc-400 mt-6 text-lg leading-relaxed">
                        Personalized university recommendations based on your
                        academic profile, financial needs, and preferences. Find
                        your perfect fit.
                    </p>

                    <div className="mt-10 flex items-center justify-center gap-4">
                        <Link
                            to="/app"
                            className="inline-flex items-center gap-2 px-6 py-3 bg-zinc-100 text-zinc-950 rounded-lg font-semibold hover:bg-white transition-colors"
                        >
                            Get Started
                            <ArrowRight className="w-4 h-4" />
                        </Link>
                    </div>
                </motion.div>
            </main>

            {/* Footer */}
            <footer className="px-8 py-6 text-center text-zinc-600 text-sm">
                © 2026 College List AI
            </footer>
        </div>
    );
}
