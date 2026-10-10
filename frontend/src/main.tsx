import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ClerkProvider } from '@clerk/react'
import { clerkAppearance } from './clerkAppearance'

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined

const root = createRoot(document.getElementById('root')!)

if (!publishableKey) {
  // Without the key Clerk cannot start. Say so clearly instead of showing a blank page.
  root.render(
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
      <div className="glass-panel" style={{ maxWidth: '520px', padding: '28px' }}>
        <h2 style={{ marginBottom: '8px' }}>Clerk key is missing</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.6 }}>
          Create a file named <code>.env</code> inside the <code>frontend</code> folder with this line,
          then restart <code>npm run dev</code>:
        </p>
        <pre style={{ marginTop: '12px', padding: '12px', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', overflowX: 'auto' }}>
          VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
        </pre>
        <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem', marginTop: '12px' }}>
          Get the key from Clerk Dashboard, API keys page.
        </p>
      </div>
    </div>,
  )
} else {
  root.render(
    <StrictMode>
      <ClerkProvider publishableKey={publishableKey} appearance={clerkAppearance}>
        <App />
      </ClerkProvider>
    </StrictMode>,
  )
}
