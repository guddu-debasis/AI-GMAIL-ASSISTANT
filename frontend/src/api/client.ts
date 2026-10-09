import type { 
  EmailItem, 
  ApprovalQueueItem, 
  UserSettings, 
  VIPSender, 
  AuditEvent, 
  GmailStatus,
  ReplyDraft 
} from '../types';

const API_BASE = 'http://localhost:8000/api/v1';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      'X-User-Email': 'demo.user@example.com',
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    let errorMsg = 'An error occurred';
    try {
      const errJson = await res.json();
      errorMsg = errJson.detail || JSON.stringify(errJson);
    } catch {
      errorMsg = await res.text();
    }
    throw new Error(errorMsg);
  }

  return res.json();
}

export const api = {
  // Gmail
  getGmailStatus: () => request<GmailStatus>('/gmail/status'),
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
