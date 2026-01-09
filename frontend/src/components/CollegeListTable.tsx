/**
 * CollegeListTable Component - Spreadsheet-like view for college list
 * 
 * Features:
 * - Sortable columns
 * - Inline notes editing
 * - Category pills with colors
 * - Formatted numbers (acceptance %, tuition $)
 * - Financial aid indicators
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronUp, 
  ChevronDown, 
  Trash2, 
  Edit2, 
  Check,
  X,
  DollarSign,
  GraduationCap,
  MapPin
} from 'lucide-react';
import type { CollegeListDetailedItem } from '../services/collegeListApi';

// =============================================================================
// Types
// =============================================================================

type SortKey = 'college_name' | 'label' | 'acceptance_rate' | 'sat_75th' | 'tuition_international' | 'state';
type SortDirection = 'asc' | 'desc';

interface CollegeListTableProps {
  colleges: CollegeListDetailedItem[];
  onRemove: (collegeName: string) => void;
  onUpdateNotes: (collegeName: string, notes: string) => void;
}

// =============================================================================
// Utility Functions
// =============================================================================

const formatAcceptanceRate = (rate: number | null): string => {
  if (rate === null) return '—';
  return `${(rate * 100).toFixed(0)}%`;
};

const formatTuition = (amount: number | null): string => {
  if (amount === null) return '—';
  return `$${(amount / 1000).toFixed(0)}k`;
};

const formatSatRange = (sat25: number | null, sat75: number | null): string => {
  if (sat25 === null && sat75 === null) return '—';
  if (sat25 === null) return `≤${sat75}`;
  if (sat75 === null) return `${sat25}+`;
  return `${sat25}–${sat75}`;
};

const formatLocation = (city: string | null, state: string | null): string => {
  if (city && state) return `${city}, ${state}`;
  return state || city || '—';
};

const getLabelColor = (label: string | null): string => {
  switch (label) {
    case 'reach': return 'bg-reach/20 text-reach border-reach/30';
    case 'target': return 'bg-target/20 text-target border-target/30';
    case 'safety': return 'bg-safety/20 text-safety border-safety/30';
    default: return 'bg-zinc-700/50 text-zinc-400 border-zinc-600/30';
  }
};

const getLabelSortValue = (label: string | null): number => {
  switch (label) {
    case 'reach': return 0;
    case 'target': return 1;
    case 'safety': return 2;
    default: return 3;
  }
};

// =============================================================================
// Sub-components
// =============================================================================

interface SortHeaderProps {
  label: string;
  sortKey: SortKey;
  currentSort: SortKey;
  direction: SortDirection;
  onSort: (key: SortKey) => void;
  className?: string;
}

function SortHeader({ label, sortKey, currentSort, direction, onSort, className = '' }: SortHeaderProps) {
  const isActive = currentSort === sortKey;
  
  return (
    <th 
      className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer select-none hover:bg-zinc-800/50 transition-colors ${className}`}
      onClick={() => onSort(sortKey)}
    >
      <div className="flex items-center gap-1">
        <span className={isActive ? 'text-zinc-100' : 'text-zinc-400'}>{label}</span>
        {isActive && (
          <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {direction === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </motion.span>
        )}
      </div>
    </th>
  );
}

interface EditableNotesProps {
  notes: string | null;
  onSave: (notes: string) => void;
}

function EditableNotes({ notes, onSave }: EditableNotesProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(notes || '');
  
  const handleSave = () => {
    onSave(value);
    setIsEditing(false);
  };
  
  const handleCancel = () => {
    setValue(notes || '');
    setIsEditing(false);
  };
  
  if (isEditing) {
    return (
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="flex-1 px-2 py-1 text-sm bg-zinc-800 border border-zinc-600 rounded text-zinc-100 focus:outline-none focus:border-zinc-500"
          placeholder="Add notes..."
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSave();
            if (e.key === 'Escape') handleCancel();
          }}
        />
        <button onClick={handleSave} className="p-1 text-emerald-400 hover:bg-emerald-500/20 rounded">
          <Check size={14} />
        </button>
        <button onClick={handleCancel} className="p-1 text-zinc-400 hover:bg-zinc-700 rounded">
          <X size={14} />
        </button>
      </div>
    );
  }
  
  return (
    <div className="flex items-center gap-2 group">
      <span className="text-sm text-zinc-400 truncate max-w-[200px]">
        {notes || <span className="italic text-zinc-600">No notes</span>}
      </span>
      <button 
        onClick={() => setIsEditing(true)}
        className="p-1 text-zinc-600 hover:text-zinc-300 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <Edit2 size={12} />
      </button>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function CollegeListTable({ 
  colleges, 
  onRemove, 
  onUpdateNotes 
}: CollegeListTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('label');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };
  
  const sortedColleges = useMemo(() => {
    const sorted = [...colleges].sort((a, b) => {
      let aVal: number | string;
      let bVal: number | string;
      
      switch (sortKey) {
        case 'label':
          aVal = getLabelSortValue(a.label);
          bVal = getLabelSortValue(b.label);
          break;
        case 'acceptance_rate':
          aVal = a.acceptance_rate ?? 999;
          bVal = b.acceptance_rate ?? 999;
          break;
        case 'sat_75th':
          aVal = a.sat_75th ?? 0;
          bVal = b.sat_75th ?? 0;
          break;
        case 'tuition_international':
          aVal = a.tuition_international ?? 0;
          bVal = b.tuition_international ?? 0;
          break;
        default:
          aVal = a[sortKey] ?? '';
          bVal = b[sortKey] ?? '';
      }
      
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortDirection === 'asc' 
          ? aVal.localeCompare(bVal) 
          : bVal.localeCompare(aVal);
      }
      
      return sortDirection === 'asc' 
        ? (aVal as number) - (bVal as number) 
        : (bVal as number) - (aVal as number);
    });
    
    return sorted;
  }, [colleges, sortKey, sortDirection]);
  
  if (colleges.length === 0) {
    return null;
  }
  
  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900/50">
      <table className="w-full min-w-[900px]">
        <thead className="bg-zinc-900 border-b border-zinc-800">
          <tr>
            <SortHeader 
              label="University" 
              sortKey="college_name" 
              currentSort={sortKey} 
              direction={sortDirection} 
              onSort={handleSort}
              className="w-[250px]"
            />
            <SortHeader 
              label="Category" 
              sortKey="label" 
              currentSort={sortKey} 
              direction={sortDirection} 
              onSort={handleSort}
              className="w-[100px]"
            />
            <SortHeader 
              label="Accept %" 
              sortKey="acceptance_rate" 
              currentSort={sortKey} 
              direction={sortDirection} 
              onSort={handleSort}
              className="w-[90px]"
            />
            <SortHeader 
              label="SAT" 
              sortKey="sat_75th" 
              currentSort={sortKey} 
              direction={sortDirection} 
              onSort={handleSort}
              className="w-[100px]"
            />
            <SortHeader 
              label="Tuition" 
              sortKey="tuition_international" 
              currentSort={sortKey} 
              direction={sortDirection} 
              onSort={handleSort}
              className="w-[90px]"
            />
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-400 w-[80px]">
              Aid
            </th>
            <SortHeader 
              label="Location" 
              sortKey="state" 
              currentSort={sortKey} 
              direction={sortDirection} 
              onSort={handleSort}
              className="w-[140px]"
            />
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Notes
            </th>
            <th className="px-4 py-3 w-[50px]"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800/50">
          <AnimatePresence>
            {sortedColleges.map((college) => (
              <motion.tr
                key={college.id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="hover:bg-zinc-800/30 transition-colors"
              >
                {/* University Name */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <GraduationCap size={16} className="text-zinc-500 flex-shrink-0" />
                    <span className="font-medium text-zinc-100 truncate">
                      {college.college_name}
                    </span>
                  </div>
                </td>
                
                {/* Category */}
                <td className="px-4 py-3">
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded border ${getLabelColor(college.label)}`}>
                    {college.label ? college.label.charAt(0).toUpperCase() + college.label.slice(1) : 'Unsorted'}
                  </span>
                </td>
                
                {/* Acceptance Rate */}
                <td className="px-4 py-3 font-mono text-sm text-zinc-300">
                  {formatAcceptanceRate(college.acceptance_rate)}
                </td>
                
                {/* SAT Range */}
                <td className="px-4 py-3 font-mono text-sm text-zinc-300">
                  {formatSatRange(college.sat_25th, college.sat_75th)}
                </td>
                
                {/* Tuition */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1 text-sm text-zinc-300">
                    <DollarSign size={12} className="text-zinc-500" />
                    <span className="font-mono">{formatTuition(college.tuition_international)}</span>
                  </div>
                </td>
                
                {/* Financial Aid */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    {college.need_blind_international && (
                      <span 
                        className="px-1.5 py-0.5 text-[10px] font-medium bg-emerald-900/50 text-emerald-400 rounded border border-emerald-700/50"
                        title="Need-blind for international students"
                      >
                        NB
                      </span>
                    )}
                    {college.meets_full_need && (
                      <span 
                        className="px-1.5 py-0.5 text-[10px] font-medium bg-blue-900/50 text-blue-400 rounded border border-blue-700/50"
                        title="Meets 100% financial need"
                      >
                        100%
                      </span>
                    )}
                    {!college.need_blind_international && !college.meets_full_need && (
                      <span className="text-zinc-600 text-xs">—</span>
                    )}
                  </div>
                </td>
                
                {/* Location */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1 text-sm text-zinc-400">
                    <MapPin size={12} className="text-zinc-600 flex-shrink-0" />
                    <span className="truncate">{formatLocation(college.city, college.state)}</span>
                  </div>
                </td>
                
                {/* Notes */}
                <td className="px-4 py-3">
                  <EditableNotes 
                    notes={college.notes} 
                    onSave={(notes) => onUpdateNotes(college.college_name, notes)}
                  />
                </td>
                
                {/* Actions */}
                <td className="px-4 py-3">
                  <button
                    onClick={() => onRemove(college.college_name)}
                    className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                    title="Remove from list"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </motion.tr>
            ))}
          </AnimatePresence>
        </tbody>
      </table>
    </div>
  );
}
