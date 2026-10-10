import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { DashboardView } from './pages/DashboardView';
import { ApprovalQueueView } from './pages/ApprovalQueueView';
import { EmailsView } from './pages/EmailsView';
import { SettingsView } from './pages/SettingsView';
import { AuditLogView } from './pages/AuditLogView';
import { LoginView } from './pages/LoginView';
import type { EmailItem, ApprovalQueueItem, GmailStatus, AuditEvent } from './types';
import type { AuthUser } from './types/auth';
import { useAuth } from '@clerk/react';
import { api, setTokenGetter } from './api/client';

export const App: React.FC = () => {
  const { isLoaded, isSignedIn, getToken, signOut } = useAuth();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [emails, setEmails] = useState<EmailItem[]>([]);
  const [approvals, setApprovals] = useState<ApprovalQueueItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Wipe everything that belongs to the previous session
  const resetSession = () => {
    setUser(null);
    setActiveTab('dashboard');
    setEmails([]);
    setApprovals([]);
    setAuditEvents([]);
    setGmailStatus(null);
    setNotification(null);
  };

  // Give the API client a way to get a fresh Clerk session token for every request
  useEffect(() => {
    setTokenGetter(() => getToken());
    return () => setTokenGetter(null);
  }, [getToken]);

  // Once Clerk knows the session state, ask our backend who we are (also creates the local user row)
  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      resetSession();
      setAuthChecked(true);
      return;
    }

    let cancelled = false;
    setAuthChecked(false);
    const loadMe = async () => {
      try {
        const me = await api.me();
        if (!cancelled) setUser(me);
      } catch (err) {
        console.error('Could not load the user from the backend:', err);
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setAuthChecked(true);
      }
    };

    loadMe();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn]);

  useEffect(() => {
    if (user) {
      loadAllData();
    }
  }, [user]);

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

  const handleConnectGmail = async () => {
    try {
      const res = await api.getGoogleAuthUrl();
      if (res.auth_url) {
        window.location.href = res.auth_url;
      } else {
        alert(res.message || 'Google OAuth is not configured yet. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env.');
      }
    } catch (err: any) {
      alert(`Failed to connect Google account: ${err.message}`);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('oauth') === 'success') {
      setNotification('Google account connected successfully! Real Gmail inbox is now active.');
      window.history.replaceState(null, '', window.location.pathname);
      loadAllData();
      setTimeout(() => setNotification(null), 6000);
    }
  }, []);

  const handleLogout = async () => {
    await signOut();
    resetSession();
  };

  if (!isLoaded || !authChecked) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        Loading...
      </div>
    );
  }

  if (!isSignedIn) {
    return <LoginView />;
  }

  if (!user) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', padding: '24px', textAlign: 'center' }}>
        <p style={{ color: 'var(--text-muted)' }}>
          Signed in, but the backend did not answer. Make sure it is running at {import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}.
        </p>
        <button className="btn btn-secondary" onClick={handleLogout}>Log out</button>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingCount={approvals.length}
        gmailStatus={gmailStatus}
        onSync={handleSync}
        isSyncing={isSyncing}
        userEmail={user.email}
        onLogout={handleLogout}
        onConnectGmail={handleConnectGmail}
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
          <SettingsView
            gmailStatus={gmailStatus}
            onConnectGmail={handleConnectGmail}
          />
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
