import React from 'react';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';

export const metadata = {
  title: 'CONCORD-AI - Autonomous Exception Resolution Teammate',
  description: 'Paytm Autonomous AI Teammate for UPI Dispute & Failed Payment Exception Resolution',
  icons: {
    icon: '/favicon.svg',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#F8F9FA] text-slate-900 min-h-screen flex font-sans antialiased">
        {/* Left Sidebar Shell */}
        <Sidebar />

        {/* Main Application Area */}
        <div className="flex-1 flex flex-col min-w-0 min-h-screen">
          <Header />
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
