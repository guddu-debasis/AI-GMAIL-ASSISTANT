import React, { useState } from 'react';
import { Star, Calendar, User } from 'lucide-react';
import type { EmailItem } from '../types';

interface EmailsViewProps {
  emails: EmailItem[];
}

export const EmailsView: React.FC<EmailsViewProps> = ({ emails }) => {
  const [selectedEmail, setSelectedEmail] = useState<EmailItem | null>(emails[0] || null);

  return (
    <div style={{ padding: '0 24px 32px' }}>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff', marginBottom: '4px' }}>
          All Processed Email Threads
        </h2>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
          Ingested via Gmail API and classified with deterministic safety policies.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 380px) 1fr', gap: '20px' }}>
        {/* Email list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '740px', overflowY: 'auto' }}>
          {emails.map((email) => {
            const isSelected = selectedEmail?.id === email.id;
            const status = email.reply_draft?.status || 'PROCESSED';
            return (
              <div
                key={email.id}
                onClick={() => setSelectedEmail(email)}
                className="glass-panel"
                style={{
                  padding: '16px',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  borderColor: isSelected ? 'var(--accent-indigo)' : 'var(--border-subtle)',
                  background: isSelected ? 'rgba(99, 102, 241, 0.12)' : 'var(--bg-card)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#e2e8f0' }}>
                    {email.sender}
                  </span>
                  {email.is_starred && <Star size={14} color="#f59e0b" fill="#f59e0b" />}
                </div>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 500, color: '#f8fafc', marginBottom: '6px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {email.subject || '(No Subject)'}
                </h4>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                  {email.classification && (
                    <span className={`badge badge-risk-${email.classification.risk_level}`} style={{ fontSize: '0.65rem' }}>
                      {email.classification.risk_level}
                    </span>
                  )}
                  <span className="badge badge-status" style={{ fontSize: '0.65rem' }}>
                    {status}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Email & Thread View */}
        {selectedEmail && (
          <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>
                  {selectedEmail.subject || '(No Subject)'}
                </h3>
                {selectedEmail.reply_draft && (
                  <span className="badge" style={{ 
                    background: selectedEmail.reply_draft.status === 'SENT' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                    color: selectedEmail.reply_draft.status === 'SENT' ? '#34d399' : '#818cf8'
                  }}>
                    {selectedEmail.reply_draft.status}
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <User size={14} /> <strong>From:</strong> {selectedEmail.sender}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Calendar size={14} /> <strong>Received:</strong> {new Date(selectedEmail.created_at).toLocaleString()}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="code-mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Thread: {selectedEmail.gmail_thread_id}
                  </span>
                </div>
              </div>
            </div>

            {/* Email Body */}
            <div>
              <h4 style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Inbound Message Content
              </h4>
              <div style={{ 
                background: 'rgba(0, 0, 0, 0.25)', 
                padding: '16px', 
                borderRadius: '10px', 
                fontSize: '0.875rem', 
                lineHeight: '1.6', 
                whiteSpace: 'pre-wrap',
                color: '#e2e8f0',
                border: '1px solid var(--border-subtle)' 
              }}>
                {selectedEmail.body_text || 'No text content available'}
              </div>
            </div>

            {/* Classification Analysis */}
            {selectedEmail.classification && (
              <div style={{ 
                background: 'rgba(255, 255, 255, 0.02)', 
                padding: '16px', 
                borderRadius: '10px', 
                border: '1px solid var(--border-subtle)' 
              }}>
                <h4 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#818cf8', textTransform: 'uppercase', marginBottom: '8px' }}>
                  AI Risk & Classification Analysis
                </h4>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', flexWrap: 'wrap' }}>
                  <span className={`badge badge-risk-${selectedEmail.classification.risk_level}`}>
                    Risk: {selectedEmail.classification.risk_level}
                  </span>
                  <span className="badge badge-status">
                    Category: {selectedEmail.classification.category}
                  </span>
                  <span className="badge badge-status">
                    Confidence: {Math.round(selectedEmail.classification.confidence * 100)}%
                  </span>
                </div>
                <p style={{ fontSize: '0.825rem', color: '#cbd5e1' }}>
                  <strong>Rationale:</strong> {selectedEmail.classification.rationale}
                </p>
              </div>
            )}

            {/* Generated Reply Draft */}
            {selectedEmail.reply_draft && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h4 style={{ fontSize: '0.8rem', fontWeight: 600, color: '#34d399', textTransform: 'uppercase' }}>
                    Reply Draft (v{selectedEmail.reply_draft.version})
                  </h4>
                  <span className="code-mono" style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                    Hash: {selectedEmail.reply_draft.content_hash.slice(0, 16)}...
                  </span>
                </div>
                <div style={{ 
                  background: 'rgba(16, 185, 129, 0.04)', 
                  padding: '16px', 
                  borderRadius: '10px', 
                  fontSize: '0.875rem', 
                  lineHeight: '1.6', 
                  whiteSpace: 'pre-wrap',
                  color: '#f8fafc',
                  border: '1px solid rgba(16, 185, 129, 0.2)' 
                }}>
                  {selectedEmail.reply_draft.body}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
