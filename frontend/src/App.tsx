import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { DashboardView } from './pages/DashboardView';
import { ApprovalQueueView } from './pages/ApprovalQueueView';
import { EmailsView } from './pages/EmailsView';
import { SettingsView } from './pages/SettingsView';
import { AuditLogView } from './pages/AuditLogView';
import type { EmailItem, ApprovalQueueItem, GmailStatus, AuditEvent } from './types';
import { api } from './api/client';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [approvals, setApprovals] = useState<ApprovalQueueItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      const [statusRes, emailsRes, approvalsRes, auditRes] = await Promise.all([
        api.getGmailStatus().catch(() => null),
        api.getEmails().catch(() => []),
        api.getApprovalQueue().catch(() => []),
        api.getAuditEvents().catch(() => []),
      ]);

      if (statusRes) setGmailStatus(statusRes);
      setEmails(emailsRes || []);
      setApprovals(approvalsRes || []);
      setAuditEvents(auditRes || []);
    } catch (err) {
      console.error('Failed to load application data:', err);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const res = await api.syncInbox();
      setNotification(`Inbox synchronized: ${res.synced_count} emails ingested & analyzed.`);
      await loadAllData();
      setTimeout(() => setNotification(null), 4000);
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingCount={approvals.length}
        gmailStatus={gmailStatus}
        onSync={handleSync}
        isSyncing={isSyncing}
      />

      {notification && (
        <div style={{
          margin: '0 24px 16px',
          padding: '12px 20px',
          borderRadius: '10px',
          background: 'rgba(99, 102, 241, 0.2)',
          border: '1px solid rgba(99, 102, 241, 0.4)',
          color: '#c7d2fe',
          fontSize: '0.875rem'
        }}>
          {notification}
        </div>
      )}

      <main style={{ flex: 1 }}>
        {activeTab === 'dashboard' && (
          <DashboardView
            emails={emails}
            approvals={approvals}
            onNavigateToApprovals={() => setActiveTab('approvals')}
            onNavigateToSettings={() => setActiveTab('settings')}
          />
        )}

        {activeTab === 'approvals' && (
          <ApprovalQueueView
            items={approvals}
            onRefresh={loadAllData}
          />
        )}

        {activeTab === 'emails' && (
          <EmailsView emails={emails} />
        )}

        {activeTab === 'settings' && (
          <SettingsView />
        )}

        {activeTab === 'audit' && (
          <AuditLogView
            events={auditEvents}
            onRefresh={loadAllData}
          />
        )}
      </main>
    </div>
  );
};

export default App;
