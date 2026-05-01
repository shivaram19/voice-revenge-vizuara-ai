import type { ReactNode } from 'react';
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";
import './globals.css';

const inter = Inter({subsets:['latin'],variable:'--font-sans'});

export const metadata = {
  title: 'Voice CRM',
  description: 'Multi-tenant Education Voice CRM'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={cn("font-sans", inter.variable)}>
      <body>
        {children}
      </body>
    </html>
  );
}
