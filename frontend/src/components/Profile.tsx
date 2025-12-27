/**
 * Profile Component
 * 
 * Full page profile editor with conditional fields based on citizenship status.
 * Supports International and Domestic (US) students.
 */

import { useState, useMemo } from 'react';
import type { 
  UserProfile, 
  UserProfileUpdate, 
  CitizenshipStatus, 
  HouseholdIncomeTier,
  CampusVibe,
  PostGradGoal,
  EnglishTestType
} from '../types/api';
import { useProfile } from '../hooks/useProfile';
import { User, GraduationCap, DollarSign, Target, Globe, MapPin, Trophy, Users, Briefcase, BookOpen } from 'lucide-react';

// US States for residence selector
const US_STATES = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
  'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
  'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
  'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
  'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
  'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
  'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
  'Wisconsin', 'Wyoming'
];

interface ProfileProps {
  currentProfile: UserProfile;
}

export function Profile({ currentProfile }: ProfileProps) {
  const { updateProfile } = useProfile();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<UserProfileUpdate>({
    citizenshipStatus: currentProfile.citizenshipStatus,
    name: currentProfile.name || '',
    nationality: currentProfile.nationality || '',
    gpa: currentProfile.gpa,
    major: currentProfile.major,
    satScore: currentProfile.satScore,
    actScore: currentProfile.actScore,
    stateOfResidence: currentProfile.stateOfResidence,
    householdIncomeTier: currentProfile.householdIncomeTier,
    englishProficiencyScore: currentProfile.englishProficiencyScore,
    englishTestType: currentProfile.englishTestType,
    campusVibe: currentProfile.campusVibe,
    isStudentAthlete: currentProfile.isStudentAthlete,
    hasLegacyStatus: currentProfile.hasLegacyStatus,
    legacyUniversities: currentProfile.legacyUniversities,
    postGradGoal: currentProfile.postGradGoal,
    isFirstGen: currentProfile.isFirstGen,
    apClassCount: currentProfile.apClassCount,
    apClasses: currentProfile.apClasses,
  });

  // Determine if student is domestic based on citizenship
  const isDomestic = useMemo(() => {
    return ['US_CITIZEN', 'PERMANENT_RESIDENT', 'DACA'].includes(formData.citizenshipStatus || '');
  }, [formData.citizenshipStatus]);

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

  const inputClass = "w-full px-4 py-3 rounded-lg bg-zinc-900 border border-white/10 text-white focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-colors";
  const selectClass = "w-full px-4 py-3 rounded-lg bg-zinc-900 border border-white/10 text-white focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-colors appearance-none cursor-pointer";
  const labelClass = "block text-sm font-medium text-zinc-200";
  const helperClass = "text-xs text-zinc-400";

  return (
    <div className="flex-1 h-full overflow-y-auto p-12 bg-zinc-950">
      <div className="max-w-3xl mx-auto">
        <header className="mb-12">
          <h2 className="text-3xl font-bold text-white mb-2">Settings</h2>
          <p className="text-zinc-400">Manage your profile and preferences for personalized recommendations.</p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-10">
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

          {/* Section 1: Identity */}
          <section className="space-y-6">
            <div className="flex items-center gap-3 pb-2 border-b border-white/10">
              <User className="w-5 h-5 text-blue-400" />
              <h3 className="text-xl font-medium text-white">Identity</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2 md:col-span-2">
                <label htmlFor="name" className={labelClass}>
                  Name
                </label>
                <input
                  id="name"
                  type="text"
                  value={formData.name || ''}
                  onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  className={inputClass}
                  placeholder="e.g., John Smith"
                />
                <p className={helperClass}>Your name for personalized greetings (never shared with AI).</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="citizenshipStatus" className={labelClass}>
                  Citizenship Status *
                </label>
                <select
                  id="citizenshipStatus"
                  required
                  value={formData.citizenshipStatus || ''}
                  onChange={e => setFormData(prev => ({ 
                    ...prev, 
                    citizenshipStatus: e.target.value as CitizenshipStatus 
                  }))}
                  className={selectClass}
                >
                  <option value="">Select status...</option>
                  <option value="US_CITIZEN">🇺🇸 US Citizen</option>
                  <option value="PERMANENT_RESIDENT">🟢 Permanent Resident (Green Card)</option>
                  <option value="DACA">📋 DACA Recipient</option>
                  <option value="INTERNATIONAL">🌍 International Student</option>
                </select>
                <p className={helperClass}>Determines financial aid eligibility and recommendation logic.</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="nationality" className={labelClass}>
                  Nationality / Country of Origin
                </label>
                <input
                  id="nationality"
                  type="text"
                  value={formData.nationality || ''}
                  onChange={e => setFormData(prev => ({ ...prev, nationality: e.target.value }))}
                  className={inputClass}
                  placeholder="e.g., Brazil, India, Germany"
                />
                <p className={helperClass}>
                  {isDomestic ? 'Optional for domestic students.' : 'Used to check Need-Blind policies.'}
                </p>
              </div>

              {/* State of Residence - Only for domestic students */}
              {isDomestic && (
                <div className="space-y-2">
                  <label htmlFor="stateOfResidence" className={labelClass}>
                    <MapPin className="w-4 h-4 inline mr-1" />
                    State of Residence
                  </label>
                  <select
                    id="stateOfResidence"
                    value={formData.stateOfResidence || ''}
                    onChange={e => setFormData(prev => ({ ...prev, stateOfResidence: e.target.value }))}
                    className={selectClass}
                  >
                    <option value="">Select state...</option>
                    {US_STATES.map(state => (
                      <option key={state} value={state}>{state}</option>
                    ))}
                  </select>
                  <p className={helperClass}>For in-state tuition calculations.</p>
                </div>
              )}

              {/* English Proficiency - Only for international students */}
              {!isDomestic && formData.citizenshipStatus === 'INTERNATIONAL' && (
                <>
                  <div className="space-y-2">
                    <label htmlFor="englishTestType" className={labelClass}>
                      <Globe className="w-4 h-4 inline mr-1" />
                      English Test Type
                    </label>
                    <select
                      id="englishTestType"
                      value={formData.englishTestType || ''}
                      onChange={e => setFormData(prev => ({ 
                        ...prev, 
                        englishTestType: e.target.value as EnglishTestType || undefined 
                      }))}
                      className={selectClass}
                    >
                      <option value="">Select test...</option>
                      <option value="TOEFL">TOEFL iBT</option>
                      <option value="DUOLINGO">Duolingo English Test</option>
                      <option value="IELTS">IELTS</option>
                    </select>
                    <p className={helperClass}>Select the English proficiency test you took.</p>
                  </div>

                  {formData.englishTestType && (
                    <div className="space-y-2">
                      <label htmlFor="englishProficiency" className={labelClass}>
                        {formData.englishTestType === 'TOEFL' && 'TOEFL iBT Score'}
                        {formData.englishTestType === 'DUOLINGO' && 'Duolingo Score'}
                        {formData.englishTestType === 'IELTS' && 'IELTS Score'}
                      </label>
                      <input
                        id="englishProficiency"
                        type="number"
                        min="0"
                        max={formData.englishTestType === 'TOEFL' ? 120 : formData.englishTestType === 'DUOLINGO' ? 160 : 9}
                        step="1"
                        value={formData.englishProficiencyScore || ''}
                        onChange={e => setFormData(prev => ({ 
                          ...prev, 
                          englishProficiencyScore: e.target.value ? parseInt(e.target.value) : undefined 
                        }))}
                        className={inputClass}
                        placeholder={
                          formData.englishTestType === 'TOEFL' ? 'e.g., 105 (0-120)' :
                          formData.englishTestType === 'DUOLINGO' ? 'e.g., 125 (10-160)' :
                          'e.g., 7 (0-9)'
                        }
                      />
                      <p className={helperClass}>
                        {formData.englishTestType === 'TOEFL' && 'TOEFL iBT score (0-120).'}
                        {formData.englishTestType === 'DUOLINGO' && 'Duolingo score (10-160).'}
                        {formData.englishTestType === 'IELTS' && 'IELTS band score (0-9, whole numbers).'}
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          </section>

          {/* Section 2: Academic Profile */}
          <section className="space-y-6">
            <div className="flex items-center gap-3 pb-2 border-b border-white/10">
              <GraduationCap className="w-5 h-5 text-green-400" />
              <h3 className="text-xl font-medium text-white">Academic Profile</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label htmlFor="gpa" className={labelClass}>GPA (4.0 scale) *</label>
                <input
                  id="gpa"
                  type="number"
                  step="0.01"
                  min="0"
                  max="4.0"
                  required
                  value={formData.gpa || ''}
                  onChange={e => setFormData(prev => ({ ...prev, gpa: parseFloat(e.target.value) }))}
                  className={inputClass}
                  placeholder="e.g., 3.85"
                />
                <p className={helperClass}>Your unweighted high school GPA.</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="major" className={labelClass}>Intended Major *</label>
                <input
                  id="major"
                  type="text"
                  required
                  value={formData.major || ''}
                  onChange={e => setFormData(prev => ({ ...prev, major: e.target.value }))}
                  className={inputClass}
                  placeholder="e.g., Computer Science"
                />
                <p className={helperClass}>Helps find programs with strong reputation in your field.</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="satScore" className={labelClass}>SAT Score</label>
                <input
                  id="satScore"
                  type="number"
                  min="400"
                  max="1600"
                  value={formData.satScore || ''}
                  onChange={e => setFormData(prev => ({ 
                    ...prev, 
                    satScore: e.target.value ? parseInt(e.target.value) : undefined 
                  }))}
                  className={inputClass}
                  placeholder="e.g., 1480"
                />
                <p className={helperClass}>Combined SAT score (400-1600).</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="actScore" className={labelClass}>ACT Score</label>
                <input
                  id="actScore"
                  type="number"
                  min="1"
                  max="36"
                  value={formData.actScore || ''}
                  onChange={e => setFormData(prev => ({ 
                    ...prev, 
                    actScore: e.target.value ? parseInt(e.target.value) : undefined 
                  }))}
                  className={inputClass}
                  placeholder="e.g., 32"
                />
                <p className={helperClass}>Composite ACT score (1-36).</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="apClassCount" className={labelClass}>
                  <BookOpen className="w-4 h-4 inline mr-1" />
                  AP Classes Taken
                </label>
                <input
                  id="apClassCount"
                  type="number"
                  min="0"
                  max="20"
                  value={formData.apClassCount || ''}
                  onChange={e => setFormData(prev => ({ 
                    ...prev, 
                    apClassCount: e.target.value ? parseInt(e.target.value) : undefined 
                  }))}
                  className={inputClass}
                  placeholder="e.g., 8"
                />
                <p className={helperClass}>Total number of AP classes taken.</p>
              </div>

              {(formData.apClassCount ?? 0) > 0 && (
                <div className="space-y-2 md:col-span-2">
                  <label htmlFor="apClasses" className={labelClass}>
                    AP Subjects
                  </label>
                  <input
                    id="apClasses"
                    type="text"
                    value={formData.apClasses?.join(', ') || ''}
                    onChange={e => setFormData(prev => ({ 
                      ...prev, 
                      apClasses: e.target.value.split(',').map(s => s.trim()).filter(Boolean) 
                    }))}
                    className={inputClass}
                    placeholder="e.g., Calculus BC, Physics C, Computer Science A"
                  />
                  <p className={helperClass}>Enter AP subjects, comma-separated.</p>
                </div>
              )}
            </div>
          </section>

          {/* Section 3: Financial Info */}
          <section className="space-y-6">
            <div className="flex items-center gap-3 pb-2 border-b border-white/10">
              <DollarSign className="w-5 h-5 text-yellow-400" />
              <h3 className="text-xl font-medium text-white">Financial Information</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label htmlFor="incomeTier" className={labelClass}>Household Income Tier</label>
                <select
                  id="incomeTier"
                  value={formData.householdIncomeTier || ''}
                  onChange={e => setFormData(prev => ({ 
                    ...prev, 
                    householdIncomeTier: e.target.value as HouseholdIncomeTier || undefined 
                  }))}
                  className={selectClass}
                >
                  <option value="">Prefer not to say</option>
                  <option value="LOW">Low (under $60k/year)</option>
                  <option value="MEDIUM">Medium ($60k - $150k/year)</option>
                  <option value="HIGH">High (over $150k/year)</option>
                </select>
                <p className={helperClass}>
                  {isDomestic 
                    ? 'Helps estimate Pell Grant and need-based aid eligibility.' 
                    : 'Helps identify schools with strong international financial aid.'}
                </p>
              </div>
            </div>
          </section>

          {/* Section 4: Fit Preferences */}
          <section className="space-y-6">
            <div className="flex items-center gap-3 pb-2 border-b border-white/10">
              <Target className="w-5 h-5 text-purple-400" />
              <h3 className="text-xl font-medium text-white">Fit Preferences</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label htmlFor="campusVibe" className={labelClass}>Campus Vibe</label>
                <select
                  id="campusVibe"
                  value={formData.campusVibe || ''}
                  onChange={e => setFormData(prev => ({ 
                    ...prev, 
                    campusVibe: e.target.value as CampusVibe || undefined 
                  }))}
                  className={selectClass}
                >
                <option value="">No preference</option>
                  <option value="URBAN">Urban</option>
                  <option value="SUBURBAN">Suburban</option>
                  <option value="RURAL">Rural / College Town</option>
                </select>
                <p className={helperClass}>Preferred campus environment type.</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="postGradGoal" className={labelClass}>
                  <Briefcase className="w-4 h-4 inline mr-1" />
                  Post-Grad Goals
                </label>
                <select
                  id="postGradGoal"
                  value={formData.postGradGoal || ''}
                  onChange={e => setFormData(prev => ({ 
                    ...prev, 
                    postGradGoal: e.target.value as PostGradGoal || undefined 
                  }))}
                  className={selectClass}
                >
                  <option value="">No specific goal</option>
                  <option value="JOB_PLACEMENT">💼 Immediate Job Placement (Big Tech, Finance)</option>
                  <option value="GRADUATE_SCHOOL">🎓 Graduate / Professional School</option>
                  <option value="ENTREPRENEURSHIP">🚀 Entrepreneurship / Startups</option>
                  <option value="UNDECIDED">🤔 Undecided</option>
                </select>
                <p className={helperClass}>Helps prioritize schools with matching career outcomes.</p>
              </div>

              {/* Toggle fields */}
              <div className="space-y-4 md:col-span-2">
                <div className="flex items-center gap-4 p-4 bg-zinc-900/50 rounded-lg border border-white/5">
                  <Trophy className="w-5 h-5 text-orange-400" />
                  <div className="flex-1">
                    <label htmlFor="isAthlete" className="font-medium text-white">Student Athlete</label>
                    <p className={helperClass}>Seeking athletic recruitment / NCAA programs</p>
                  </div>
                  <input
                    id="isAthlete"
                    type="checkbox"
                    checked={formData.isStudentAthlete || false}
                    onChange={e => setFormData(prev => ({ ...prev, isStudentAthlete: e.target.checked }))}
                    className="w-5 h-5 rounded bg-zinc-800 border-white/20 text-blue-500 focus:ring-blue-500/50"
                  />
                </div>

                <div className="flex items-center gap-4 p-4 bg-zinc-900/50 rounded-lg border border-white/5">
                  <Users className="w-5 h-5 text-cyan-400" />
                  <div className="flex-1">
                    <label htmlFor="hasLegacy" className="font-medium text-white">Legacy Status</label>
                    <p className={helperClass}>Family member attended a university</p>
                  </div>
                  <input
                    id="hasLegacy"
                    type="checkbox"
                    checked={formData.hasLegacyStatus || false}
                    onChange={e => setFormData(prev => ({ ...prev, hasLegacyStatus: e.target.checked }))}
                    className="w-5 h-5 rounded bg-zinc-800 border-white/20 text-blue-500 focus:ring-blue-500/50"
                  />
                </div>

                <div className="flex items-center gap-4 p-4 bg-zinc-900/50 rounded-lg border border-white/5">
                  <GraduationCap className="w-5 h-5 text-emerald-400" />
                  <div className="flex-1">
                    <label htmlFor="isFirstGen" className="font-medium text-white">First-Generation Student</label>
                    <p className={helperClass}>First in family to attend college</p>
                  </div>
                  <input
                    id="isFirstGen"
                    type="checkbox"
                    checked={formData.isFirstGen || false}
                    onChange={e => setFormData(prev => ({ ...prev, isFirstGen: e.target.checked }))}
                    className="w-5 h-5 rounded bg-zinc-800 border-white/20 text-blue-500 focus:ring-blue-500/50"
                  />
                </div>

                {/* Legacy Universities input */}
                {formData.hasLegacyStatus && (
                  <div className="space-y-2 pl-9">
                    <label htmlFor="legacyUniversities" className={labelClass}>
                      Legacy Universities
                    </label>
                    <input
                      id="legacyUniversities"
                      type="text"
                      value={formData.legacyUniversities?.join(', ') || ''}
                      onChange={e => setFormData(prev => ({ 
                        ...prev, 
                        legacyUniversities: e.target.value.split(',').map(s => s.trim()).filter(Boolean) 
                      }))}
                      className={inputClass}
                      placeholder="e.g., Harvard, Stanford (comma-separated)"
                    />
                    <p className={helperClass}>Enter universities where you have legacy connections.</p>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Submit Button */}
          <div className="pt-6 border-t border-white/10 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="px-8 py-3 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Saving Changes...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
