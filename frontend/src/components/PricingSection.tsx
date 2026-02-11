/**
 * Pricing Section
 *
 * Reusable pricing component for the Landing Page.
 * Features two plans: Free and Student (all premium features).
 * Glassmorphism design with animated cards and launch marketing copy.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    Check,
    Sparkles,
    Zap,
    ArrowRight,
    Loader2,
    Globe,
    Rocket,
    Shield,
    X,
    Calendar,
    Heart
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

/* =========================================================================
   Type Definitions
   ========================================================================= */

type CurrencyCode = 'USD' | 'BRL';
type BillingPeriod = 'monthly' | 'annual';

interface PricingTier {
    tier: string;
    name: string;
    monthly_price: number;
    annual_price: number;
    features: string[];
    popular: boolean;
}

interface PricingResponse {
    currency: string;
    tiers: PricingTier[];
    launch_promo_active: boolean;
}

/* =========================================================================
   Constants
   ========================================================================= */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const CURRENCY_CONFIG: Record<CurrencyCode, { flag: string; label: string; symbol: string }> = {
    USD: { flag: '🇺🇸', label: 'USD', symbol: '$' },
    BRL: { flag: '🇧🇷', label: 'BRL', symbol: 'R$' },
};

/* ── Localized Copy ────────────────────────────────────────────────── */

const COPY = {
    USD: {
        badge: 'Launch Special',
        title: 'All Premium Features.',
        titleHighlight: 'One Simple Price.',
        subtitle: 'For a limited time, unlock everything at our Student price. No feature gates, no upsells — just full access.',
        launchPromo: 'Launch pricing active — lock in your rate today',
        freeName: 'Free',
        freePrice: 'Free',
        freeSubtitle: 'No credit card required',
        freeCta: 'Get Started',
        studentBadge: 'All Features Included',
        studentCta: 'Unlock Full Access',
        earlyAdopterTitle: 'Early Adopter Advantage',
        earlyAdopterText: "You're getting every premium feature at our launch price. When we introduce higher tiers, Student subscribers get",
        earlyAdopterHighlight: 'exclusive upgrade discounts',
        earlyAdopterEnd: '. Lock in your rate today.',
        trustPayments: 'Secure payments by Stripe',
        trustCancel: 'Cancel anytime',
    },
    BRL: {
        badge: 'Especial de Lançamento',
        title: 'Do Brasil para o mundo.',
        titleHighlight: 'Preço justo em reais.',
        subtitle: 'Pague em reais com câmbio fixo — economize comparado ao dólar. Sem IOF, sem surpresas na fatura.',
        launchPromo: 'Preço de lançamento ativo — garanta o seu agora',
        freeName: 'Grátis',
        freePrice: 'Grátis',
        freeSubtitle: 'Sem cartão de crédito',
        freeCta: 'Começar Grátis',
        studentBadge: 'Tudo Incluso',
        studentCta: 'Desbloquear Acesso Total',
        earlyAdopterTitle: 'Vantagem de Early Adopter',
        earlyAdopterText: 'Você está garantindo todas as funcionalidades premium no preço de lançamento. Quando lançarmos planos superiores, assinantes Student terão',
        earlyAdopterHighlight: 'descontos exclusivos de upgrade',
        earlyAdopterEnd: '. Garanta seu preço hoje.',
        trustPayments: 'Pagamentos seguros via Stripe',
        trustCancel: 'Cancele quando quiser',
    },
};

/* =========================================================================
   Component
   ========================================================================= */

const THEME = {
    USD: {
        badgeBg: 'bg-white/10',
        badgeBorder: 'border-white/20',
        badgeText: 'text-zinc-200',
        badgeIcon: 'text-zinc-100',
        titleGradient: 'from-white to-zinc-400',
        
        // Student Card
        cardBorder: 'border-white/20',
        cardBg: 'bg-zinc-900/80',
        cardShadow: 'shadow-white/5',
        cardIconBg: 'bg-white',
        cardIconColor: 'text-zinc-950',
        
        // Button
        buttonBg: 'bg-white text-zinc-950 hover:bg-zinc-200',
        buttonShadow: 'hover:shadow-white/10',
        
        // Accents
        checkColor: 'text-white',
        popularBadgeBg: 'bg-white text-zinc-950',
        popularBadgeShadow: 'shadow-white/20',

        // Toggles
        toggleActive: 'bg-white text-zinc-950',
        toggleInactive: 'text-zinc-400 hover:text-white',
    },
    BRL: {
        badgeBg: 'bg-green-500/10',
        badgeBorder: 'border-green-500/20',
        badgeText: 'text-green-400',
        badgeIcon: 'text-yellow-400',
        titleGradient: 'from-green-400 to-yellow-400',

        // Student Card
        cardBorder: 'border-green-500/40',
        cardBg: 'bg-zinc-900/80', // Keep dark bg, just colored borders
        cardShadow: 'shadow-green-500/10',
        cardIconBg: 'bg-gradient-to-br from-green-500 to-yellow-500',
        cardIconColor: 'text-zinc-950',

        // Button
        buttonBg: 'bg-gradient-to-r from-green-500 to-yellow-500 text-zinc-950 hover:brightness-110',
        buttonShadow: 'hover:shadow-green-500/20',

        // Accents
        checkColor: 'text-green-400',
        popularBadgeBg: 'bg-gradient-to-r from-green-500 to-yellow-500 text-zinc-950',
        popularBadgeShadow: 'shadow-green-500/30',

        // Toggles
        toggleActive: 'bg-gradient-to-r from-green-500 to-yellow-500 text-zinc-950',
        toggleInactive: 'text-zinc-400 hover:text-white',
    }
};

/* =========================================================================
   Component
   ========================================================================= */

export function PricingSection() {
    const navigate = useNavigate();
    const { user, session } = useAuth();
    const [currency, setCurrency] = useState<CurrencyCode>('USD');
    const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>('monthly');
    const [pricing, setPricing] = useState<PricingResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const copy = COPY[currency];
    const theme = THEME[currency];

    /* ── Data Fetching ──────────────────────────────────────────────── */

    const fetchPricing = useCallback(async (cur: CurrencyCode) => {
        try {
            setLoading(true);
            const res = await fetch(
                `${API_URL}/api/subscriptions/pricing?currency=${cur}`
            );
            if (!res.ok) throw new Error('Failed to fetch pricing');
            const data: PricingResponse = await res.json();
            setPricing(data);
        } catch (err) {
            setError('Unable to load pricing. Please try again.');
            console.error('Pricing fetch error:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPricing(currency);
    }, [currency, fetchPricing]);

    /* ── Handlers ───────────────────────────────────────────────────── */

    const handleCurrencyToggle = (cur: CurrencyCode) => {
        if (cur !== currency) {
            setCurrency(cur);
        }
    };

    const handleSubscribe = async (tier: string) => {
        if (tier === 'free') {
            navigate('/app');
            return;
        }

        if (!user || !session) {
            navigate(`/app/login?returnTo=${encodeURIComponent('/pricing')}`);
            return;
        }

        setCheckoutLoading(tier);
        setError(null);

        try {
            const res = await fetch(`${API_URL}/api/subscriptions/checkout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${session.access_token}`
                },
                body: JSON.stringify({
                    tier,
                    billing_period: billingPeriod,
                    currency,
                    success_url: `${window.location.origin}/app?subscription=success`,
                    cancel_url: `${window.location.origin}/?cancelled=true`
                })
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.detail || 'Checkout failed');
            }

            const { checkout_url } = await res.json();
            window.location.href = checkout_url;
        } catch (err) {
            setError(
                err instanceof Error ? err.message : 'Failed to start checkout'
            );
        } finally {
            setCheckoutLoading(null);
        }
    };

    /* ── Price Formatting ───────────────────────────────────────────── */

    const formatPrice = (cents: number): string => {
        if (cents === 0) return 'Free';
        const amount = cents / 100;
        const config = CURRENCY_CONFIG[currency];

        if (currency === 'BRL') {
            return `${config.symbol}${amount.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`;
        }
        return `${config.symbol}${amount.toFixed(0)}`;
    };

    const freeTier = pricing?.tiers.find(t => t.tier === 'free');
    const studentTier = pricing?.tiers.find(t => t.tier === 'student');

    /* ── Render ──────────────────────────────────────────────────────── */

    return (
        <section className="py-24 px-6 relative overflow-hidden" id="pricing">
            {/* Background Ambient Effects */}
            <div className="absolute inset-0 pointer-events-none">
                {currency === 'BRL' ? (
                     <>
                        <div className="absolute top-0 right-1/4 w-96 h-96 bg-green-600/10 rounded-full blur-3xl opacity-50" />
                        <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-yellow-600/10 rounded-full blur-3xl opacity-50" />
                     </>
                ) : (
                    <>
                        <div className="absolute top-0 right-1/4 w-96 h-96 bg-zinc-600/5 rounded-full blur-3xl" />
                        <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-white/5 rounded-full blur-3xl" />
                    </>
                )}
            </div>

            <div className="max-w-7xl mx-auto relative z-10">
                {/* ── Header ────────────────────────────────────────── */}
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="max-w-4xl mx-auto text-center mb-14"
                >
                    <div className={`inline-flex items-center gap-2 px-4 py-2 mb-6 rounded-full border ${theme.badgeBg} ${theme.badgeBorder}`}>
                        <Rocket className={`w-4 h-4 ${theme.badgeIcon}`} />
                        <span className={`text-sm font-medium tracking-wide ${theme.badgeText}`}>
                            {copy.badge}
                        </span>
                    </div>

                    <h2 className="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
                        {copy.title}{' '}
                        <span className={`bg-gradient-to-r ${theme.titleGradient} bg-clip-text text-transparent`}>
                            {copy.titleHighlight}
                        </span>
                    </h2>
                    <p className="text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed">
                        {copy.subtitle}
                    </p>

                    {/* ── Toggles Row ────────────────────────────────── */}
                    <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
                        {/* Currency Toggle */}
                        <div className="inline-flex items-center gap-1 p-1.5 bg-zinc-900/70 rounded-xl border border-white/10 backdrop-blur-sm">
                            {(Object.keys(CURRENCY_CONFIG) as CurrencyCode[]).map(cur => (
                                <button
                                    key={cur}
                                    onClick={() => handleCurrencyToggle(cur)}
                                    className={`
                                        px-5 py-2.5 rounded-lg text-sm font-medium
                                        transition-all duration-200 flex items-center gap-2.5
                                        ${currency === cur ? theme.toggleActive : theme.toggleInactive}
                                    `}
                                >
                                    <span className="text-base">{CURRENCY_CONFIG[cur].flag}</span>
                                    {CURRENCY_CONFIG[cur].label}
                                </button>
                            ))}
                        </div>

                        {/* Billing Period Toggle */}
                        <div className="inline-flex items-center gap-1 p-1.5 bg-zinc-900/70 rounded-xl border border-white/10 backdrop-blur-sm">
                            <button
                                onClick={() => setBillingPeriod('monthly')}
                                className={`
                                    px-5 py-2.5 rounded-lg text-sm font-medium
                                    transition-all duration-200 flex items-center gap-2
                                    ${billingPeriod === 'monthly' ? (currency === 'BRL' ? theme.toggleActive : 'bg-white text-zinc-900 shadow-sm') : 'text-zinc-400 hover:text-white'}
                                `}
                            >
                                <Calendar className="w-4 h-4" />
                                {currency === 'BRL' ? 'Mensal' : 'Monthly'}
                            </button>
                            <button
                                onClick={() => setBillingPeriod('annual')}
                                className={`
                                    px-5 py-2.5 rounded-lg text-sm font-medium
                                    transition-all duration-200 flex items-center gap-2 relative
                                    ${billingPeriod === 'annual' ? (currency === 'BRL' ? theme.toggleActive : 'bg-white text-zinc-900 shadow-sm') : 'text-zinc-400 hover:text-white'}
                                `}
                            >
                                <Calendar className="w-4 h-4" />
                                {currency === 'BRL' ? 'Anual' : 'Annual'}
                                <span className={`ml-1 px-1.5 py-0.5 text-[10px] font-semibold rounded-full ${currency === 'BRL' ? 'bg-zinc-900/20 text-zinc-900' : 'bg-emerald-500/20 text-emerald-400'}`}>
                                    -17%
                                </span>
                            </button>
                        </div>
                    </div>

                    {pricing?.launch_promo_active && (
                        <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                            <Sparkles className="w-4 h-4 text-emerald-400" />
                            <span className="text-sm text-emerald-300">
                                {copy.launchPromo}
                            </span>
                        </div>
                    )}

                    {/* ── Brazilian Advantage Banner ──────────────────── */}
                    {currency === 'BRL' && (
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="mt-5 max-w-lg mx-auto p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 backdrop-blur-sm"
                        >
                            <div className="flex items-start gap-3">
                                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                                    <Heart className="w-4 h-4 text-emerald-400" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-emerald-300">
                                        Feito por brasileiros, para brasileiros.
                                    </p>
                                    <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                                        Câmbio fixo de R$5 por dólar — sem IOF, sem surpresas. Você economiza até 14% comparado ao preço em dólar.
                                    </p>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </motion.div>

                {/* ── Error ──────────────────────────────────────────── */}
                {error && (
                    <div className="max-w-4xl mx-auto mb-8">
                        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-center text-sm flex items-center justify-center gap-2">
                            <X className="w-4 h-4 flex-shrink-0" />
                            {error}
                        </div>
                    </div>
                )}

                {/* ── Pricing Cards ─────────────────────────────────── */}
                {loading && !pricing ? (
                     <div className="flex justify-center py-12">
                        <div className="w-10 h-10 border-4 border-zinc-800 border-t-zinc-100 rounded-full animate-spin" />
                    </div>
                ) : (
                    <div className="max-w-3xl mx-auto grid md:grid-cols-2 gap-6">
                        {/* Free Card */}
                        {freeTier && (
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.2 }}
                                className="group"
                            >
                                <div className="h-full p-7 rounded-2xl border border-white/10 bg-zinc-900/50 backdrop-blur-sm
                                            transition-all duration-300 hover:border-white/20 flex flex-col">
                                    {/* Icon & Name */}
                                    <div className="flex items-center gap-3 mb-5">
                                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-zinc-600 to-zinc-700 flex items-center justify-center text-white">
                                            <Zap className="w-5 h-5" />
                                        </div>
                                        <h3 className="text-xl font-semibold text-white">
                                            {copy.freeName}
                                        </h3>
                                    </div>

                                    {/* Price */}
                                    <div className="mb-6">
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-4xl font-bold text-white">{copy.freePrice}</span>
                                        </div>
                                        <p className="text-sm text-zinc-500 mt-1">
                                            {copy.freeSubtitle}
                                        </p>
                                    </div>

                                    {/* Features */}
                                    <ul className="space-y-3 mb-8 flex-1">
                                        {freeTier.features.map((feature, i) => (
                                            <li key={i} className="flex items-start gap-3">
                                                <Check className="w-4 h-4 text-zinc-500 flex-shrink-0 mt-0.5" />
                                                <span className="text-sm text-zinc-400">{feature}</span>
                                            </li>
                                        ))}
                                    </ul>

                                    {/* CTA */}
                                    <button
                                        onClick={() => handleSubscribe('free')}
                                        className="w-full py-3 px-4 rounded-xl font-semibold
                                                bg-zinc-800 text-zinc-300 hover:bg-zinc-700
                                                transition-all flex items-center justify-center gap-2
                                                active:scale-95"
                                    >
                                        {copy.freeCta}
                                        <ArrowRight className="w-4 h-4" />
                                    </button>
                                </div>
                            </motion.div>
                        )}

                        {/* Student Card (Featured) */}
                        {studentTier && (
                            <motion.div 
                                initial={{ opacity: 0, x: 20 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.3 }}
                                className="relative group md:-mt-3 md:mb-3"
                            >
                                {/* Popular Badge */}
                                <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                                    <div className={`px-4 py-1.5 ${theme.popularBadgeBg}
                                                    rounded-full text-xs font-semibold
                                                    shadow-lg ${theme.popularBadgeShadow}`}>
                                        {copy.studentBadge}
                                    </div>
                                </div>

                                <div className={`h-full p-7 rounded-2xl border ${theme.cardBorder}
                                            ${theme.cardBg} backdrop-blur-sm shadow-xl ${theme.cardShadow}
                                            transition-all duration-300
                                            hover:shadow-violet-500/10 flex flex-col`}>
                                    {/* Icon & Name */}
                                    <div className="flex items-center gap-3 mb-5">
                                        <div className={`w-10 h-10 rounded-xl ${theme.cardIconBg} flex items-center justify-center ${theme.cardIconColor}`}>
                                            <Sparkles className="w-5 h-5" />
                                        </div>
                                        <h3 className="text-xl font-semibold text-white">
                                            {studentTier.name}
                                        </h3>
                                    </div>

                                    {/* Price */}
                                    <div className="mb-6">
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-4xl font-bold text-white">
                                                {billingPeriod === 'annual'
                                                    ? formatPrice(Math.round(studentTier.annual_price / 12))
                                                    : formatPrice(studentTier.monthly_price)
                                                }
                                            </span>
                                            <span className="text-zinc-500">/month</span>
                                        </div>
                                        <p className="text-sm text-zinc-500 mt-1">
                                            {billingPeriod === 'annual'
                                                ? (currency === 'BRL'
                                                    ? `Cobrado ${formatPrice(studentTier.annual_price)}/ano`
                                                    : `Billed ${formatPrice(studentTier.annual_price)}/year`
                                                )
                                                : (currency === 'BRL' ? 'Cobrado mensalmente' : 'Billed monthly')
                                            }
                                        </p>
                                    </div>

                                    {/* Features */}
                                    <ul className="space-y-3 mb-8 flex-1">
                                        {studentTier.features.map((feature, i) => (
                                            <li key={i} className="flex items-start gap-3">
                                                <Check className={`w-4 h-4 flex-shrink-0 mt-0.5 ${theme.checkColor}`} />
                                                <span className="text-sm text-zinc-200">{feature}</span>
                                            </li>
                                        ))}
                                    </ul>

                                    {/* CTA */}
                                    <button
                                        onClick={() => handleSubscribe('student')}
                                        disabled={checkoutLoading === 'student'}
                                        className={`w-full py-3 px-4 rounded-xl font-semibold
                                                ${theme.buttonBg}
                                                hover:shadow-lg ${theme.buttonShadow} hover:scale-[1.02]
                                                transition-all flex items-center justify-center gap-2
                                                disabled:opacity-50 disabled:cursor-not-allowed active:scale-95`}
                                    >
                                        {checkoutLoading === 'student' ? (
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                        ) : (
                                            <>
                                                {copy.studentCta}
                                                <ArrowRight className="w-4 h-4" />
                                            </>
                                        )}
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </div>
                )}


                {/* ── Launch Teaser ──────────────────────────────────── */}
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.4 }}
                    className="max-w-3xl mx-auto mt-14"
                >
                    <div className="p-6 rounded-2xl border border-white/5 bg-zinc-900/30 backdrop-blur-sm">
                        <div className="flex items-start gap-4">
                            <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
                                <Shield className="w-5 h-5 text-amber-400" />
                            </div>
                            <div>
                                <h3 className="text-base font-semibold text-white mb-1">
                                    {copy.earlyAdopterTitle}
                                </h3>
                                <p className="text-sm text-zinc-400 leading-relaxed">
                                    {copy.earlyAdopterText}{' '}
                                    <span className="text-amber-400 font-medium">
                                        {copy.earlyAdopterHighlight}
                                    </span>
                                    {copy.earlyAdopterEnd}
                                </p>
                            </div>
                        </div>
                    </div>
                </motion.div>

                {/* ── Trust Indicators ───────────────────────────────── */}
                <div className="max-w-2xl mx-auto text-center mt-10">
                    <div className="flex items-center justify-center gap-6 text-zinc-600 text-xs">
                        <div className="flex items-center gap-1.5">
                            <Shield className="w-3.5 h-3.5" />
                            <span>{copy.trustPayments}</span>
                        </div>
                        <span className="text-zinc-800">·</span>
                        <div className="flex items-center gap-1.5">
                            <Globe className="w-3.5 h-3.5" />
                            <span>{copy.trustCancel}</span>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}

