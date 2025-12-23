/**
 * CollegeCard Component - Minimalist "Trading Card" Style
 */

import type { CollegeLabel } from '../types/api';
import { motion } from 'framer-motion';

interface CollegeCardProps {
  name: string;
  label: CollegeLabel;
  matchScore?: number;
  reasoning?: string;
  financialAidInfo?: string;
  url?: string;
  onExclude?: () => void;
}

export function CollegeCard({
  name,
  label,
  matchScore,
  reasoning,
  financialAidInfo,
  url,
  onExclude,
}: CollegeCardProps) {
  
  // Map labels to Tailwind color classes
  const accentColors = {
    Reach: { border: 'border-l-reach', text: 'text-reach', bg: 'bg-reach' },
    Target: { border: 'border-l-target', text: 'text-target', bg: 'bg-target' },
    Safety: { border: 'border-l-safety', text: 'text-safety', bg: 'bg-safety' },
  };

  const colors = accentColors[label];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className={`glass-card p-6 mb-4 border-l-2 bg-zinc-900/40 ${colors.border}`}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-xl font-semibold m-0">{name}</h3>
        <span className={`text-[0.65rem] uppercase tracking-wider px-2 py-0.5 rounded border border-current font-mono ${colors.text}`}>
          {label}
        </span>
      </div>

      {/* Match Bar */}
      {matchScore !== undefined && (
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: `${matchScore}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
              className={`h-full rounded-full ${colors.bg}`}
            />
          </div>
          <span className="font-mono text-xs text-zinc-400">
            {matchScore}%
          </span>
        </div>
      )}

      {/* Content */}
      <div className="text-sm text-zinc-400 leading-relaxed mb-4">
        <p className="mb-2">{reasoning}</p>
        
        {financialAidInfo && (
          <div className="flex items-center gap-2 mt-3 text-xs">
            <span className="text-white">$</span>
            <span>{financialAidInfo}</span>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="flex gap-4 mt-5 pt-4 border-t border-white/5">
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-zinc-200 no-underline font-medium hover:text-white transition-colors"
          >
            Visit Website ↗
          </a>
        )}
        
        {onExclude && (
          <button
            onClick={onExclude}
            className="ml-auto bg-none border-none text-sm text-zinc-500 cursor-pointer hover:text-zinc-300 transition-colors"
          >
            Hide
          </button>
        )}
      </div>
    </motion.div>
  );
}
