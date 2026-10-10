import React from 'react';
import { 
  ShieldCheck, 
  Mail, 
  CheckCircle2, 
  Inbox, 
  Settings, 
  History, 
  RefreshCw,
  LogOut
} from 'lucide-react';
import type { GmailStatus } from '../types';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  pendingCount: number;
  gmailStatus: GmailStatus | null;
  onSync: () => void;
  isSyncing: boolean;
  userEmail: string;
  onLogout: () => void;
  onConnectGmail: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  pendingCount,
  gmailStatus,
  onSync,
  isSyncing,
  userEmail,
  onLogout,
  onConnectGmail,
}) => {
  return (
    <header className="glass-panel" style={{ margin: '16px 24px', padding: '16px 24px', borderRadius: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Logo & Product Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ 
            width: '42px', 
            height: '42px', 
            borderRadius: '12px', 
            background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(99, 102, 241, 0.4)'
          }}>
            <ShieldCheck size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: '700', letterSpacing: '-0.02em', color: '#ffffff' }}>
                AI Gmail Assistant
              </h1>
              <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                HUMAN-IN-THE-LOOP
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Deterministic Policy Engine • Protected Draft Dispatch
            </p>
          </div>
        </div>

        {/* Status, Sync Action and Account */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            padding: '6px 14px', 
            borderRadius: '10px', 
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.825rem'
          }}>
            <span style={{ 
              width: '8px', 
              height: '8px', 
              borderRadius: '50%', 
              backgroundColor: gmailStatus?.connected ? '#10b981' : '#f59e0b',
              boxShadow: gmailStatus?.connected ? '0 0 8px #10b981' : '0 0 8px #f59e0b'
            }} className="pulse-indicator" />
            <span style={{ color: 'var(--text-muted)' }}>
              {gmailStatus?.gmail_address ? gmailStatus.gmail_address : 'Sandbox / Mock Inbox'}
            </span>
          </div>

          {(!gmailStatus?.connected || !gmailStatus?.gmail_address) && (
            <button 
              className="btn btn-secondary"
              onClick={onConnectGmail}
              id="connect-gmail-button"
              style={{ fontSize: '0.825rem', borderColor: 'rgba(99, 102, 241, 0.4)', color: '#c7d2fe' }}
            >
              <Mail size={14} color="#818cf8" />
              Connect Real Gmail
            </button>
          )}

          <button 
            className="btn btn-primary"
            onClick={onSync}
            disabled={isSyncing}
            id="sync-inbox-button"
          >
            <RefreshCw size={15} className={isSyncing ? 'animate-spin' : ''} style={{ animation: isSyncing ? 'spin 1s linear infinite' : 'none' }} />
            {isSyncing ? 'Syncing...' : 'Sync Inbox'}
          </button>

          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px', 
            paddingLeft: '12px', 
            borderLeft: '1px solid var(--border-subtle)' 
          }}>
            <span 
              title={userEmail}
              style={{ 
                fontSize: '0.8rem', 
                color: 'var(--text-muted)', 
                maxWidth: '180px', 
                overflow: 'hidden', 
                textOverflow: 'ellipsis', 
                whiteSpace: 'nowrap' 
              }}
            >
              {userEmail}
            </span>
            <button 
              className="btn btn-secondary"
              onClick={onLogout}
              id="logout-button"
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <LogOut size={14} />
              Log out
            </button>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav style={{ display: 'flex', gap: '8px', marginTop: '16px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px', overflowX: 'auto' }}>
        {[
          { id: 'dashboard', label: 'Dashboard', icon: Inbox },
          { id: 'approvals', label: 'Approval Queue', icon: CheckCircle2, badge: pendingCount },
          { id: 'emails', label: 'All Emails', icon: Mail },
          { id: 'settings', label: 'Approval Policies', icon: Settings },
          { id: 'audit', label: 'Audit Trail', icon: History },
        ].map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              id={`nav-tab-${item.id}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '8px',
                border: 'none',
                background: isActive ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
                color: isActive ? '#a5b4fc' : 'var(--text-muted)',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.875rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={16} />
              <span>{item.label}</span>
              {typeof item.badge === 'number' && item.badge > 0 && (
                <span style={{
                  padding: '1px 7px',
                  borderRadius: '10px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  backgroundColor: '#f43f5e',
                  color: '#ffffff',
                }}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </header>
  );
};
