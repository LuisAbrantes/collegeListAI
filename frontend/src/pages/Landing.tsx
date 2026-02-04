/**
 * College List AI - Landing Page
 */

import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    ArrowRight,
    Sparkles,
    Target,
    ShieldCheck,
    GraduationCap,
    LineChart,
    Compass,
    ListTodo,
    Users
} from 'lucide-react';

const fadeUp = {
    initial: { opacity: 0, y: 18 },
    animate: { opacity: 1, y: 0 }
};

export function Landing() {
    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-100">
            <div className="relative overflow-hidden">
                <div className="absolute inset-0">
                    <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-reach/15 blur-[120px]" />
                    <div className="absolute top-10 right-0 h-[28rem] w-[28rem] rounded-full bg-target/10 blur-[140px]" />
                    <div className="absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-safety/10 blur-[120px]" />
                </div>

                <header className="relative z-10 flex items-center justify-between px-6 py-6 md:px-12">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/5 border border-white/10">
                            <Sparkles className="h-5 w-5 text-zinc-200" />
                        </div>
                        <div>
                            <p className="text-sm uppercase tracking-[0.2em] text-zinc-400">
                                College List AI
                            </p>
                            <p className="text-base font-semibold text-zinc-100">
                                Lista inteligente de faculdades
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                        <a className="hidden md:block text-zinc-400 hover:text-white transition-colors" href="#como-funciona">
                            Como funciona
                        </a>
                        <a className="hidden md:block text-zinc-400 hover:text-white transition-colors" href="#diferenciais">
                            Diferenciais
                        </a>
                        <a className="hidden md:block text-zinc-400 hover:text-white transition-colors" href="#faq">
                            FAQ
                        </a>
                        <Link
                            to="/app/login"
                            className="px-4 py-2 rounded-full border border-white/10 bg-white/5 text-zinc-100 hover:bg-white/10 transition"
                        >
                            Entrar
                        </Link>
                    </div>
                </header>

                <main className="relative z-10 px-6 pb-16 pt-8 md:px-12 md:pt-16">
                    <div className="grid items-center gap-12 lg:grid-cols-[1.1fr,0.9fr]">
                        <motion.div
                            initial={fadeUp.initial}
                            animate={fadeUp.animate}
                            transition={{ duration: 0.6 }}
                        >
                            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.2em] text-zinc-300">
                                <span className="h-2 w-2 rounded-full bg-safety" />
                                Analise real do seu perfil
                            </div>
                            <h1 className="mt-6 text-4xl font-semibold leading-tight text-white md:text-6xl">
                                Monte sua lista com clareza, foco e contexto.
                            </h1>
                            <p className="mt-6 max-w-xl text-lg text-zinc-300">
                                O College List AI organiza seu perfil, seus objetivos e suas restricoes
                                para construir uma estrategia de candidatura mais segura. Sem promessas
                                irreais, com transparencia e criterios claros.
                            </p>
                            <div className="mt-8 flex flex-wrap items-center gap-4">
                                <Link
                                    to="/app/login"
                                    className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-zinc-200"
                                >
                                    Comecar agora
                                    <ArrowRight className="h-4 w-4" />
                                </Link>
                                <a
                                    href="#como-funciona"
                                    className="inline-flex items-center gap-2 rounded-full border border-white/10 px-6 py-3 text-sm text-zinc-200 hover:bg-white/5 transition"
                                >
                                    Ver metodologia
                                </a>
                            </div>
                            <div className="mt-8 grid gap-4 sm:grid-cols-3">
                                {[
                                    { label: 'Perfil mapeado', value: 'Academico e financeiro' },
                                    { label: 'Lista balanceada', value: 'Alcance, alvo e seguranca' },
                                    { label: 'Plano de acao', value: 'Tarefas priorizadas' }
                                ].map((item) => (
                                    <div
                                        key={item.label}
                                        className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4"
                                    >
                                        <p className="text-sm text-zinc-400">{item.label}</p>
                                        <p className="mt-2 text-sm font-semibold text-zinc-100">
                                            {item.value}
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </motion.div>

                        <motion.div
                            initial={{ opacity: 0, scale: 0.96 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.6, delay: 0.1 }}
                            className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/10 via-white/5 to-transparent p-6"
                        >
                            <div className="rounded-2xl border border-white/10 bg-zinc-950/70 p-6">
                                <div className="flex items-center justify-between">
                                    <p className="text-sm text-zinc-400">Resumo do perfil</p>
                                    <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-zinc-300">
                                        Atualizado agora
                                    </span>
                                </div>
                                <div className="mt-6 grid gap-4">
                                    {[{
                                        title: 'Interesses academicos',
                                        value: 'Ciencia de Dados, Economia'
                                    }, {
                                        title: 'Orcamento anual',
                                        value: 'Definido por faixa, sem promessas'
                                    }, {
                                        title: 'Regioes de interesse',
                                        value: 'Costa Leste e Mid-West'
                                    }].map((item) => (
                                        <div key={item.title} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                                            <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">
                                                {item.title}
                                            </p>
                                            <p className="mt-2 text-sm font-medium text-zinc-100">
                                                {item.value}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                                <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                                    <div className="flex items-center gap-2">
                                        <LineChart className="h-4 w-4 text-safety" />
                                        <p className="text-sm font-semibold text-zinc-100">Prioridades</p>
                                    </div>
                                    <p className="mt-2 text-sm text-zinc-400">
                                        A lista final depende do seu engajamento e da qualidade das informacoes fornecidas.
                                        O assistente orienta, mas o resultado e o ritmo sao seus.
                                    </p>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                </main>
            </div>

            <section id="como-funciona" className="px-6 py-16 md:px-12">
                <div className="grid gap-10 lg:grid-cols-[0.9fr,1.1fr]">
                    <div>
                        <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Como funciona</p>
                        <h2 className="mt-4 text-3xl font-semibold text-white">
                            Um processo guiado, sem atalhos artificiais.
                        </h2>
                        <p className="mt-4 text-zinc-300">
                            Em vez de prometer prazos irreais, a plataforma organiza o caminho: diagnostico,
                            estrategia e plano de acao. Voce ve o que precisa fazer e quando.
                        </p>
                    </div>
                    <div className="grid gap-4">
                        {[{
                            icon: <Compass className="h-5 w-5 text-target" />,
                            title: 'Mapeamento completo',
                            text: 'Coletamos dados reais do seu perfil academico, financeiro e pessoal.'
                        }, {
                            icon: <Target className="h-5 w-5 text-reach" />,
                            title: 'Balanceamento inteligente',
                            text: 'Distribuimos faculdades entre alcance, alvo e seguranca.'
                        }, {
                            icon: <ListTodo className="h-5 w-5 text-safety" />,
                            title: 'Plano de execucao',
                            text: 'Checklist com prioridades, prazos recomendados e foco no que importa.'
                        }].map((item) => (
                            <div
                                key={item.title}
                                className="rounded-2xl border border-white/10 bg-white/5 p-5"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5">
                                        {item.icon}
                                    </div>
                                    <div>
                                        <p className="text-base font-semibold text-white">{item.title}</p>
                                        <p className="mt-1 text-sm text-zinc-400">{item.text}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section id="diferenciais" className="px-6 pb-16 md:px-12">
                <div className="rounded-3xl border border-white/10 bg-white/5 p-8">
                    <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
                        <div>
                            <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">
                                Diferenciais
                            </p>
                            <h2 className="mt-4 text-3xl font-semibold text-white">
                                O que voce recebe na pratica
                            </h2>
                        </div>
                        <p className="max-w-xl text-sm text-zinc-300">
                            Tudo focado em clareza, criterio e execucao. Nada de promessas de resultados
                            garantidos. O sistema orienta; voce decide e executa.
                        </p>
                    </div>
                    <div className="mt-8 grid gap-4 md:grid-cols-2">
                        {[{
                            icon: <GraduationCap className="h-5 w-5 text-zinc-100" />,
                            title: 'Lista recomendada e explicada',
                            text: 'Cada faculdade vem com o motivo de estar ali e o nivel de encaixe.'
                        }, {
                            icon: <ShieldCheck className="h-5 w-5 text-zinc-100" />,
                            title: 'Criterios transparentes',
                            text: 'Voce ve quais fatores pesaram mais e pode ajustar o foco.'
                        }, {
                            icon: <Users className="h-5 w-5 text-zinc-100" />,
                            title: 'Simulacao de cenarios',
                            text: 'Teste diferentes prioridades para entender o impacto na sua lista.'
                        }, {
                            icon: <LineChart className="h-5 w-5 text-zinc-100" />,
                            title: 'Acompanhamento do progresso',
                            text: 'Acompanhe tarefas e riscos sem perder o controle do cronograma.'
                        }].map((item) => (
                            <div key={item.title} className="rounded-2xl border border-white/10 bg-zinc-950/40 p-5">
                                <div className="flex items-center gap-3">
                                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5">
                                        {item.icon}
                                    </div>
                                    <div>
                                        <p className="text-base font-semibold text-white">{item.title}</p>
                                        <p className="mt-1 text-sm text-zinc-400">{item.text}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section className="px-6 pb-16 md:px-12">
                <div className="grid gap-6 lg:grid-cols-[1fr,1fr]">
                    <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                        <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Para quem</p>
                        <h3 className="mt-4 text-2xl font-semibold text-white">
                            Feito para quem quer decisao consciente.
                        </h3>
                        <ul className="mt-6 space-y-3 text-sm text-zinc-300">
                            <li className="flex items-start gap-2">
                                <CheckMark />
                                <span>Estudantes que precisam organizar criterios sem ruido.</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckMark />
                                <span>Familias que querem visualizar custo, risco e retorno.</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckMark />
                                <span>Orientadores que buscam uma base clara para aconselhar.</span>
                            </li>
                        </ul>
                    </div>
                    <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
                        <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Compromisso</p>
                        <h3 className="mt-4 text-2xl font-semibold text-white">
                            Sem promessas vazias. Com metodo.
                        </h3>
                        <p className="mt-4 text-sm text-zinc-300">
                            O College List AI nao promete resultados garantidos. O desempenho depende
                            do seu esforco, da qualidade do seu historico e do tempo disponivel.
                            Nosso papel e entregar clareza e direcao para que voce tome melhores decisoes.
                        </p>
                        <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-zinc-400">
                            Transparencia importa: se algo nao puder ser afirmado com seguranca, nao vamos afirmar.
                        </div>
                    </div>
                </div>
            </section>

            <section id="faq" className="px-6 pb-16 md:px-12">
                <div className="rounded-3xl border border-white/10 bg-white/5 p-8">
                    <div className="flex flex-col gap-2">
                        <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">FAQ</p>
                        <h2 className="text-3xl font-semibold text-white">Perguntas frequentes</h2>
                    </div>
                    <div className="mt-6 grid gap-4 lg:grid-cols-2">
                        {[{
                            q: 'Em quanto tempo minha lista fica pronta?',
                            a: 'Nao existe um prazo fixo. O tempo varia conforme a qualidade das informacoes e o ritmo de cada pessoa.'
                        }, {
                            q: 'O sistema garante aprovacao?',
                            a: 'Nao. Ele organiza criterios e orienta decisoes, mas o resultado depende do seu desempenho e contexto.'
                        }, {
                            q: 'Posso ajustar prioridades depois?',
                            a: 'Sim. Voce pode refazer escolhas e testar cenarios para entender impactos na lista.'
                        }, {
                            q: 'Os dados sao protegidos?',
                            a: 'Aplicamos boas praticas de seguranca e acesso restrito ao seu perfil.'
                        }].map((item) => (
                            <div key={item.q} className="rounded-2xl border border-white/10 bg-zinc-950/40 p-5">
                                <p className="text-sm font-semibold text-white">{item.q}</p>
                                <p className="mt-2 text-sm text-zinc-400">{item.a}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            <section className="px-6 pb-20 md:px-12">
                <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/10 via-white/5 to-transparent p-10 text-center">
                    <h2 className="text-3xl font-semibold text-white">
                        Pronto para construir sua lista com estrategia?
                    </h2>
                    <p className="mx-auto mt-4 max-w-2xl text-sm text-zinc-300">
                        Comece agora e receba um plano claro, sem promessas impossiveis.
                    </p>
                    <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
                        <Link
                            to="/app/login"
                            className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-zinc-200"
                        >
                            Criar minha lista
                            <ArrowRight className="h-4 w-4" />
                        </Link>
                        <Link
                            to="/app/login"
                            className="inline-flex items-center gap-2 rounded-full border border-white/10 px-6 py-3 text-sm text-zinc-200 hover:bg-white/5 transition"
                        >
                            Falar com o assistente
                        </Link>
                    </div>
                </div>
            </section>

            <footer className="px-6 pb-10 md:px-12">
                <div className="flex flex-col gap-4 border-t border-white/10 pt-6 text-sm text-zinc-500 md:flex-row md:items-center md:justify-between">
                    <p>(c) 2026 College List AI. Todos os direitos reservados.</p>
                    <div className="flex flex-wrap gap-4">
                        <span className="text-zinc-400">Privacidade</span>
                        <span className="text-zinc-400">Termos</span>
                        <span className="text-zinc-400">Contato</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}

function CheckMark() {
    return (
        <span className="mt-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/10">
            <span className="h-2 w-2 rounded-full bg-safety" />
        </span>
    );
}
