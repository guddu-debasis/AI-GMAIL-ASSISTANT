import React from 'react';
import { RefreshCw } from 'lucide-react';
import type { AuditEvent } from '../types';

interface AuditLogViewProps {
  events: AuditEvent[];
  onRefresh: () => void;
}

export const AuditLogView: React.FC<AuditLogViewProps> = ({ events, onRefresh }) => {
  const getEventBadge = (type: string) => {
    switch (type) {
      case 'approved':
        return <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399' }}>APPROVED</span>;
      case 'sent':
        return <span className="badge" style={{ background: 'rgba(6, 182, 212, 0.2)', color: '#22d3ee' }}>SENT</span>;
      case 'rejected':
        return <span className="badge" style={{ background: 'rgba(244, 63, 94, 0.2)', color: '#fb7185' }}>REJECTED</span>;
      case 'approval_invalidated':
        return <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24' }}>INVALIDATED</span>;
      case 'edited':
        return <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.2)', color: '#c084fc' }}>EDITED</span>;
      case 'send_started':
        return <span className="badge" style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8' }}>SENDING</span>;
      default:
        return <span className="badge badge-status">{type.toUpperCase()}</span>;
    }
  };

  return (
    <div style={{ padding: '0 24px 32px', maxWidth: '1080px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#ffffff', marginBottom: '4px' }}>
            System Audit Trail
          </h2>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
            Cryptographically tracked audit events of every draft creation, modification, approval, and send action.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={onRefresh}>
          <RefreshCw size={14} /> Refresh Logs
        </button>
      </div>

      <div className="glass-panel" style={{ padding: '16px', overflowX: 'auto' }}>
        {events.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-dim)' }}>
            No audit events logged yet.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-dim)' }}>
                <th style={{ padding: '10px 14px' }}>Timestamp</th>
                <th style={{ padding: '10px 14px' }}>Event</th>
                <th style={{ padding: '10px 14px' }}>Version</th>
                <th style={{ padding: '10px 14px' }}>Content Hash</th>
                <th style={{ padding: '10px 14px' }}>Metadata Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr 
                  key={ev.id}
                  style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.03)' }}
                >
                  <td style={{ padding: '12px 14px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {new Date(ev.created_at).toLocaleTimeString()}
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    {getEventBadge(ev.event_type)}
                  </td>
                  <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>
                    v{ev.draft_version}
                  </td>
                  <td style={{ padding: '12px 14px' }}>
                    {ev.content_hash ? (
                      <span className="code-mono" style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>
                        {ev.content_hash.slice(0, 12)}...
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-dim)' }}>—</span>
                    )}
                  </td>
                  <td style={{ padding: '12px 14px', color: 'var(--text-muted)' }}>
                    {ev.metadata_json ? (
                      <span className="code-mono" style={{ fontSize: '0.75rem' }}>
                        {JSON.stringify(ev.metadata_json)}
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
