/**
 * Profile Component
 * 
 * Full page profile editor.
 */

import { useState } from 'react';
// import { useNavigate } from 'react-router-dom'; // Navigation handled by Sidebar
import type { UserProfile, UserProfileUpdate } from '../types/api';
import { useProfile } from '../hooks/useProfile';

interface ProfileProps {
  currentProfile: UserProfile;
}

export function Profile({ currentProfile }: ProfileProps) {
  const { updateProfile } = useProfile();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<UserProfileUpdate>({
    nationality: currentProfile.nationality,
    gpa: currentProfile.gpa,
    major: currentProfile.major,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    const success = await updateProfile(formData);
    
    if (success) {
      setSuccessMsg('Profile updated successfully!');
      setTimeout(() => setSuccessMsg(null), 3000);
    } else {
      setError('Failed to update profile. Please try again.');
    }
    setLoading(false);
  };

  return (
    <div className="flex-1 h-full overflow-y-auto p-12 bg-zinc-950">
      <div className="max-w-2xl mx-auto">
        <header className="mb-12">
          <h2 className="text-3xl font-bold text-white mb-2">
            Settings
          </h2>
          <p className="text-zinc-400">Manage your profile and preferences.</p>
        </header>

        <section className="mb-8">
            <h3 className="text-xl font-medium text-white mb-6 pb-2 border-b border-white/10">
                Academic Profile
            </h3>

            <form onSubmit={handleSubmit} className="space-y-8">
            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                {error}
                </div>
            )}
            
            {successMsg && (
                <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-400 text-sm">
                {successMsg}
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                    <label htmlFor="nationality" className="block text-sm font-medium text-zinc-200">
                      Nationality
                    </label>
                    <input
                      id="nationality"
                      type="text"
                      required
                      value={formData.nationality}
                      onChange={e => setFormData(prev => ({ ...prev, nationality: e.target.value }))}
                      className="w-full px-4 py-3 rounded-lg bg-zinc-900 border border-white/10 text-white focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-colors"
                      placeholder="e.g., Brazil, USA"
                    />
                    <p className="text-xs text-zinc-400">Used to determine financial aid eligibility.</p>
                </div>

                <div className="space-y-2">
                    <label htmlFor="gpa" className="block text-sm font-medium text-zinc-200">
                      GPA (4.0 scale)
                    </label>
                    <input
                      id="gpa"
                      type="number"
                      step="0.1"
                      min="0"
                      max="4.0"
                      required
                      value={formData.gpa}
                      onChange={e => setFormData(prev => ({ ...prev, gpa: parseFloat(e.target.value) }))}
                      className="w-full px-4 py-3 rounded-lg bg-zinc-900 border border-white/10 text-white focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-colors"
                      placeholder="e.g., 3.5"
                    />
                    <p className="text-xs text-zinc-400">Your unweighted high school GPA.</p>
                </div>

                <div className="space-y-2 md:col-span-2">
                    <label htmlFor="major" className="block text-sm font-medium text-zinc-200">
                      Intended Major
                    </label>
                    <input
                      id="major"
                      type="text"
                      required
                      value={formData.major}
                      onChange={e => setFormData(prev => ({ ...prev, major: e.target.value }))}
                      className="w-full px-4 py-3 rounded-lg bg-zinc-900 border border-white/10 text-white focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-colors"
                      placeholder="e.g., Computer Science"
                    />
                     <p className="text-xs text-zinc-400">This helps finding programs with strong reputation in your field.</p>
                </div>
            </div>

            <div className="pt-4 border-t border-white/10 flex justify-end">
                <button
                    type="submit"
                    disabled={loading}
                    className="px-6 py-2.5 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading ? 'Saving Changes...' : 'Save Changes'}
                </button>
            </div>
            </form>
        </section>
      </div>
    </div>
  );
}
