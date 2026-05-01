import type { ReactNode } from 'react';

import './globals.css';

export const metadata = {
  title: 'Voice CRM Cockpit',
  description: 'Slack-inspired CRM board for live voice operations'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="root-shell">
          {children}
        </div>
      </body>
    </html>
  );
}
