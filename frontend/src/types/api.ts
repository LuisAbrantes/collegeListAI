/**
 * College List AI - API Types
 *
 * Strict TypeScript types for all API interactions.
 * These types match the backend Pydantic models exactly.
 */

// ============================================================================
// Enums
// ============================================================================

/**
 * College classification based on admission probability
 */
export type CollegeLabel = 'Reach' | 'Target' | 'Safety';

/**
 * Student citizenship/residency status for financial aid determination
 */
export type CitizenshipStatus = 'US_CITIZEN' | 'PERMANENT_RESIDENT' | 'INTERNATIONAL' | 'DACA';

/**
 * Income tier for financial aid estimation
 */
export type HouseholdIncomeTier = 'LOW' | 'MEDIUM' | 'HIGH';

/**
 * Preferred campus environment type
 */
export type CampusVibe = 'URBAN' | 'SUBURBAN' | 'RURAL';

/**
 * Post-graduation career focus
 */
export type PostGradGoal = 'JOB_PLACEMENT' | 'GRADUATE_SCHOOL' | 'ENTREPRENEURSHIP' | 'UNDECIDED';

/**
 * English proficiency test type
 */
export type EnglishTestType = 'TOEFL' | 'DUOLINGO' | 'IELTS';

// ============================================================================
// User Profile Types
// ============================================================================

/**
 * Request body for creating a new user profile
 */
export interface UserProfileCreate {
  /** Student's citizenship/residency status (required) */
  citizenshipStatus: CitizenshipStatus;
  /** Country of citizenship (optional context) */
  nationality?: string;
  /** GPA on 4.0 scale (0.0 - 4.0) */
  gpa: number;
  /** Intended major/field of study (2-100 chars) */
  major: string;
  /** SAT score (400-1600) */
  satScore?: number;
  /** ACT score (1-36) */
  actScore?: number;
  /** State for in-state tuition (US residents only) */
  stateOfResidence?: string;
  /** Income tier for aid estimation */
  householdIncomeTier?: HouseholdIncomeTier;
  /** TOEFL/IELTS score (internationals) */
  englishProficiencyScore?: number;
  /** Preferred campus environment */
  campusVibe?: CampusVibe;
  /** Pursuing athletic recruitment */
  isStudentAthlete?: boolean;
  /** Has family alumni connections */
  hasLegacyStatus?: boolean;
  /** Universities with legacy status */
  legacyUniversities?: string[];
  /** Post-graduation career focus */
  postGradGoal?: PostGradGoal;
  /** First-generation college student */
  isFirstGen?: boolean;
  /** Type of English proficiency test */
  englishTestType?: EnglishTestType;
  /** Number of AP classes taken */
  apClassCount?: number;
  /** List of AP subjects */
  apClasses?: string[];
}

/**
 * Request body for updating an existing profile (partial)
 */
export interface UserProfileUpdate {
  citizenshipStatus?: CitizenshipStatus;
  nationality?: string;
  gpa?: number;
  major?: string;
  satScore?: number;
  actScore?: number;
  stateOfResidence?: string;
  householdIncomeTier?: HouseholdIncomeTier;
  englishProficiencyScore?: number;
  campusVibe?: CampusVibe;
  isStudentAthlete?: boolean;
  hasLegacyStatus?: boolean;
  legacyUniversities?: string[];
  postGradGoal?: PostGradGoal;
  isFirstGen?: boolean;
  englishTestType?: EnglishTestType;
  apClassCount?: number;
  apClasses?: string[];
}

/**
 * Complete user profile entity from database
 */
export interface UserProfile {
  id: string;
  userId: string;
  /** Student's citizenship/residency status */
  citizenshipStatus?: CitizenshipStatus;
  nationality?: string;
  gpa: number;
  major: string;
  satScore?: number;
  actScore?: number;
  stateOfResidence?: string;
  householdIncomeTier?: HouseholdIncomeTier;
  englishProficiencyScore?: number;
  campusVibe?: CampusVibe;
  isStudentAthlete: boolean;
  hasLegacyStatus: boolean;
  legacyUniversities?: string[];
  postGradGoal?: PostGradGoal;
  isFirstGen: boolean;
  englishTestType?: EnglishTestType;
  apClassCount?: number;
  apClasses?: string[];
  createdAt: string;
  updatedAt: string;
}

// ============================================================================
// College Types
// ============================================================================

/**
 * Extended metadata for a college
 */
export interface CollegeMetadata {
  acceptanceRate?: number;
  needBlindCountries?: string[];
  needAwareCountries?: string[];
  applicationDeadline?: string;
  financialAidAvailable: boolean;
  avgSat?: number;
  avgGpa?: number;
}

/**
 * College entity from cache
 */
export interface College {
  id: string;
  name: string;
  metadata?: CollegeMetadata;
  createdAt: string;
}

/**
 * Result from vector similarity search
 */
export interface CollegeSearchResult {
  id: string;
  name: string;
  metadata?: CollegeMetadata;
  /** Cosine similarity score (0.0 - 1.0) */
  similarity: number;
}

/**
 * AI-generated college recommendation
 */
export interface CollegeRecommendation {
  id: string;
  name: string;
  label: CollegeLabel;
  /** Match score (0-100) based on profile fit */
  matchScore: number;
  /** Personalized explanation of fit */
  reasoning: string;
  /** Financial aid info specific to nationality */
  financialAidSummary: string;
  /** Verified 2025 admission page URLs */
  officialLinks: string[];
}

// ============================================================================
// User Exclusion Types
// ============================================================================

/**
 * User's blacklisted college
 */
export interface UserExclusion {
  id: string;
  userId: string;
  collegeId: string;
  createdAt: string;
}

/**
 * Request to add a college to exclusion list
 */
export interface CreateExclusionRequest {
  collegeId: string;
}

// ============================================================================
// API Response Wrappers
// ============================================================================

/**
 * Standard API error structure
 */
export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
}

/**
 * Paginated API response
 */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

// ============================================================================
// Search & Recommendation Request Types
// ============================================================================

/**
 * Request for college recommendations
 */
export interface RecommendationRequest {
  /** Natural language query */
  query: string;
  /** Override profile values (optional) */
  profileOverrides?: Partial<UserProfileCreate>;
  /** Number of recommendations to return */
  limit?: number;
}

/**
 * Response containing college recommendations
 */
export interface RecommendationResponse {
  recommendations: CollegeRecommendation[];
  /** Search metadata */
  meta: {
    queryTime: number;
    totalMatches: number;
    model: string;
  };
}

// ============================================================================
// SSE Event Types (for streaming responses)
// ============================================================================

/**
 * Server-Sent Event types
 */
export type SSEEventType =
  | 'chunk'
  | 'recommendation'
  | 'complete'
  | 'error';

/**
 * SSE event payload
 */
export interface SSEEvent<T = unknown> {
  type: SSEEventType;
  data: T;
  timestamp: string;
}

/**
 * Chunk event for streaming text
 */
export interface SSEChunkEvent extends SSEEvent<{ text: string }> {
  type: 'chunk';
}

/**
 * Recommendation event for streaming results
 */
export interface SSERecommendationEvent extends SSEEvent<CollegeRecommendation> {
  type: 'recommendation';
}

// ============================================================================
// Conversation/Thread Types
// ============================================================================

/**
 * Chat message in a conversation thread
 */
export interface ChatMessage {
  id: string;
  threadId: string;
  role: 'user' | 'assistant';
  content: string;
  /** Attached recommendations if any */
  recommendations?: CollegeRecommendation[];
  createdAt: string;
}

/**
 * Conversation thread
 */
export interface ConversationThread {
  id: string;
  userId: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Type guard to check if a response has an error
 */
export function hasError<T>(
  response: ApiResponse<T>
): response is ApiResponse<T> & { error: ApiError } {
  return response.error !== null;
}

/**
 * Type guard to check if a response has data
 */
export function hasData<T>(
  response: ApiResponse<T>
): response is ApiResponse<T> & { data: T } {
  return response.data !== null;
}

/**
 * Type guard for CollegeLabel
 */
export function isCollegeLabel(value: string): value is CollegeLabel {
  return ['Reach', 'Target', 'Safety'].includes(value);
}
