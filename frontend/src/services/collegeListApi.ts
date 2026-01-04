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

export interface Exclusion {
    id: string;
    college_name: string;
    reason: string | null;
    created_at: string;
}

/**
 * Get the user's saved college list
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
