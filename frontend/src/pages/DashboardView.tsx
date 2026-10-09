import React from 'react';
import { 
  CheckCircle2, 
  Clock, 
  Mail, 
  ShieldAlert, 
  ArrowRight, 
  Sparkles,
  Lock
} from 'lucide-react';
import type { EmailItem, ApprovalQueueItem } from '../types';

interface DashboardViewProps {
  emails: EmailItem[];
  approvals: ApprovalQueueItem[];
  onNavigateToApprovals: () => void;
  onNavigateToSettings: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  emails,
  approvals,
  onNavigateToApprovals,
  onNavigateToSettings,
}) => {
  const pendingApprovalsCount = approvals.filter(a => a.draft_status === 'PENDING_APPROVAL').length;
  const draftsReadyCount = approvals.filter(a => a.draft_status === 'DRAFT_READY').length;
  const sentCount = emails.filter(e => e.reply_draft?.status === 'SENT').length;

  return (
    <div style={{ padding: '0 24px 32px' }}>
      {/* Safety Posture Alert Banner */}
      <div className="glass-panel" style={{ 
        padding: '16px 20px', 
        marginBottom: '24px', 
        borderColor: 'rgba(99, 102, 241, 0.3)',
        background: 'linear-gradient(90deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ 
            padding: '8px', 
            borderRadius: '10px', 
            background: 'rgba(99, 102, 241, 0.2)',
            color: '#818cf8' 
          }}>
            <Lock size={20} />
          </div>
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#e0e7ff' }}>
              Safety Invariant Active: Autonomous Sending Disabled
            </h4>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
              Replies are prepared as drafts. No email will ever be sent without explicit user authorization for the exact content hash.
            </p>
          </div>
        </div>
        <button 
          className="btn btn-secondary" 
          onClick={onNavigateToSettings}
          style={{ fontSize: '0.8rem' }}
        >
          Inspect Policies <ArrowRight size={14} />
        </button>
      </div>

      {/* Metrics Grid */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', 
        gap: '16px', 
        marginBottom: '28px' 
      }}>
        {/* Metric 1 */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Action Required
            </span>
            <span style={{ padding: '6px', borderRadius: '8px', background: 'rgba(244, 63, 94, 0.15)', color: '#fb7185' }}>
              <ShieldAlert size={18} />
            </span>
          </div>
          <div style={{ fontSize: '1.875rem', fontWeight: 700, color: '#f8fafc', marginBottom: '4px' }}>
            {pendingApprovalsCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#fb7185' }}>
            Pending Human Approval
          </span>
        </div>

        {/* Metric 2 */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Drafts Ready
            </span>
            <span style={{ padding: '6px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>
              <Clock size={18} />
            </span>
          </div>
          <div style={{ fontSize: '1.875rem', fontWeight: 700, color: '#f8fafc', marginBottom: '4px' }}>
            {draftsReadyCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#a5b4fc' }}>
            Prepared AI Proposals
          </span>
        </div>

        {/* Metric 3 */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Processed Messages
            </span>
            <span style={{ padding: '6px', borderRadius: '8px', background: 'rgba(6, 182, 212, 0.15)', color: '#22d3ee' }}>
              <Mail size={18} />
            </span>
          </div>
          <div style={{ fontSize: '1.875rem', fontWeight: 700, color: '#f8fafc', marginBottom: '4px' }}>
            {emails.length}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#67e8f9' }}>
            Total Ingested Threads
          </span>
        </div>

        {/* Metric 4 */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              Sent Dispatches
            </span>
            <span style={{ padding: '6px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
              <CheckCircle2 size={18} />
            </span>
          </div>
          <div style={{ fontSize: '1.875rem', fontWeight: 700, color: '#f8fafc', marginBottom: '4px' }}>
            {sentCount}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#34d399' }}>
            Authorized & Sent
          </span>
        </div>
      </div>

      {/* Immediate Attention Queue */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#ffffff' }}>
              Items Requiring Human Authorization
            </h3>
            <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
              High-risk categories, VIP senders, starred items, or uncertain classifications
            </p>
          </div>
          {approvals.length > 0 && (
            <button 
              className="btn btn-primary" 
              onClick={onNavigateToApprovals}
              id="view-full-queue-button"
            >
              Open Full Queue ({approvals.length}) <ArrowRight size={15} />
            </button>
          )}
        </div>

        {approvals.length === 0 ? (
          <div style={{ 
            textAlign: 'center', 
            padding: '48px 24px', 
            color: 'var(--text-dim)',
            background: 'rgba(0, 0, 0, 0.15)',
            borderRadius: '12px' 
          }}>
            <Sparkles size={36} style={{ margin: '0 auto 12px', opacity: 0.5, color: '#818cf8' }} />
            <h4 style={{ color: '#cbd5e1', fontWeight: 500, marginBottom: '6px' }}>Queue is Clear</h4>
            <p style={{ fontSize: '0.85rem' }}>
              No emails are currently waiting for approval. Click "Sync Inbox" in the header to check for new messages.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {approvals.slice(0, 3).map((item) => (
              <div 
                key={item.draft_id}
                style={{
                  padding: '16px 20px',
                  borderRadius: '12px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                  flexWrap: 'wrap'
                }}
              >
                <div style={{ maxWidth: '65%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span className={`badge badge-risk-${item.risk_level}`}>
                      {item.risk_level} risk
                    </span>
                    <span className="badge badge-status">
                      {item.category.replace('_', ' ')}
                    </span>
                    {item.is_starred && (
                      <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24' }}>
                        Starred
                      </span>
                    )}
                  </div>
                  <h4 style={{ fontSize: '0.925rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '4px' }}>
                    {item.email_subject || '(No Subject)'}
                  </h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    From: {item.email_sender}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button 
                    className="btn btn-secondary" 
                    onClick={onNavigateToApprovals}
                    style={{ fontSize: '0.8rem' }}
                  >
                    Review Proposal
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
