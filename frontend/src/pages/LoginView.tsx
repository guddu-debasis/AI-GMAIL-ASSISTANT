import React, { useState } from 'react';
import { SignIn, SignUp } from '@clerk/react';
import { ShieldCheck } from 'lucide-react';
import { clerkAppearance as baseAppearance } from '../clerkAppearance';

type Mode = 'sign-in' | 'sign-up';

// We switch between the two forms ourselves, so hide Clerk's own "Don't have an account?" link
const clerkAppearance = {
  ...baseAppearance,
  elements: {
    ...baseAppearance.elements,
    footerAction: { display: 'none' },
  },
};

export const LoginView: React.FC = () => {
  const [mode, setMode] = useState<Mode>('sign-in');

  const switchMode = (next: Mode) => {
    if (next === mode) return;
    // Clerk keeps its own step in the URL hash. Clear it so the other form starts fresh.
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    setMode(next);
  };

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 20px',
    borderRadius: '8px',
    border: 'none',
    cursor: 'pointer',
    fontFamily: 'var(--font-sans)',
    fontSize: '0.875rem',
    fontWeight: active ? 600 : 500,
    background: active ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
    color: active ? '#a5b4fc' : 'var(--text-muted)',
  });

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '20px',
      padding: '24px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '46px',
          height: '46px',
          borderRadius: '12px',
          background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 16px rgba(99, 102, 241, 0.4)',
        }}>
          <ShieldCheck size={26} color="#ffffff" />
        </div>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff' }}>AI Gmail Assistant</h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Sign in to review and approve your drafts</p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '6px', padding: '4px', borderRadius: '10px', background: 'rgba(255, 255, 255, 0.04)', border: '1px solid var(--border-subtle)' }}>
        <button type="button" id="auth-tab-sign-in" style={tabStyle(mode === 'sign-in')} onClick={() => switchMode('sign-in')}>
          Sign in
        </button>
        <button type="button" id="auth-tab-sign-up" style={tabStyle(mode === 'sign-up')} onClick={() => switchMode('sign-up')}>
          Create account
        </button>
      </div>

      {mode === 'sign-in' ? (
        <SignIn routing="hash" appearance={clerkAppearance} />
      ) : (
        <SignUp routing="hash" appearance={clerkAppearance} />
      )}
    </div>
  );
};

export default LoginView;
