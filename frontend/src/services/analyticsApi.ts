/**
 * Analytics API service
 * 
 * Tracks user behavior for data flywheel optimization.
 * All tracking calls are fire-and-forget (non-blocking).
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Track a search event
 */
export async function trackSearch(
    token: string,
    query: string,
    resultsCount: number,
    major?: string
): Promise<void> {
    try {
        await fetch(`${API_BASE}/api/analytics/track/search`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query,
                results_count: resultsCount,
                major,
            }),
        });
    } catch {
        // Analytics should never block UX - fail silently
        console.debug('[Analytics] Failed to track search');
    }
}

/**
 * Track when user views a college recommendation
 */
export async function trackRecommendationView(
    token: string,
    collegeName: string,
    position: number,
    label?: string
): Promise<void> {
    try {
        await fetch(`${API_BASE}/api/analytics/track/view`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                college_name: collegeName,
                position,
                label,
            }),
        });
    } catch {
        console.debug('[Analytics] Failed to track view');
    }
}

/**
 * Track when user adds a college to their list
 */
export async function trackListAdd(
    token: string,
    collegeName: string,
    label?: string
): Promise<void> {
    try {
        await fetch(`${API_BASE}/api/analytics/track/add`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                college_name: collegeName,
                label,
            }),
        });
    } catch {
        console.debug('[Analytics] Failed to track add');
    }
}

/**
 * Track when user rejects/excludes a college
 */
export async function trackRejection(
    token: string,
    collegeName: string,
    reason?: string
): Promise<void> {
    try {
        await fetch(`${API_BASE}/api/analytics/track/reject`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                college_name: collegeName,
                reason,
            }),
        });
    } catch {
        console.debug('[Analytics] Failed to track rejection');
    }
}

export type OutcomeStatus = 'applied' | 'accepted' | 'rejected' | 'waitlisted' | 'deferred' | 'enrolled';

/**
 * Record an application outcome
 */
export async function recordOutcome(
    token: string,
    collegeName: string,
    outcomeStatus: OutcomeStatus,
    cycleYear: number,
    predictedLabel?: string
): Promise<void> {
    const response = await fetch(`${API_BASE}/api/analytics/outcomes`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            college_name: collegeName,
            outcome_status: outcomeStatus,
            cycle_year: cycleYear,
            predicted_label: predictedLabel,
        }),
    });

    if (!response.ok) {
        throw new Error('Failed to record outcome');
    }
}

export interface ApplicationOutcome {
    id: string;
    college_name: string;
    outcome_status: OutcomeStatus;
    cycle_year: number;
    predicted_label: string | null;
    created_at: string;
}

/**
 * Get user's recorded outcomes
 */
export async function getOutcomes(token: string): Promise<ApplicationOutcome[]> {
    const response = await fetch(`${API_BASE}/api/analytics/outcomes`, {
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error('Failed to fetch outcomes');
    }

    return response.json();
}
