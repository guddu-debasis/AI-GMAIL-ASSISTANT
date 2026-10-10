import type { 
  EmailItem, 
  ApprovalQueueItem, 
  UserSettings, 
  VIPSender, 
  AuditEvent, 
  GmailStatus,
  ReplyDraft 
} from '../types';
import type { AuthUser } from '../types/auth';

const API_ROOT: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const API_BASE = `${API_ROOT}/api/v1`;

// Clerk's getToken() only exists inside React components (the useAuth hook).
// App.tsx hands it to us here, so every request can carry a fresh session token.
type TokenGetter = () => Promise<string | null>;
let tokenGetter: TokenGetter | null = null;

export function setTokenGetter(getter: TokenGetter | null): void {
  tokenGetter = getter;
}

function extractErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      // FastAPI validation errors: [{ msg: "..." }, ...]
      const messages = detail
        .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : ''))
        .filter(Boolean);
      if (messages.length > 0) return messages.join('. ');
    }
  }
  return fallback;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  base: string = API_BASE,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string> | undefined) || {}),
  };

  if (tokenGetter) {
    try {
      const token = await tokenGetter();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    } catch {
      // no token available, the server will answer 401 and the UI will show it
    }
  }

  let res: Response;
  try {
    res = await fetch(`${base}${endpoint}`, { ...options, headers });
  } catch {
    throw new Error(`Cannot reach the server at ${API_ROOT}. Is the backend running?`);
  }

  if (!res.ok) {
    const text = await res.text();
    let parsed: unknown = null;
    try {
      parsed = JSON.parse(text);
    } catch {
      // not JSON, fall back to raw text
    }
    throw new Error(extractErrorMessage(parsed, text || 'An error occurred'));
  }

  return res.json();
}

export const api = {
  // Auth: sign in and sign up happen in Clerk. This only asks our backend "who am I".
  // The first call after a new sign up also creates the local user row.
  me: () => request<AuthUser>('/auth/me', {}, API_ROOT),

  // Gmail
  getGmailStatus: () => request<GmailStatus>('/gmail/status'),
  getGoogleAuthUrl: () => request<{ auth_url?: string; message?: string }>('/auth/google/start', {}, API_ROOT),
  syncInbox: () => request<{ message: string; synced_count: number; drafted_count: number }>('/gmail/sync', { method: 'POST' }),

  // Emails
  getEmails: (params?: { category?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.category) q.append('category', params.category);
    if (params?.status) q.append('status', params.status);
    const qs = q.toString() ? `?${q.toString()}` : '';
    return request<EmailItem[]>(`/emails${qs}`);
  },
  getEmailDetail: (emailId: string) => request<EmailItem>(`/emails/${emailId}`),

  // Approvals
  getApprovalQueue: () => request<ApprovalQueueItem[]>('/approvals'),
  approveAndSend: (draftId: string, payload?: { comment?: string }) =>
    request<ReplyDraft>(`/approvals/${draftId}/approve?auto_send=true`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }),
  rejectDraft: (draftId: string, payload?: { reason?: string }) =>
    request<ReplyDraft>(`/approvals/${draftId}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }),

  // Drafts
  updateDraft: (draftId: string, body: string) =>
    request<ReplyDraft>(`/drafts/${draftId}`, {
      method: 'PATCH',
      body: JSON.stringify({ body }),
    }),
  sendDraft: (draftId: string) =>
    request<ReplyDraft>(`/drafts/${draftId}/send`, {
      method: 'POST',
    }),

  // Settings
  getSettings: () => request<UserSettings>('/settings'),
  updateSettings: (updates: Partial<UserSettings>) =>
    request<UserSettings>('/settings', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    }),
  getVIPSenders: () => request<VIPSender[]>('/settings/vip-senders'),
  addVIPSender: (email_address: string) =>
    request<VIPSender>('/settings/vip-senders', {
      method: 'POST',
      body: JSON.stringify({ email_address }),
    }),
  deleteVIPSender: (vipId: string) =>
    request<{ message: string }>(`/settings/vip-senders/${vipId}`, {
      method: 'DELETE',
    }),

  // Audit Events
  getAuditEvents: () => request<AuditEvent[]>('/audit-events'),
};
