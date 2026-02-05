/**
 * Landing Page - College List AI
 *
 * Modern, minimalist landing page showcasing the AI-powered
 * college list advisor for international students.
 */

import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    Search,
    Target,
    Shield,
    TrendingUp,
    Globe,
    Sparkles,
    Brain,
    DollarSign,
    ArrowRight,
    CheckCircle,
    MessageSquare,
    ListChecks,
    Clock,
    Settings
} from 'lucide-react';

export function Landing() {
    const fadeInUp = {
        initial: { opacity: 0, y: 30 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] }
    };

    const stagger = {
        animate: {
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    const features = [
        {
            icon: Brain,
            title: 'AI-Powered Recommendations',
            description:
                'Get personalized college suggestions based on your GPA, test scores, major, and preferences using advanced AI.',
            color: 'text-purple-400'
        },
        {
            icon: Target,
            title: 'Reach / Target / Safety',
            description:
                'Every school is categorized based on your admission probability, helping you build a balanced list.',
            color: 'text-target'
        },
        {
            icon: Globe,
            title: 'Domestic & International Support',
            description:
                'Full support for both domestic and international students with nationality-aware financial aid insights.',
            color: 'text-cyan-400'
        },
        {
            icon: DollarSign,
            title: 'Financial Aid Insights',
            description:
                'Discover merit scholarships, need-based aid, and schools with the best financial support for your situation.',
            color: 'text-safety'
        },
        {
            icon: Search,
            title: 'Real-Time Data',
            description:
                'Access up-to-date 2025-2026 deadlines, acceptance rates, and program-specific information.',
            color: 'text-reach'
        },
        {
            icon: ListChecks,
            title: 'Smart College List',
            description:
                'Save schools, track applications, and manage your entire college journey in one place.',
            color: 'text-emerald-400'
        }
    ];

    const howItWorks = [
        {
            step: '01',
            title: 'Create Your Profile',
            description:
                'Enter your GPA, test scores, nationality, intended major, and financial situation.'
        },
        {
            step: '02',
            title: 'Chat with AI Advisor',
            description:
                'Ask for recommendations, explore schools, and get personalized advice through natural conversation.'
        },
        {
            step: '03',
            title: 'Build Your List',
            description:
                'Save schools to your college list with reach, target, and safety categorization.'
        }
    ];

    const stats = [
        { value: '3,000+', label: 'Universities' },
        { value: 'Real-Time', label: 'Data Updates' },
        { value: '50+', label: 'Countries Supported' },
        { value: 'Free', label: 'To Get Started' }
    ];

    // Why College List AI - Differentiation points
    const whyPoints = [
        {
            icon: Clock,
            title: 'Save Time',
            description: 'Stop spending weeks on random rankings and Reddit threads.'
        },
        {
            icon: DollarSign,
            title: 'See Costs Upfront',
            description: "See cost and financial aid friendliness upfront, not after you fall in love with a school."
        },
        {
            icon: Target,
            title: 'Clear Categories',
            description: 'Reach / Target / Safety labels tailored to your GPA, scores, and major.'
        },
        {
            icon: Settings,
            title: 'You Stay in Control',
            description: 'AI suggests, you decide. Build a list that fits your goals.'
        }
    ];

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans overflow-x-hidden">
            {/* Background Effects */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-purple-500/5 rounded-full blur-[120px]" />
                <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[120px]" />
            </div>

            {/* Navigation */}
            <nav className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-zinc-950/80 border-b border-white/5">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Link
                        to="/"
                        className="flex items-center gap-2 text-white no-underline"
                    >
                        <img src="https://em-content.zobj.net/source/apple/391/graduation-cap_1f393.png" alt="🎓" className="w-7 h-7" />
                        <span className="text-lg font-semibold tracking-tight">
                            College List AI
                        </span>
                    </Link>

                    <div className="flex items-center gap-4">
                        <Link
                            to="/app/login"
                            className="text-zinc-400 hover:text-white transition-colors no-underline text-sm"
                        >
                            Sign In
                        </Link>
                        <Link
                            to="/app/login"
                            className="btn-primary text-sm no-underline"
                        >
                            Get Started
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="relative pt-32 pb-20 px-6">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                        className="text-center max-w-4xl mx-auto"
                    >
                        {/* Badge */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.2 }}
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-sm text-zinc-400 mb-8"
                        >
                            <Sparkles className="w-4 h-4 text-gray-500" />
                            <span>AI-Powered College Advisor</span>
                        </motion.div>

                        <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-[1.1] tracking-tight">
                            <span className="bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
                                Build a Smart
                            </span>
                            <br />
                            <span className="bg-gradient-to-r from-zinc-300 via-zinc-400 to-zinc-500 bg-clip-text text-transparent">
                                College List
                            </span>
                        </h1>

                        <p className="text-xl text-zinc-400 mb-4 max-w-2xl mx-auto leading-relaxed">
                            Get real admission odds and cost estimates for U.S. colleges.
                            Use AI to find reach, target, and safety schools that match
                            your profile, budget, and major.
                        </p>

                        {/* For Who positioning */}
                        <p className="text-sm text-zinc-500 mb-10 max-w-xl mx-auto">
                            Designed for high school students, gap-year applicants, and transfers
                            applying to U.S. colleges – from any country.
                        </p>

                        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                            <Link
                                to="/app/login"
                                className="group flex items-center gap-2 px-8 py-4 bg-white text-zinc-950 rounded-xl font-semibold text-lg hover:bg-zinc-100 transition-all no-underline hover:scale-[1.02]"
                            >
                                Get Your College List (Free)
                                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                            </Link>
                            <a
                                href="#how-it-works"
                                className="flex items-center gap-2 px-8 py-4 text-zinc-400 hover:text-white transition-colors no-underline"
                            >
                                See How It Works
                            </a>
                        </div>
                    </motion.div>

                    {/* Hero Visual - Labels Preview */}
                    <motion.div
                        initial={{ opacity: 0, y: 60 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4, duration: 0.8 }}
                        className="mt-20 max-w-4xl mx-auto"
                    >
                        <div className="glass-card p-8 relative overflow-hidden">
                            {/* Ambient glow */}
                            <div className="absolute -top-20 -right-20 w-60 h-60 bg-target/20 rounded-full blur-[80px]" />
                            <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-reach/20 rounded-full blur-[80px]" />

                            <div className="relative">
                                <div className="flex items-center gap-3 mb-6">
                                    <MessageSquare className="w-5 h-5 text-zinc-500" />
                                    <span className="text-sm text-zinc-500">
                                        Sample Conversation
                                    </span>
                                </div>

                                <div className="space-y-4">
                                    <div className="flex justify-end">
                                        <div className="bg-white/10 rounded-2xl rounded-br-md px-4 py-3 max-w-md">
                                            <p className="text-sm text-zinc-200">
                                                Give me 5 target schools for
                                                Computer Science where my total
                                                cost is likely under $30k/year
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex justify-start">
                                        <div className="bg-zinc-800/50 rounded-2xl rounded-bl-md px-4 py-3 max-w-lg">
                                            <p className="text-sm text-zinc-300 mb-3">
                                                Based on your profile, here are
                                                target schools with strong CS programs
                                                within your budget:
                                            </p>

                                            {/* College Cards Preview */}
                                            <div className="space-y-2">
                                                {[
                                                    {
                                                        name: 'University of Michigan',
                                                        label: 'Target',
                                                        color: 'border-target text-target',
                                                        aid: 'Est. $26-30k/yr after aid'
                                                    },
                                                    {
                                                        name: 'Georgia Tech',
                                                        label: 'Target',
                                                        color: 'border-target text-target',
                                                        aid: 'Strong merit scholarships'
                                                    },
                                                    {
                                                        name: 'UT Austin',
                                                        label: 'Target',
                                                        color: 'border-target text-target',
                                                        aid: 'Est. $22-28k/yr for residents'
                                                    }
                                                ].map((school, i) => (
                                                    <motion.div
                                                        key={school.name}
                                                        initial={{
                                                            opacity: 0,
                                                            x: -20
                                                        }}
                                                        animate={{
                                                            opacity: 1,
                                                            x: 0
                                                        }}
                                                        transition={{
                                                            delay: 0.8 + i * 0.1
                                                        }}
                                                        className={`flex flex-col gap-1 p-3 bg-zinc-900/50 rounded-lg border-l-2 ${school.color.split(' ')[0]}`}
                                                    >
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-sm text-zinc-200">
                                                                {school.name}
                                                            </span>
                                                            <span
                                                                className={`text-[0.6rem] uppercase tracking-wider px-2 py-0.5 rounded border border-current font-mono ${school.color.split(' ')[1]}`}
                                                            >
                                                                {school.label}
                                                            </span>
                                                        </div>
                                                        <span className="text-xs text-zinc-500">
                                                            {school.aid}
                                                        </span>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Stats Section */}
            <section className="py-16 px-6 border-y border-white/5">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial="initial"
                        whileInView="animate"
                        viewport={{ once: true }}
                        variants={stagger}
                        className="grid grid-cols-2 md:grid-cols-4 gap-8"
                    >
                        {stats.map(stat => (
                            <motion.div
                                key={stat.label}
                                variants={fadeInUp}
                                className="text-center"
                            >
                                <div className="text-3xl md:text-4xl font-bold text-white mb-2">
                                    {stat.value}
                                </div>
                                <div className="text-sm text-zinc-500">
                                    {stat.label}
                                </div>
                            </motion.div>
                        ))}
                    </motion.div>
                </div>
            </section>

            {/* Dream Schools / University Logos Section */}
            <section className="py-16 px-6">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-10"
                    >
                        <h3 className="text-xl md:text-2xl font-semibold text-white mb-3">
                            Your Dream School Is Within Reach
                        </h3>
                        <p className="text-base text-zinc-400 max-w-xl mx-auto">
                            Every year, students just like you get accepted to these schools. 
                            We help you find where you truly belong — and build a list that gets you there.
                        </p>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="flex flex-wrap justify-center items-center gap-8 md:gap-12"
                    >
                        {[
                            {
                                name: 'Massachusetts Institute of Technology',
                                logo: 'https://download.logo.wine/logo/Massachusetts_Institute_of_Technology/Massachusetts_Institute_of_Technology-Logo.wine.png'
                            },
                            {
                                name: 'Stanford University',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/b/b5/Seal_of_Leland_Stanford_Junior_University.svg'
                            },
                            {
                                name: 'Harvard University',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/c/cc/Harvard_University_coat_of_arms.svg'
                            },
                            {
                                name: 'UC Berkeley',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/a/a1/Seal_of_University_of_California%2C_Berkeley.svg'
                            },
                            {
                                name: 'Carnegie Mellon University',
                                logo: 'https://www.drupal.org/files/styles/grid-4-2x/public/CMU_Logo_Stack_Red.png?itok=z-anp9I_'
                            },
                            {
                                name: 'Georgia Tech',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/6/6c/Georgia_Tech_seal.svg'
                            },
                            {
                                name: 'UCLA',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/e/ef/UCLA_Bruins_logo.svg'
                            },
                            {
                                name: 'New York University',
                                logo: 'https://1000logos.net/wp-content/uploads/2022/08/NYU-Logo.png'
                            },
                            {
                                name: 'UT Austin',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/8/8d/Texas_Longhorns_logo.svg'
                            },
                            {
                                name: 'Notre Dame',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/f/f5/Notre_Dame_Fighting_Irish_logo.svg'
                            },
                            {
                                name: 'University of Michigan',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/3/36/Michigan_Wolverines_Block_M.png'
                            },
                            {
                                name: 'University of Miami',
                                logo: 'https://images.seeklogo.com/logo-png/21/2/university-of-miami-logo-png_seeklogo-211487.png'
                            },
                            {
                                name: 'Brandeis University',
                                logo: 'https://upload.wikimedia.org/wikipedia/en/3/32/Brandeis_University_seal.svg'
                            },
                            {
                                name: 'Columbia University',
                                logo: 'https://pluspng.com/img-png/columbia-university-logo-png--1200.png'
                            },
                            {
                                name: 'Duke University',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Duke_University_logo.svg/200px-Duke_University_logo.svg.png'
                            },
                            {
                                name: 'Northwestern University',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Northwestern_University_seal.svg/250px-Northwestern_University_seal.svg.png'
                            },
                            {
                                name: 'USC',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/USC_Trojans_logo.svg/960px-USC_Trojans_logo.svg.png'
                            },
                            {
                                name: 'Boston University',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Boston_University_wordmark.svg/200px-Boston_University_wordmark.svg.png'
                            },
                            {
                                name: 'Yale University',
                                logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Yale_University_Shield_1.svg/800px-Yale_University_Shield_1.svg.png'
                            },
                            {
                                name: 'Dartmouth College',
                                logo: 'https://upload.wikimedia.org/wikipedia/en/e/e4/Dartmouth_College_shield.svg'
                            }
                        ].map((school, index) => (
                            <motion.div
                                key={school.name}
                                initial={{ opacity: 0, scale: 0.8 }}
                                whileInView={{ opacity: 1, scale: 1 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.1 + index * 0.05 }}
                                whileHover={{ scale: 1.15 }}
                                className="w-16 h-16 md:w-20 md:h-20 flex items-center justify-center cursor-default transition-all opacity-80 hover:opacity-100 hover:scale-1.15"
                                title={school.name}
                            >
                                <img 
                                    src={school.logo} 
                                    alt={school.name}
                                    className="w-full h-full object-contain"
                                />
                            </motion.div>
                        ))}
                    </motion.div>

                    {/* Data credibility note */}
                    <motion.p
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.5 }}
                        className="text-center text-xs text-zinc-600 mt-8"
                    >
                        Powered by data from IPEDS, College Scorecard, and official university reports.
                    </motion.p>
                </div>
            </section>

            {/* Features Section */}
            <section className="py-24 px-6">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-16"
                    >
                        <h2 className="text-4xl font-bold mb-4">
                            Everything You Need
                        </h2>
                        <p className="text-zinc-400 max-w-2xl mx-auto">
                            Get comprehensive college advising with AI. Support
                            for both domestic and international students, with
                            specialized features for each.
                        </p>
                    </motion.div>

                    <motion.div
                        initial="initial"
                        whileInView="animate"
                        viewport={{ once: true }}
                        variants={stagger}
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                    >
                        {features.map(feature => (
                            <motion.div
                                key={feature.title}
                                variants={fadeInUp}
                                className="glass-card p-6 hover:bg-zinc-800/30 transition-colors group"
                            >
                                <feature.icon
                                    className={`w-10 h-10 ${feature.color} mb-4 group-hover:scale-110 transition-transform`}
                                />
                                <h3 className="text-lg font-semibold mb-2">
                                    {feature.title}
                                </h3>
                                <p className="text-sm text-zinc-400 leading-relaxed">
                                    {feature.description}
                                </p>
                            </motion.div>
                        ))}
                    </motion.div>
                </div>
            </section>

            {/* Labels Explanation */}
            <section className="py-24 px-6 bg-zinc-900/30">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-16"
                    >
                        <h2 className="text-4xl font-bold mb-4">
                            Smart Categorization
                        </h2>
                        <p className="text-zinc-400 max-w-2xl mx-auto">
                            Every school is labeled based on your admission
                            probability, helping you build a balanced and
                            strategic college list.
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {[
                            {
                                label: 'Reach',
                                description:
                                    'Competitive schools where your stats are below average or acceptance rate is under 15%. Dream big!',
                                color: 'border-reach',
                                textColor: 'text-reach',
                                bgColor: 'bg-reach/10',
                                percentage: '< 15%',
                                icon: TrendingUp
                            },
                            {
                                label: 'Target',
                                description:
                                    "Schools where your stats align with admitted students. You're a competitive applicant.",
                                color: 'border-target',
                                textColor: 'text-target',
                                bgColor: 'bg-target/10',
                                percentage: '15-35%',
                                icon: Target
                            },
                            {
                                label: 'Safety',
                                description:
                                    'Schools where your stats exceed the average. High likelihood of admission.',
                                color: 'border-safety',
                                textColor: 'text-safety',
                                bgColor: 'bg-safety/10',
                                percentage: '> 35%',
                                icon: Shield
                            }
                        ].map((item, i) => (
                            <motion.div
                                key={item.label}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.1 }}
                                className={`glass-card p-8 border-t-2 ${item.color}`}
                            >
                                <div
                                    className={`inline-flex items-center justify-center w-12 h-12 rounded-xl ${item.bgColor} mb-4`}
                                >
                                    <item.icon
                                        className={`w-6 h-6 ${item.textColor}`}
                                    />
                                </div>
                                <div className="flex items-center gap-3 mb-3">
                                    <h3
                                        className={`text-2xl font-bold ${item.textColor}`}
                                    >
                                        {item.label}
                                    </h3>
                                    <span className="text-sm text-zinc-500 font-mono">
                                        {item.percentage}
                                    </span>
                                </div>
                                <p className="text-zinc-400 text-sm leading-relaxed">
                                    {item.description}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* How It Works */}
            <section id="how-it-works" className="py-24 px-6">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-16"
                    >
                        <h2 className="text-4xl font-bold mb-4">
                            How It Works
                        </h2>
                        <p className="text-zinc-400 max-w-2xl mx-auto">
                            Get started in minutes. Our AI advisor guides you
                            through the entire process.
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {howItWorks.map((item, i) => (
                            <motion.div
                                key={item.step}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.15 }}
                                className="relative"
                            >
                                {/* Connector line */}
                                {i < howItWorks.length - 1 && (
                                    <div className="hidden md:block absolute top-8 left-[60%] w-[80%] h-px bg-gradient-to-r from-white/20 to-transparent" />
                                )}

                                <div className="glass-card p-8">
                                    <span className="text-5xl font-bold text-white/10 mb-4 block">
                                        {item.step}
                                    </span>
                                    <h3 className="text-xl font-semibold mb-3">
                                        {item.title}
                                    </h3>
                                    <p className="text-sm text-zinc-400 leading-relaxed">
                                        {item.description}
                                    </p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Why College List AI Section */}
            <section className="py-24 px-6 bg-zinc-900/30">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-16"
                    >
                        <h2 className="text-4xl font-bold mb-4">
                            Why College List AI?
                        </h2>
                        <p className="text-zinc-400 max-w-2xl mx-auto">
                            Skip the guesswork. Get data-driven insights that save time and money.
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {whyPoints.map((point, i) => (
                            <motion.div
                                key={point.title}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.1 }}
                                className="glass-card p-6 text-center"
                            >
                                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-white/5 mb-4">
                                    <point.icon className="w-6 h-6 text-zinc-300" />
                                </div>
                                <h3 className="text-lg font-semibold mb-2">
                                    {point.title}
                                </h3>
                                <p className="text-sm text-zinc-400 leading-relaxed">
                                    {point.description}
                                </p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Emotional Paragraph Section */}
            <section className="py-16 px-6">
                <div className="max-w-3xl mx-auto text-center">
                    <motion.p
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-xl text-zinc-400 leading-relaxed italic"
                    >
                        "Choosing where to apply shouldn't feel like guessing. Whether you're in
                        the U.S. or halfway across the world, College List AI helps you build a list
                        that fits your profile, your dreams, and your budget – so you spend your
                        application time and money where it actually matters."
                    </motion.p>
                </div>
            </section>

            {/* Testimonials - Commented for future use */}
            {/* <section className="py-24 px-6 bg-zinc-900/30">
                <div className="max-w-7xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="text-center mb-16"
                    >
                        <h2 className="text-4xl font-bold mb-4">
                            Loved by Students
                        </h2>
                        <p className="text-zinc-400 max-w-2xl mx-auto">
                            Join thousands of students who have built their
                            college lists with College List AI.
                        </p>
                    </motion.div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {testimonials.map((testimonial, i) => (
                            <motion.div
                                key={testimonial.author}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: i * 0.1 }}
                                className="glass-card p-6"
                            >
                                <div className="flex gap-1 mb-4">
                                    {[...Array(5)].map((_, i) => (
                                        <Star
                                            key={i}
                                            className="w-4 h-4 fill-yellow-500 text-yellow-500"
                                        />
                                    ))}
                                </div>
                                <p className="text-zinc-300 text-sm mb-6 leading-relaxed italic">
                                    "{testimonial.quote}"
                                </p>
                                <div>
                                    <p className="font-semibold text-white">
                                        {testimonial.author}
                                    </p>
                                    <p className="text-xs text-zinc-500">
                                        {testimonial.role}
                                    </p>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section> */}

            {/* CTA Section */}
            <section className="py-24 px-6">
                <div className="max-w-4xl mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="glass-card p-12 text-center relative overflow-hidden"
                    >
                        {/* Background effects */}
                        <div className="absolute inset-0 bg-gradient-to-br from-target/10 via-transparent to-reach/10" />
                        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-[100px]" />

                        <div className="relative z-10">
                            <h2 className="text-4xl font-bold mb-4">
                                Ready to Build Your College List?
                            </h2>
                            <p className="text-zinc-400 mb-8 max-w-xl mx-auto">
                                Join students from the U.S. and around the world
                                using AI to find their perfect college match.
                                Start free, upgrade anytime.
                            </p>

                            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                                <Link
                                    to="/app/login"
                                    className="group flex items-center gap-2 px-8 py-4 bg-white text-zinc-950 rounded-xl font-semibold text-lg hover:bg-zinc-100 transition-all no-underline hover:scale-[1.02]"
                                >
                                    Get Your College List (Free)
                                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                                </Link>
                            </div>

                            <div className="flex items-center justify-center gap-6 mt-8 text-sm text-zinc-500">
                                <div className="flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4 text-safety" />
                                    <span>Free to start</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4 text-safety" />
                                    <span>No credit card required</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4 text-safety" />
                                    <span>Instant access</span>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Footer */}
            <footer className="py-12 px-6 border-t border-white/5">
                <div className="max-w-7xl mx-auto">
                    <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                        <div className="flex items-center gap-2">
                            <img src="https://em-content.zobj.net/source/apple/391/graduation-cap_1f393.png" alt="🎓" className="w-6 h-6" />
                            <span className="text-zinc-400 font-medium">
                                College List AI
                            </span>
                        </div>

                        <p className="text-sm text-zinc-600">
                            © 2026 College List AI. All rights reserved.
                        </p>

                        <div className="flex items-center gap-6 text-sm text-zinc-500">
                            <a
                                href="#"
                                className="hover:text-white transition-colors no-underline"
                            >
                                Privacy
                            </a>
                            <a
                                href="#"
                                className="hover:text-white transition-colors no-underline"
                            >
                                Terms
                            </a>
                            <a
                                href="https://github.com/LuisAbrantes/collegeListAI"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="hover:text-white transition-colors no-underline"
                            >
                                GitHub
                            </a>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}
