/**
 * MyList Component - User's saved college list
 * 
 * Features:
 * - Display colleges organized by category
 * - Search and add universities from database
 * - Fallback to AI search for unknown universities
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BookmarkX, 
  ListChecks, 
  ChevronDown, 
  ChevronUp, 
  Trash2, 
  RefreshCw,
  Search,
  Plus,
  X,
  Sparkles
} from 'lucide-react';
import { supabase } from '../services/supabase';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface CollegeListItem {
  id: string;
  college_name: string;
  label: 'reach' | 'target' | 'safety' | null;
  notes: string | null;
  added_at: string;
}

interface Exclusion {
  id: string;
  college_name: string;
  reason: string | null;
  created_at: string;
}

interface CollegeSearchResult {
  id: string;
  name: string;
  campus_setting: string | null;
  need_blind_domestic: boolean | null;
  need_blind_international: boolean | null;
  meets_full_need: boolean | null;
  state: string | null;
}

interface MyListProps {
  className?: string;
}

export function MyList({ className = '' }: MyListProps) {
  const [colleges, setColleges] = useState<CollegeListItem[]>([]);
  const [exclusions, setExclusions] = useState<Exclusion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showExclusions, setShowExclusions] = useState(false);
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<CollegeSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState<'reach' | 'target' | 'safety'>('target');
  const searchRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        setError('Not authenticated');
        return;
      }

      // Fetch college list
      const { data: listData, error: listError } = await supabase
        .from('user_college_list')
        .select('*')
        .eq('user_id', user.id)
        .order('added_at', { ascending: false });

      if (listError) throw listError;

      // Fetch exclusions
      const { data: exclusionData, error: exclusionError } = await supabase
        .from('user_exclusions')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });

      if (exclusionError) throw exclusionError;

      setColleges(listData || []);
      setExclusions(exclusionData || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRemove = async (collegeName: string) => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { error } = await supabase
        .from('user_college_list')
        .delete()
        .eq('user_id', user.id)
        .ilike('college_name', collegeName);

      if (error) throw error;
      
      setColleges(prev => prev.filter(c => 
        c.college_name.toLowerCase() !== collegeName.toLowerCase()
      ));
    } catch (err) {
      console.error('Failed to remove:', err);
    }
  };

  const handleUnexclude = async (collegeName: string) => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { error } = await supabase
        .from('user_exclusions')
        .delete()
        .eq('user_id', user.id)
        .ilike('college_name', collegeName);

      if (error) throw error;
      
      setExclusions(prev => prev.filter(e => 
        e.college_name.toLowerCase() !== collegeName.toLowerCase()
      ));
    } catch (err) {
      console.error('Failed to un-exclude:', err);
    }
  };

  // Search functions
  const searchColleges = useCallback(async (query: string) => {
    if (query.length < 2) {
      setSearchResults([]);
      return;
    }
    
    setIsSearching(true);
    try {
      const response = await fetch(`${API_BASE}/api/colleges/search?q=${encodeURIComponent(query)}&limit=8`);
      if (response.ok) {
        const results = await response.json();
        setSearchResults(results);
        setShowResults(true);
      }
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery) searchColleges(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, searchColleges]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleAddCollege = async (collegeName: string) => {
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      // Check if already in list
      const exists = colleges.some(c => c.college_name.toLowerCase() === collegeName.toLowerCase());
      if (exists) {
        setSearchQuery('');
        setShowResults(false);
        return;
      }

      const { data, error } = await supabase
        .from('user_college_list')
        .insert({
          id: crypto.randomUUID(),
          user_id: user.id,
          college_name: collegeName,
          label: selectedLabel,
        })
        .select()
        .single();

      if (error) throw error;
      
      setColleges(prev => [data, ...prev]);
      setSearchQuery('');
      setShowResults(false);
    } catch (err) {
      console.error('Failed to add college:', err);
    }
  };

  // Group colleges by label
  const grouped = {
    reach: colleges.filter(c => c.label === 'reach'),
    target: colleges.filter(c => c.label === 'target'),
    safety: colleges.filter(c => c.label === 'safety'),
    uncategorized: colleges.filter(c => !c.label),
  };

  const labelColors = {
    reach: 'border-l-reach text-reach',
    target: 'border-l-target text-target',
    safety: 'border-l-safety text-safety',
    uncategorized: 'border-l-zinc-500 text-zinc-400',
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center min-h-[50vh] ${className}`}>
        <div className="w-8 h-8 border-2 border-zinc-700 border-t-zinc-300 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex flex-col items-center justify-center min-h-[50vh] gap-4 ${className}`}>
        <p className="text-red-400">{error}</p>
        <button 
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm"
        >
          <RefreshCw size={14} />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className={`max-w-4xl mx-auto px-4 py-8 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <ListChecks className="w-8 h-8 text-zinc-400" />
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">My College List</h1>
          <p className="text-sm text-zinc-400">
            {colleges.length} {colleges.length === 1 ? 'school' : 'schools'} saved
          </p>
        </div>
      </div>

      {/* Search & Add Section */}
      <div ref={searchRef} className="relative mb-8">
        <div className="flex gap-2">
          {/* Label Selector */}
          <select
            value={selectedLabel}
            onChange={(e) => setSelectedLabel(e.target.value as 'reach' | 'target' | 'safety')}
            className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-300 focus:outline-none focus:border-zinc-600"
          >
            <option value="reach">Reach</option>
            <option value="target">Target</option>
            <option value="safety">Safety</option>
          </select>

          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => searchResults.length > 0 && setShowResults(true)}
              placeholder="Search university to add..."
              className="w-full pl-10 pr-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-600"
            />
            {searchQuery && (
              <button
                onClick={() => { setSearchQuery(''); setSearchResults([]); setShowResults(false); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Search Results Dropdown */}
        <AnimatePresence>
          {showResults && (searchResults.length > 0 || isSearching || searchQuery.length >= 2) && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute z-10 w-full mt-2 bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl overflow-hidden"
            >
              {isSearching ? (
                <div className="p-4 text-center text-zinc-500 text-sm">Searching...</div>
              ) : searchResults.length > 0 ? (
                <>
                  {searchResults.map((college) => (
                    <button
                      key={college.id}
                      onClick={() => handleAddCollege(college.name)}
                      className="w-full p-3 text-left hover:bg-zinc-800 flex items-center justify-between group border-b border-zinc-800 last:border-0"
                    >
                      <div>
                        <p className="text-sm text-zinc-100 font-medium">{college.name}</p>
                        <p className="text-xs text-zinc-500">
                          {college.state || college.campus_setting || 'University'}
                          {college.need_blind_international && ' • Need-blind'}
                        </p>
                      </div>
                      <Plus className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300" />
                    </button>
                  ))}
                </>
              ) : (
                <div className="p-4">
                  <p className="text-sm text-zinc-500 mb-3">No universities found in database</p>
                  <button
                    onClick={() => {
                      // For now, just add with the typed name
                      handleAddCollege(searchQuery);
                    }}
                    className="flex items-center gap-2 px-3 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm text-zinc-300"
                  >
                    <Sparkles className="w-4 h-4" />
                    Add "{searchQuery}" anyway
                  </button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Empty State */}
      {colleges.length === 0 && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass-card p-12 text-center"
        >
          <ListChecks className="w-16 h-16 mx-auto mb-4 text-zinc-600" />
          <h3 className="text-xl font-semibold text-zinc-300 mb-2">No colleges saved yet</h3>
          <p className="text-zinc-500 mb-6">
            Start building your list by asking the advisor for recommendations
            <br />
            or saying "add [school name] to my list"
          </p>
        </motion.div>
      )}

      {/* Grouped Lists */}
      {(['reach', 'target', 'safety', 'uncategorized'] as const).map((category) => {
        const items = grouped[category];
        if (items.length === 0) return null;

        return (
          <div key={category} className="mb-8">
            <h2 className={`text-lg font-semibold mb-4 capitalize ${labelColors[category].split(' ')[1]}`}>
              {category === 'uncategorized' ? 'Unsorted' : `${category} Schools`}
              <span className="text-zinc-500 font-normal ml-2">({items.length})</span>
            </h2>
            
            <div className="space-y-3">
              <AnimatePresence mode="popLayout">
                {items.map((college) => (
                  <motion.div
                    key={college.id}
                    layout
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20, height: 0 }}
                    className={`glass-card p-4 border-l-2 ${labelColors[category].split(' ')[0]} flex items-center justify-between`}
                  >
                    <div>
                      <h3 className="font-medium text-zinc-100">{college.college_name}</h3>
                      {college.notes && (
                        <p className="text-sm text-zinc-400 mt-1">{college.notes}</p>
                      )}
                      <p className="text-xs text-zinc-500 mt-1">
                        Added {new Date(college.added_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={() => handleRemove(college.college_name)}
                      className="p-2 text-zinc-500 hover:text-red-400 hover:bg-zinc-800 rounded-lg transition-colors"
                      title="Remove from list"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        );
      })}

      {/* Exclusions Section */}
      {exclusions.length > 0 && (
        <div className="mt-12 pt-8 border-t border-zinc-800">
          <button
            onClick={() => setShowExclusions(!showExclusions)}
            className="flex items-center gap-2 text-zinc-400 hover:text-zinc-300 mb-4"
          >
            <BookmarkX className="w-5 h-5" />
            <span>Excluded Schools ({exclusions.length})</span>
            {showExclusions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          <AnimatePresence>
            {showExclusions && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="space-y-2 overflow-hidden"
              >
                {exclusions.map((exc) => (
                  <div
                    key={exc.id}
                    className="flex items-center justify-between p-3 bg-zinc-900/50 rounded-lg"
                  >
                    <div>
                      <span className="text-zinc-300">{exc.college_name}</span>
                      {exc.reason && (
                        <span className="text-xs text-zinc-500 ml-2">({exc.reason})</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleUnexclude(exc.college_name)}
                      className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1"
                    >
                      Un-exclude
                    </button>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

