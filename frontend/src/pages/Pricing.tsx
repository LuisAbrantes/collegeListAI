/**
 * Pricing Page
 *
 * Launch pricing with USD/BRL currency toggle.
 * Features two plans: Free and Student (all premium features).
 * Glassmorphism design with animated cards and launch marketing copy.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
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

export function Pricing() {
    const navigate = useNavigate();
    const { user, session } = useAuth();

    const [currency, setCurrency] = useState<CurrencyCode>('USD');
    const copy = COPY[currency];
    const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>('monthly');
    const [pricing, setPricing] = useState<PricingResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

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
                    cancel_url: `${window.location.origin}/pricing?cancelled=true`
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

    /* ── Loading State ──────────────────────────────────────────────── */

    if (loading && !pricing) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-zinc-950">
                <div className="w-10 h-10 border-4 border-zinc-800 border-t-zinc-100 rounded-full animate-spin" />
            </div>
        );
    }

    const freeTier = pricing?.tiers.find(t => t.tier === 'free');
    const studentTier = pricing?.tiers.find(t => t.tier === 'student');

    /* ── Render ──────────────────────────────────────────────────────── */

    return (
        <div className="min-h-screen bg-zinc-950 relative overflow-hidden">
            {/* Background Ambient Effects */}
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-600/8 rounded-full blur-3xl" />
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-600/6 rounded-full blur-3xl" />
            </div>

            <div className="relative z-10 py-16 px-4">
                {/* ── Header ────────────────────────────────────────── */}
                <div className="max-w-4xl mx-auto text-center mb-14">
                    <div className="inline-flex items-center gap-2 px-4 py-2 mb-6 bg-violet-500/10 border border-violet-500/20 rounded-full">
                        <Rocket className="w-4 h-4 text-violet-400" />
                        <span className="text-sm font-medium text-violet-300 tracking-wide">
                            {copy.badge}
                        </span>
                    </div>

                    <h1 className="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
                        {copy.title}{' '}
                        <span className="bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
                            {copy.titleHighlight}
                        </span>
                    </h1>
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
                                        ${currency === cur
                                            ? 'bg-white text-zinc-900 shadow-sm'
                                            : 'text-zinc-400 hover:text-white'
                                        }
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
                                    ${billingPeriod === 'monthly'
                                        ? 'bg-white text-zinc-900 shadow-sm'
                                        : 'text-zinc-400 hover:text-white'
                                    }
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
                                    ${billingPeriod === 'annual'
                                        ? 'bg-white text-zinc-900 shadow-sm'
                                        : 'text-zinc-400 hover:text-white'
                                    }
                                `}
                            >
                                <Calendar className="w-4 h-4" />
                                {currency === 'BRL' ? 'Anual' : 'Annual'}
                                <span className="ml-1 px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-500/20 text-emerald-400">
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
                        <div className="mt-5 max-w-lg mx-auto p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 backdrop-blur-sm">
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
                        </div>
                    )}
                </div>

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
                <div className="max-w-3xl mx-auto grid md:grid-cols-2 gap-6">
                    {/* Free Card */}
                    {freeTier && (
                        <div className="group">
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
                        </div>
                    )}

                    {/* Student Card (Featured) */}
                    {studentTier && (
                        <div className="relative group md:-mt-3 md:mb-3">
                            {/* Popular Badge */}
                            <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                                <div className="px-4 py-1.5 bg-gradient-to-r from-violet-500 to-purple-600
                                                rounded-full text-white text-xs font-semibold
                                                shadow-lg shadow-violet-500/30">
                                    {copy.studentBadge}
                                </div>
                            </div>

                            <div className="h-full p-7 rounded-2xl border border-violet-500/40
                                           bg-zinc-900/70 backdrop-blur-sm shadow-xl shadow-violet-500/5
                                           transition-all duration-300 hover:border-violet-500/60
                                           hover:shadow-violet-500/10 flex flex-col">
                                {/* Icon & Name */}
                                <div className="flex items-center gap-3 mb-5">
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white">
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
                                            <Check className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                                            <span className="text-sm text-zinc-200">{feature}</span>
                                        </li>
                                    ))}
                                </ul>

                                {/* CTA */}
                                <button
                                    onClick={() => handleSubscribe('student')}
                                    disabled={checkoutLoading === 'student'}
                                    className="w-full py-3 px-4 rounded-xl font-semibold
                                               bg-gradient-to-r from-violet-500 to-purple-600 text-white
                                               hover:shadow-lg hover:shadow-violet-500/30 hover:scale-[1.02]
                                               transition-all flex items-center justify-center gap-2
                                               disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
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
                        </div>
                    )}
                </div>

                {/* ── Launch Teaser ──────────────────────────────────── */}
                <div className="max-w-3xl mx-auto mt-14">
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
                                    <span className="text-violet-400 font-medium">
                                        {copy.earlyAdopterHighlight}
                                    </span>
                                    {copy.earlyAdopterEnd}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

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

                {/* ── Back Link ──────────────────────────────────────── */}
                <div className="text-center mt-8">
                    <button
                        onClick={() => navigate(-1)}
                        className="text-sm text-zinc-500 hover:text-white transition-colors"
                    >
                        ← Back
                    </button>
                </div>
            </div>
        </div>
    );
}
