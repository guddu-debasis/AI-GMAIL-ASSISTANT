import React from 'react';
import { UserProfile } from '@clerk/react';

// Clerk's full account page: name, photo, email addresses, password, two step login, active sessions.
export const ProfileView: React.FC = () => {
  return (
    <div style={{ padding: '0 24px 32px', display: 'flex', justifyContent: 'center' }}>
      <UserProfile
        routing="hash"
        appearance={{
          elements: {
            rootBox: { width: '100%', maxWidth: '960px' },
            cardBox: { width: '100%', maxWidth: '960px' },
          },
        }}
      />
    </div>
  );
};

export default ProfileView;
