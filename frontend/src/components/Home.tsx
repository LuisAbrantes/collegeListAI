/**
 * Home Component - Platform Landing with Manual
 * 
 * Displays platform guide and recent chats.
 * Minimalist design with zinc color palette.
 */

import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  MessageSquare, 
  ListChecks, 
  Search, 
  BookOpen,
  Target,
  Shield,
  TrendingUp,
  Plus,
  ArrowRight,
  GraduationCap
} from 'lucide-react';
import { useChatContext } from '../contexts/ChatContext';

export function Home() {
  const navigate = useNavigate();
  const { threads, loadThread, newChat } = useChatContext();

  const handleNewChat = () => {
    newChat();
    navigate('/chat');
  };

  const handleLoadThread = (threadId: string) => {
    loadThread(threadId);
    navigate('/chat');
  };

  const features = [
    {
      icon: Search,
      title: 'Smart Recommendations',
      description: 'Get personalized college recommendations based on your GPA, test scores, and preferences.',
    },
    {
      icon: Target,
      title: 'Reach/Target/Safety',
      description: 'Each school is labeled based on your admission probability.',
    },
    {
      icon: Shield,
      title: 'Financial Aid Insights',
      description: 'Discover need-blind policies, merit scholarships, and financial aid opportunities.',
    },
    {
      icon: ListChecks,
      title: 'Build Your List',
      description: 'Save schools to your personal college list and track your applications.',
    },
  ];

  const examplePrompts = [
    "Give me 10 reach schools for Computer Science",
    "Which schools have the best financial aid?",
    "Add MIT to my college list",
    "Show me safety schools in California",
    "Tell me about Stanford's CS program",
  ];

  return (
    <div className="min-h-screen p-8 overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="flex items-center justify-center gap-3 mb-4">
            <GraduationCap className="w-10 h-10 text-zinc-300" />
            <h1 className="text-3xl font-bold text-zinc-100">Welcome to College List AI</h1>
          </div>
          <p className="text-zinc-400 max-w-xl mx-auto">
            Your AI-powered personalized college list maker. Build a strategic list, get personalized recommendations.
          </p>
        </motion.div>

        {/* Overview Section */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-6 mb-10"
        >
          <h2 className="text-lg font-semibold text-zinc-200 mb-3">How It Works</h2>
          <p className="text-sm text-zinc-400 leading-relaxed mb-4">
            College List AI helps you build a strategic college list tailored to your academic profile. 
            Simply chat with our AI advisor to get personalized recommendations based on your GPA, 
            test scores, intended major, and financial situation.
          </p>
          <p className="text-sm text-zinc-400 leading-relaxed">
            Our system categorizes schools into <span className="text-zinc-200">Reach</span> (competitive admits), 
            <span className="text-zinc-200"> Target</span> (good match), and <span className="text-zinc-200">Safety</span> (likely admits) 
            to help you create a balanced application strategy. You can save schools to your personal list 
            and track your college application journey.
          </p>
        </motion.div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
          <motion.button
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            whileHover={{ scale: 1.02 }}
            onClick={handleNewChat}
            className="glass-card p-6 text-left cursor-pointer border-none hover:bg-zinc-800/50 transition-colors"
          >
            <div className="flex items-center gap-3 mb-2">
              <Plus className="w-5 h-5 text-zinc-400" />
              <h3 className="text-lg font-semibold text-zinc-100">Start New Chat</h3>
            </div>
            <p className="text-zinc-500 text-sm">Ask for recommendations, explore schools, or get advice.</p>
          </motion.button>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <Link to="/my-list" className="block no-underline">
              <div className="glass-card p-6 hover:bg-zinc-800/50 transition-colors">
                <div className="flex items-center gap-3 mb-2">
                  <ListChecks className="w-5 h-5 text-zinc-400" />
                  <h3 className="text-lg font-semibold text-zinc-100">My College List</h3>
                </div>
                <p className="text-zinc-500 text-sm">View and manage your saved schools.</p>
              </div>
            </Link>
          </motion.div>
        </div>

        {/* Features Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mb-10"
        >
          <h2 className="text-lg font-semibold text-zinc-200 mb-4 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-zinc-400" />
            What You Can Do
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i }}
                className="glass-card p-4"
              >
                <div className="flex items-start gap-3">
                  <feature.icon className="w-4 h-4 text-zinc-500 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-zinc-200 text-sm mb-1">{feature.title}</h4>
                    <p className="text-xs text-zinc-500">{feature.description}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Example Prompts */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="mb-10"
        >
          <h2 className="text-lg font-semibold text-zinc-200 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-zinc-400" />
            Try Asking
          </h2>
          <div className="flex flex-wrap gap-2">
            {examplePrompts.map((prompt) => (
              <button
                key={prompt}
                onClick={handleNewChat}
                className="px-3 py-1.5 text-xs text-zinc-400 bg-zinc-900 hover:bg-zinc-800 rounded-full border border-zinc-800 hover:border-zinc-700 transition-colors cursor-pointer"
              >
                "{prompt}"
              </button>
            ))}
          </div>
        </motion.div>

        {/* Recent Chats */}
        {threads.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            <h2 className="text-lg font-semibold text-zinc-200 mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-zinc-400" />
              Recent Conversations
            </h2>
            <div className="space-y-2">
              {threads.slice(0, 5).map((thread) => (
                <motion.button
                  key={thread.id}
                  whileHover={{ x: 4 }}
                  onClick={() => handleLoadThread(thread.id)}
                  className="w-full glass-card p-3 text-left cursor-pointer border-none flex items-center justify-between group"
                >
                  <div className="flex items-center gap-3">
                    <MessageSquare className="w-4 h-4 text-zinc-600" />
                    <span className="text-sm text-zinc-300">{thread.title || 'New conversation'}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-zinc-700 group-hover:text-zinc-500 transition-colors" />
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

