import React, { useState, useEffect } from 'react';
import { 
  Lock, 
  UserPlus, 
  Trash2, 
  Save 
} from 'lucide-react';
import type { UserSettings, VIPSender } from '../types';
import { api } from '../api/client';

export const SettingsView: React.FC = () => {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [vipSenders, setVipSenders] = useState<VIPSender[]>([]);
  const [newVipEmail, setNewVipEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [s, v] = await Promise.all([api.getSettings(), api.getVIPSenders()]);
      setSettings(s);
      setVipSenders(v);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCategoryToggle = (cat: string) => {
    if (!settings) return;
    const current = new Set(settings.approval_categories);
    if (current.has(cat)) {
      current.delete(cat);
    } else {
      current.add(cat);
    }
    setSettings({ ...settings, approval_categories: Array.from(current) });
  };

  const handleSaveSettings = async () => {
    if (!settings) return;
    setLoading(true);
    setFeedback(null);
    try {
      const updated = await api.updateSettings({
        approval_categories: settings.approval_categories,
        approve_when_uncertain: settings.approve_when_uncertain,
        approve_starred: settings.approve_starred,
        min_confidence: settings.min_confidence,
        allow_auto_send: false, // Invariant guard
      });
      setSettings(updated);
      setFeedback('Policies updated successfully. Policy version incremented.');
    } catch (err: any) {
      setFeedback(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAddVip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newVipEmail.trim()) return;
    try {
      await api.addVIPSender(newVipEmail.trim());
      setNewVipEmail('');
      const updated = await api.getVIPSenders();
      setVipSenders(updated);
    } catch (err: any) {
      alert(err.message || 'Failed to add VIP');
    }
  };

  const handleDeleteVip = async (id: string) => {
    try {
      await api.deleteVIPSender(id);
      setVipSenders(vipSenders.filter((v) => v.id !== id));
    } catch (err: any) {
      alert(err.message || 'Failed to delete VIP');
    }
  };

  if (!settings) {
    return <div style={{ padding: '24px', color: 'var(--text-muted)' }}>Loading policy settings...</div>;
  }

  const allCategories = [
    { id: 'job_recruitment', label: 'Job Offers & Recruiters', desc: 'Interview invitations, executive recruiters, salary offers' },
    { id: 'financial', label: 'Financial & Payments', desc: 'Invoices, wires, billing inquiries, pricing terms' },
    { id: 'legal_contractual', label: 'Legal & Contractual', desc: 'NDAs, customer agreements, terms of service, compliance' },
    { id: 'complaint_sensitive', label: 'Customer Grievances & Complaints', desc: 'Escalations, refunds, sensitive disputes' },
    { id: 'general', label: 'General Routine Messages', desc: 'Standard business and personal communication' },
  ];

  return (
    <div style={{ padding: '0 24px 32px', maxWidth: '960px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#ffffff', marginBottom: '4px' }}>
          Deterministic Policy Configuration
        </h2>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>
          Policy Engine (v{settings.policy_version}) enforces strict human authorization rules before any outgoing message is sent.
        </p>
      </div>

      {feedback && (
        <div style={{
          padding: '12px 18px',
          marginBottom: '20px',
          borderRadius: '10px',
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          color: '#34d399',
          fontSize: '0.875rem'
        }}>
          {feedback}
        </div>
      )}

      {/* 1. Protected Categories */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#ffffff', marginBottom: '6px' }}>
          Protected Categories (Human Approval Mandatory)
        </h3>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Emails classified in these categories will always require human review and approval.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {allCategories.map((cat) => {
            const isChecked = settings.approval_categories.includes(cat.id);
            return (
              <label 
                key={cat.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 16px',
                  borderRadius: '10px',
                  background: isChecked ? 'rgba(99, 102, 241, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${isChecked ? 'rgba(99, 102, 241, 0.3)' : 'var(--border-subtle)'}`,
                  cursor: 'pointer'
                }}
              >
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => handleCategoryToggle(cat.id)}
                  style={{ width: '16px', height: '16px', accentColor: 'var(--accent-indigo)' }}
                />
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
                    {cat.label}
                  </div>
                  <div style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>
                    {cat.desc}
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {/* 2. Guardrails & Thresholds */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#ffffff', marginBottom: '16px' }}>
          Deterministic Guardrails
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Uncertain classification toggle */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
                Approve when uncertain
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Require human review whenever LLM confidence is below threshold or classification is ambiguous.
              </div>
            </div>
            <input
              type="checkbox"
              checked={settings.approve_when_uncertain}
              onChange={(e) => setSettings({ ...settings, approve_when_uncertain: e.target.checked })}
              style={{ width: '18px', height: '18px', accentColor: 'var(--accent-indigo)' }}
            />
          </div>

          {/* Starred emails toggle */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
            <div>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
                Approve starred messages
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Require human authorization for all starred or flagged Gmail threads.
              </div>
            </div>
            <input
              type="checkbox"
              checked={settings.approve_starred}
              onChange={(e) => setSettings({ ...settings, approve_starred: e.target.checked })}
              style={{ width: '18px', height: '18px', accentColor: 'var(--accent-indigo)' }}
            />
          </div>

          {/* Min Confidence Threshold Slider */}
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
                Minimum Confidence Threshold
              </div>
              <span className="code-mono" style={{ color: '#818cf8', fontWeight: 700 }}>
                {Math.round(settings.min_confidence * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.50"
              max="0.99"
              step="0.01"
              value={settings.min_confidence}
              onChange={(e) => setSettings({ ...settings, min_confidence: parseFloat(e.target.value) })}
              style={{ width: '100%', accentColor: 'var(--accent-indigo)' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '4px' }}>
              <span>50% (Permissive)</span>
              <span>80% (Default Safe)</span>
              <span>99% (Strict Review)</span>
            </div>
          </div>

          {/* Auto Send Toggle - Protected Read Only */}
          <div style={{ 
            borderTop: '1px solid var(--border-subtle)', 
            paddingTop: '16px',
            opacity: 0.8,
            background: 'rgba(0, 0, 0, 0.2)',
            padding: '16px',
            borderRadius: '10px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Lock size={15} color="#fbbf24" />
                  <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f8fafc' }}>
                    Autonomous Sending (Locked Disabled)
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  By system specification, auto-send is permanently disabled in the MVP to guarantee zero unapproved emails leave your account.
                </div>
              </div>
              <span className="badge" style={{ background: 'rgba(244, 63, 94, 0.15)', color: '#fb7185' }}>
                DISABLED
              </span>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
          <button 
            className="btn btn-primary" 
            onClick={handleSaveSettings}
            disabled={loading}
            id="save-policy-settings-button"
          >
            <Save size={16} /> Save Policy Settings
          </button>
        </div>
      </div>

      {/* 3. VIP Senders */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#ffffff', marginBottom: '6px' }}>
          VIP Senders (Always Require Approval)
        </h3>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Outreach from these specific email addresses will never be dispatched automatically under any circumstances.
        </p>

        <form onSubmit={handleAddVip} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input
            type="email"
            placeholder="Add VIP email (e.g. boss@company.com)..."
            value={newVipEmail}
            onChange={(e) => setNewVipEmail(e.target.value)}
            style={{
              flex: 1,
              background: 'rgba(0, 0, 0, 0.25)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '8px 12px',
              color: '#ffffff',
              fontSize: '0.875rem',
              outline: 'none'
            }}
          />
          <button type="submit" className="btn btn-secondary">
            <UserPlus size={15} /> Add VIP
          </button>
        </form>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {vipSenders.length === 0 ? (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
              No VIP senders registered yet.
            </div>
          ) : (
            vipSenders.map((vip) => (
              <div
                key={vip.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)'
                }}
              >
                <span style={{ fontSize: '0.875rem', color: '#e2e8f0' }}>{vip.email_address}</span>
                <button
                  onClick={() => handleDeleteVip(vip.id)}
                  style={{ background: 'transparent', border: 'none', color: '#f87171', cursor: 'pointer' }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
