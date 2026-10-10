// One place to make every Clerk screen (sign in, sign up, user menu, profile) match the dark theme.
export const clerkAppearance = {
  variables: {
    colorPrimary: '#6366f1',
    colorPrimaryForeground: '#ffffff',
    colorBackground: '#0f172a',
    colorForeground: '#f8fafc',
    colorMutedForeground: '#94a3b8',
    colorMuted: '#1e293b',
    colorInput: '#0b1220',
    colorInputForeground: '#f8fafc',
    colorBorder: 'rgba(148, 163, 184, 0.25)',
    colorNeutral: '#f8fafc',
    colorRing: 'rgba(99, 102, 241, 0.45)',
    colorDanger: '#f43f5e',
    colorSuccess: '#10b981',
    colorShimmer: 'rgba(255, 255, 255, 0.12)',
    colorModalBackdrop: 'rgba(2, 6, 23, 0.7)',
    borderRadius: '0.75rem',
    fontFamily: "'Outfit', -apple-system, BlinkMacSystemFont, sans-serif",
  },
  elements: {
    card: { border: '1px solid rgba(148, 163, 184, 0.18)', boxShadow: '0 10px 40px rgba(0, 0, 0, 0.45)' },
  },
};
