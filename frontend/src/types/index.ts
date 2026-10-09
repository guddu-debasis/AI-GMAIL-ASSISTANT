export type Category = 
  | 'job_recruitment' 
  | 'financial' 
  | 'legal_contractual' 
  | 'complaint_sensitive' 
  | 'general' 
  | 'other';

export type RiskLevel = 'low' | 'medium' | 'high' | 'uncertain';

export type DraftStatus = 
  | 'PROCESSING'
  | 'PENDING_APPROVAL'
  | 'DRAFT_READY'
  | 'APPROVED'
  | 'REJECTED'
  | 'SENDING'
  | 'SENT'
  | 'SEND_FAILED'
  | 'SEND_UNKNOWN'
  | 'EXPIRED';

export interface Classification {
  id: string;
  email_id: string;
  category: Category;
  risk_level: RiskLevel;
  confidence: number;
  rationale: string;
  reasons: string[];
  requires_approval: boolean;
  policy_version: number;
  created_at: string;
}

export interface ReplyDraft {
  id: string;
  email_id: string;
  body: string;
  status: DraftStatus;
  version: number;
  content_hash: string;
  policy_version: number;
  approved_by?: string;
  approved_at?: string;
  approved_content_hash?: string;
  gmail_draft_id?: string;
  gmail_sent_message_id?: string;
  sent_at?: string;
  created_at: string;
  updated_at: string;
}

export interface EmailItem {
  id: string;
  user_id: string;
  gmail_account_id: string;
  gmail_message_id: string;
  gmail_thread_id: string;
  sender: string;
  subject?: string;
  body_text?: string;
  received_at?: string;
  is_starred: boolean;
  processing_status: string;
  created_at: string;
  classification?: Classification;
  reply_draft?: ReplyDraft;
}

export interface ApprovalQueueItem {
  draft_id: string;
  email_id: string;
  email_subject?: string;
  email_sender: string;
  email_received_at?: string;
  email_body?: string;
  is_starred: boolean;
  category: Category;
  risk_level: RiskLevel;
  confidence: number;
  reasons: string[];
  draft_body: string;
  draft_version: number;
  draft_status: DraftStatus;
  content_hash: string;
  created_at: string;
}

export interface UserSettings {
  user_id: string;
  approval_categories: string[];
  approve_when_uncertain: boolean;
  approve_starred: boolean;
  allow_auto_send: boolean;
  min_confidence: number;
  policy_version: number;
  created_at: string;
  updated_at: string;
}

export interface VIPSender {
  id: string;
  user_id: string;
  email_address: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  draft_id: string;
  user_id: string;
  event_type: string;
  draft_version: number;
  content_hash?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface GmailStatus {
  connected: boolean;
  status: string;
  gmail_address?: string;
  message?: string;
  connected_at?: string;
}
