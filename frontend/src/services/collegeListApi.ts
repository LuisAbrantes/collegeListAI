/**
 * API service for College List and Exclusions
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface CollegeListItem {
    id: string;
    college_name: string;
    label: 'reach' | 'target' | 'safety' | null;
    notes: string | null;
    added_at: string;
}

/**
 * Enriched college list item for spreadsheet view.
 * Combines user's list data with institutional data.
 */
export interface CollegeListDetailedItem {
    // User list data
    id: string;
    college_name: string;
    label: 'reach' | 'target' | 'safety' | null;
    notes: string | null;
    added_at: string;
    // Institutional data
    acceptance_rate: number | null;
    sat_25th: number | null;
    sat_75th: number | null;
    act_25th: number | null;
    act_75th: number | null;
    tuition_international: number | null;
    need_blind_international: boolean | null;
    meets_full_need: boolean | null;
    city: string | null;
    state: string | null;
    campus_setting: string | null;
    student_size: number | null;
}

export interface Exclusion {
    id: string;
    college_name: string;
    reason: string | null;
    created_at: string;
}

/**
 * Get the user's saved college list (basic)
 */
export async function getCollegeList(token: string): Promise<CollegeListItem[]> {
    const response = await fetch(`${API_BASE}/api/college-list`, {
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error('Failed to fetch college list');
    }

    return response.json();
}

/**
 * Get the user's saved college list with full institutional data.
 * Used for spreadsheet-like view.
 */
export async function getCollegeListDetailed(token: string): Promise<CollegeListDetailedItem[]> {
    const response = await fetch(`${API_BASE}/api/college-list/detailed`, {
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error('Failed to fetch detailed college list');
    }

    return response.json();
}

/**
 * Add a college to the user's list
 */
export async function addToCollegeList(
    token: string,
    collegeName: string,
    label?: string,
    notes?: string
): Promise<CollegeListItem> {
    const response = await fetch(`${API_BASE}/api/college-list`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            college_name: collegeName,
            label,
            notes,
        }),
    });

    if (!response.ok) {
        throw new Error('Failed to add college to list');
    }

    return response.json();
}

/**
 * Remove a college from the user's list
 */
export async function removeFromCollegeList(
    token: string,
    collegeName: string
): Promise<void> {
    const response = await fetch(
        `${API_BASE}/api/college-list/${encodeURIComponent(collegeName)}`,
        {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        }
    );

    if (!response.ok && response.status !== 404) {
        throw new Error('Failed to remove college from list');
    }
}

/**
 * Get the user's exclusions
 */
export async function getExclusions(token: string): Promise<Exclusion[]> {
    const response = await fetch(`${API_BASE}/api/exclusions`, {
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    });

    if (!response.ok) {
        throw new Error('Failed to fetch exclusions');
    }

    return response.json();
}

/**
 * Exclude a college from future recommendations
 */
export async function excludeCollege(
    token: string,
    collegeName: string,
    reason?: string
): Promise<Exclusion> {
    const response = await fetch(`${API_BASE}/api/exclusions`, {
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

    if (!response.ok) {
        throw new Error('Failed to exclude college');
    }

    return response.json();
}

/**
 * Remove an exclusion
 */
export async function removeExclusion(
    token: string,
    collegeName: string
): Promise<void> {
    const response = await fetch(
        `${API_BASE}/api/exclusions/${encodeURIComponent(collegeName)}`,
        {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        }
    );

    if (!response.ok && response.status !== 404) {
        throw new Error('Failed to remove exclusion');
    }
}
