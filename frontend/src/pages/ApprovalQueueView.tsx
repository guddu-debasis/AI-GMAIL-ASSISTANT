import React, { useState } from 'react';
import { 
  X, 
  Edit3, 
  Send, 
  Hash, 
  AlertCircle,
  Search,
  CheckCircle,
  Sparkles
} from 'lucide-react';
import type { ApprovalQueueItem } from '../types';
import { api } from '../api/client';

interface ApprovalQueueViewProps {
  items: ApprovalQueueItem[];
  onRefresh: () => void;
}

export const ApprovalQueueView: React.FC<ApprovalQueueViewProps> = ({
  items,
  onRefresh,
}) => {
  const [selectedItem, setSelectedItem] = useState<ApprovalQueueItem | null>(items[0] || null);
  const [editingDraftId, setEditingDraftId] = useState<string | null>(null);
  const [draftText, setDraftText] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [riskFilter, setRiskFilter] = useState('all');
  const [actionLoading, setActionLoading] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Sync selected item when items update
  React.useEffect(() => {
    if (!selectedItem && items.length > 0) {
      setSelectedItem(items[0]);
    } else if (selectedItem) {
      const match = items.find(i => i.draft_id === selectedItem.draft_id);
      if (match) setSelectedItem(match);
    }
  }, [items]);

  const filteredItems = items.filter((item) => {
    const matchesSearch = 
      (item.email_subject || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.email_sender.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || item.category === categoryFilter;
    const matchesRisk = riskFilter === 'all' || item.risk_level === riskFilter;
    return matchesSearch && matchesCategory && matchesRisk;
  });

  const handleStartEdit = (item: ApprovalQueueItem) => {
    setEditingDraftId(item.draft_id);
    setDraftText(item.draft_body);
  };

  const handleSaveDraft = async (draftId: string) => {
    setActionLoading(true);
    try {
      await api.updateDraft(draftId, draftText);
      setEditingDraftId(null);
      setFeedbackMessage({ 
        type: 'success', 
        text: 'Draft updated. Notice: Version incremented and approval invalidated as per policy.' 
      });
      onRefresh();
    } catch (err: any) {
      setFeedbackMessage({ type: 'error', text: err.message || 'Failed to update draft' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleApproveAndSend = async (item: ApprovalQueueItem) => {
    if (!confirm(`Are you sure you want to approve and immediately send this reply to ${item.email_sender}?`)) {
      return;
    }
    setActionLoading(true);
    setFeedbackMessage(null);
    try {
      await api.approveAndSend(item.draft_id);
      setFeedbackMessage({ 
        type: 'success', 
        text: `Draft approved and successfully sent to ${item.email_sender}!` 
      });
      onRefresh();
    } catch (err: any) {
      setFeedbackMessage({ type: 'error', text: `Send failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (draftId: string) => {
    const reason = prompt('Enter a reason for rejection:', 'Not relevant / No reply required');
    if (reason === null) return;
    setActionLoading(true);
    try {
      await api.rejectDraft(draftId, { reason });
      setFeedbackMessage({ type: 'success', text: 'Draft proposal rejected and dismissed.' });
      onRefresh();
    } catch (err: any) {
      setFeedbackMessage({ type: 'error', text: `Rejection failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div style={{ padding: '0 24px 32px' }}>
      {/* Toast Feedback */}
      {feedbackMessage && (
        <div style={{
          padding: '12px 18px',
          marginBottom: '20px',
          borderRadius: '12px',
          background: feedbackMessage.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
          border: `1px solid ${feedbackMessage.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
          color: feedbackMessage.type === 'success' ? '#34d399' : '#fb7185',
          fontSize: '0.875rem',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          {feedbackMessage.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          <span>{feedbackMessage.text}</span>
          <button 
            onClick={() => setFeedbackMessage(null)} 
            style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '20px', display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '240px' }}>
          <Search size={16} color="var(--text-dim)" />
          <input
            type="text"
            placeholder="Search by sender or subject..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#ffffff',
              fontSize: '0.875rem',
              width: '100%'
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{
              background: 'rgba(0, 0, 0, 0.25)',
              border: '1px solid var(--border-subtle)',
              color: '#ffffff',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '0.8rem',
              outline: 'none'
            }}
          >
            <option value="all">All Categories</option>
            <option value="job_recruitment">Job / Recruiters</option>
            <option value="financial">Financial / Invoices</option>
            <option value="legal_contractual">Legal / Contracts</option>
            <option value="complaint_sensitive">Complaints / Sensitive</option>
            <option value="general">General</option>
          </select>

          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            style={{
              background: 'rgba(0, 0, 0, 0.25)',
              border: '1px solid var(--border-subtle)',
              color: '#ffffff',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '0.8rem',
              outline: 'none'
            }}
          >
            <option value="all">All Risk Levels</option>
            <option value="high">High Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="low">Low Risk</option>
            <option value="uncertain">Uncertain</option>
          </select>
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <div className="glass-panel" style={{ padding: '64px 24px', textAlign: 'center', color: 'var(--text-dim)' }}>
          <Sparkles size={40} style={{ margin: '0 auto 12px', color: '#818cf8', opacity: 0.6 }} />
          <h3 style={{ color: '#e2e8f0', marginBottom: '6px' }}>No Approvals in Queue</h3>
          <p style={{ fontSize: '0.875rem' }}>All review items have been resolved or filtered out.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 360px) 1fr', gap: '20px' }}>
          {/* List Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '780px', overflowY: 'auto', paddingRight: '4px' }}>
            {filteredItems.map((item) => {
              const isSelected = selectedItem?.draft_id === item.draft_id;
              return (
                <div
                  key={item.draft_id}
                  onClick={() => setSelectedItem(item)}
                  className="glass-panel"
                  style={{
                    padding: '16px',
                    cursor: 'pointer',
                    borderRadius: '12px',
                    borderColor: isSelected ? 'var(--accent-indigo)' : 'var(--border-subtle)',
                    background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'var(--bg-card)',
                    transform: isSelected ? 'translateX(3px)' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span className={`badge badge-risk-${item.risk_level}`}>
                      {item.risk_level}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      v{item.draft_version}
                    </span>
                  </div>
                  <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.email_subject || '(No Subject)'}
                  </h4>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.email_sender}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Active Review & Authorization Pane */}
          {selectedItem && (
            <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              {/* Header Info */}
              <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '10px' }}>
                  <div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff', marginBottom: '6px' }}>
                      {selectedItem.email_subject || '(No Subject)'}
                    </h2>
                    <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
                      From: <strong style={{ color: '#e2e8f0' }}>{selectedItem.email_sender}</strong>
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span className={`badge badge-risk-${selectedItem.risk_level}`}>
                      {selectedItem.risk_level} risk
                    </span>
                    <span className="badge badge-status">
                      {selectedItem.category.replace('_', ' ')}
                    </span>
                    <span className="badge badge-status">
                      Confidence: {Math.round(selectedItem.confidence * 100)}%
                    </span>
                  </div>
                </div>

                {/* Policy reasons tags */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Policy flags:</span>
                  {selectedItem.reasons.map((r) => (
                    <span key={r} className="badge" style={{ background: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', fontSize: '0.7rem' }}>
                      {r.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              </div>

              {/* Split Content: Original vs Proposed Draft */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                {/* Original Message */}
                <div style={{ 
                  background: 'rgba(0, 0, 0, 0.25)', 
                  padding: '16px', 
                  borderRadius: '12px',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column'
                }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '10px' }}>
                    Original Inbound Message
                  </div>
                  <div style={{ 
                    fontSize: '0.85rem', 
                    color: '#cbd5e1', 
                    lineHeight: '1.6', 
                    whiteSpace: 'pre-wrap', 
                    overflowY: 'auto',
                    maxHeight: '340px' 
                  }}>
                    {selectedItem.email_body || 'No body text'}
                  </div>
                </div>

                {/* Proposed Reply Draft */}
                <div style={{ 
                  background: 'rgba(99, 102, 241, 0.05)', 
                  padding: '16px', 
                  borderRadius: '12px',
                  border: '1px solid rgba(99, 102, 241, 0.2)',
                  display: 'flex',
                  flexDirection: 'column'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#818cf8', textTransform: 'uppercase' }}>
                        Proposed AI Reply Draft
                      </span>
                      <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#c7d2fe', fontSize: '0.7rem' }}>
                        v{selectedItem.draft_version}
                      </span>
                    </div>

                    {editingDraftId !== selectedItem.draft_id ? (
                      <button 
                        className="btn btn-secondary" 
                        onClick={() => handleStartEdit(selectedItem)}
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                        id="edit-draft-button"
                      >
                        <Edit3 size={12} /> Edit
                      </button>
                    ) : (
                      <button 
                        className="btn btn-primary" 
                        onClick={() => handleSaveDraft(selectedItem.draft_id)}
                        disabled={actionLoading}
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                        id="save-draft-button"
                      >
                        Save & Invalidate
                      </button>
                    )}
                  </div>

                  {editingDraftId === selectedItem.draft_id ? (
                    <div>
                      <textarea
                        value={draftText}
                        onChange={(e) => setDraftText(e.target.value)}
                        rows={10}
                        style={{
                          width: '100%',
                          background: 'rgba(0, 0, 0, 0.35)',
                          border: '1px solid var(--accent-indigo)',
                          borderRadius: '8px',
                          color: '#f8fafc',
                          padding: '10px',
                          fontSize: '0.85rem',
                          fontFamily: 'inherit',
                          outline: 'none',
                          resize: 'vertical'
                        }}
                      />
                      <p style={{ fontSize: '0.7rem', color: '#fbbf24', marginTop: '6px' }}>
                        * Saving changes updates the version, generates a new SHA-256 hash, and invalidates any previous approval.
                      </p>
                    </div>
                  ) : (
                    <div style={{ 
                      fontSize: '0.85rem', 
                      color: '#f1f5f9', 
                      lineHeight: '1.6', 
                      whiteSpace: 'pre-wrap', 
                      overflowY: 'auto',
                      maxHeight: '340px' 
                    }}>
                      {selectedItem.draft_body}
                    </div>
                  )}

                  {/* Cryptographic Content Hash Signature */}
                  <div style={{ 
                    marginTop: 'auto', 
                    paddingTop: '12px', 
                    borderTop: '1px solid rgba(255, 255, 255, 0.05)', 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '6px',
                    fontSize: '0.7rem',
                    color: 'var(--text-dim)' 
                  }}>
                    <Hash size={12} />
                    <span className="code-mono">
                      SHA-256: {selectedItem.content_hash.slice(0, 16)}...
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ 
                display: 'flex', 
                justifyContent: 'flex-end', 
                gap: '12px', 
                paddingTop: '16px', 
                borderTop: '1px solid var(--border-subtle)' 
              }}>
                <button
                  className="btn btn-danger"
                  onClick={() => handleReject(selectedItem.draft_id)}
                  disabled={actionLoading}
                  id="reject-draft-button"
                >
                  <X size={15} /> Reject Draft
                </button>

                <button
                  className="btn btn-success"
                  onClick={() => handleApproveAndSend(selectedItem)}
                  disabled={actionLoading || editingDraftId === selectedItem.draft_id}
                  id="approve-and-send-button"
                >
                  <Send size={15} /> Approve & Send
                </button>
              </div>

            </div>
          )}
        </div>
      )}
    </div>
  );
};
