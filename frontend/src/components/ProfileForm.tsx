/**
 * ProfileForm Component - Multi-step Wizard Feel
 */

import { useState } from 'react';
import type { FormEvent } from 'react';
import type { UserProfileCreate, CitizenshipStatus } from '../types/api';
import { motion } from 'framer-motion';

interface ProfileFormProps {
  onSubmit: (data: UserProfileCreate) => Promise<boolean>;
  loading?: boolean;
  error?: string | null;
}

export function ProfileForm({ onSubmit, loading = false, error }: ProfileFormProps) {
  const [citizenshipStatus, setCitizenshipStatus] = useState<CitizenshipStatus>('INTERNATIONAL');
  const [nationality, setNationality] = useState('');
  const [gpa, setGpa] = useState('');
  const [major, setMajor] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await onSubmit({ 
      citizenshipStatus,
      nationality: nationality || undefined, 
      gpa: parseFloat(gpa), 
      major 
    });
  };

  const isInternational = citizenshipStatus === 'INTERNATIONAL';

  return (
    <div className="min-h-screen flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card w-full max-w-lg p-12"
      >
        <span className="inline-block px-3 py-1 bg-white/10 rounded-full text-xs text-zinc-400 mb-6 font-mono">
          SETUP_O.1
        </span>
        
        <h2 className="text-2xl font-bold mb-2">
          Initialize Profile
        </h2>
        <p className="text-zinc-400 mb-10">
          Calibrating recommendations based on your academic data.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-8">
          
          {/* Citizenship Status */}
          <div>
            <label className="block mb-2 text-sm text-zinc-400">
              Citizenship Status
            </label>
            <select
              value={citizenshipStatus}
              onChange={(e) => setCitizenshipStatus(e.target.value as CitizenshipStatus)}
              required
              className="glass-input font-mono w-full"
            >
              <option value="INTERNATIONAL">International Student</option>
              <option value="US_CITIZEN">US Citizen</option>
              <option value="PERMANENT_RESIDENT">Permanent Resident</option>
              <option value="DACA">DACA</option>
            </select>
          </div>

          {/* Nationality - only show for international */}
          {isInternational && (
            <div>
              <label className="block mb-2 text-sm text-zinc-400">
                Country of Citizenship
              </label>
              <input
                type="text"
                value={nationality}
                onChange={(e) => setNationality(e.target.value)}
                placeholder="e.g. Brazil"
                required={isInternational}
                className="glass-input font-mono w-full"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-6">
            {/* GPA */}
            <div>
              <label className="block mb-2 text-sm text-zinc-400">
                GPA (4.0 Scale)
              </label>
              <input
                type="number"
                value={gpa}
                onChange={(e) => setGpa(e.target.value)}
                placeholder="3.8"
                step="0.01"
                min="0"
                max="4"
                required
                className="glass-input font-mono w-full"
              />
            </div>

            {/* Major */}
            <div>
              <label className="block mb-2 text-sm text-zinc-400">
                Intended Major
              </label>
              <input
                type="text"
                value={major}
                onChange={(e) => setMajor(e.target.value)}
                placeholder="Computer Science"
                required
                className="glass-input font-mono w-full"
              />
            </div>
          </div>

          {error && (
            <div className="text-red-400 text-sm">{error}</div>
          )}

          <motion.button
            type="submit"
            disabled={loading}
            whileHover={{ scale: 1.02, backgroundColor: '#fff' }}
            whileTap={{ scale: 0.98 }}
            className="mt-4 bg-zinc-100 text-black border-none py-3.5 px-6 rounded-lg text-base font-semibold cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? 'Analyzing...' : 'Launch Advisor'}
            {!loading && <span>→</span>}
          </motion.button>
        </form>
      </motion.div>
    </div>
  );
}
