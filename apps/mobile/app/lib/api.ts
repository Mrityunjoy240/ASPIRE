import {
    StudentSelfResponse,
    StudentCaseResponse,
    StudentDecisionRequest,
    StudentDecisionResponse
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function fetchStudentProfile(): Promise<StudentSelfResponse> {
    const res = await fetch(`${API_BASE}/students/me`);
    if (!res.ok) throw new Error('Failed to fetch profile');
    return res.json();
}

export async function fetchStudentCase(): Promise<StudentCaseResponse | null> {
    const res = await fetch(`${API_BASE}/students/me/case`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error('Failed to fetch case');
    return res.json();
}

export async function respondToCase(payload: StudentDecisionRequest): Promise<StudentDecisionResponse> {
    const res = await fetch(`${API_BASE}/students/me/case/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to respond to case');
    }
    return res.json();
}
