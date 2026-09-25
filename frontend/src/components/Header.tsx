'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ConcordIcon } from '@/components/ConcordLogo';
import { fetchDemoHealth } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Search } from 'lucide-react';

export const Header: React.FC = () => {
  const pathname = usePathname();
  const [healthInfo, setHealthInfo] = useState<any>(null);

  useEffect(() => {
    fetchDemoHealth().then(d => setHealthInfo(d)).catch(() => {});
  }, []);

  const getPageTitle = () => {
    if (!pathname || pathname === '/' || pathname === '/cases') return 'Payment Exceptions';
    if (pathname.startsWith('/cases/')) return `Case ${pathname.split('/')[2]}`;
    if (pathname === '/escalations') return 'Human Ops Queue';
    if (pathname.startsWith('/agent-runs/')) return `Run Trace`;
    if (pathname === '/agent-runs') return 'Agent Runs';
    if (pathname === '/audit') return 'Audit Trail';
    if (pathname === '/scenarios') return 'Policy Rules';
    if (pathname === '/demo') return 'Presentation Mode';
    return 'Payment Operations';
  };

  const mobileNavItems = [
    { label: 'Exceptions', href: '/cases' },
    { label: 'Human Ops', href: '/escalations' },
    { label: 'Policy Rules', href: '/scenarios' },
    { label: 'Audit Trail', href: '/audit' },
    { label: 'Agent Runs', href: '/agent-runs' },
    { label: 'Demo', href: '/demo' },
  ];

  const llmMode = healthInfo?.llm_mode || 'MOCK';

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 text-xs font-sans">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        <div className="h-11 flex items-center justify-between">
          
          {/* Breadcrumb Header */}
          <div className="flex items-center space-x-2 text-slate-500">
            <Link href="/cases" className="flex items-center gap-1.5 font-bold text-slate-900 tracking-tight hover:text-slate-700">
              <ConcordIcon size={18} />
              <span className="font-extrabold font-sans">CONCORD</span>
            </Link>
            <span className="text-slate-300">/</span>
            <span className="text-slate-700 font-medium">{getPageTitle()}</span>
          </div>

          {/* Right Controls & Environment State */}
          <div className="flex items-center space-x-3">
            {/* Quick search shortcut trigger hint */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-200 bg-slate-50 text-slate-500 text-[11px]">
              <Search className="w-3 h-3 text-slate-400" />
              <span>Search cases...</span>
              <kbd className="bg-white text-slate-600 text-[9px] font-mono px-1 py-0.5 rounded border border-slate-200">⌘K</kbd>
            </div>

            <Badge variant="success" className="text-[10px] font-sans gap-1 bg-emerald-50 text-emerald-700 border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              Live Stream
            </Badge>

            <Badge variant="outline" className="text-[10px] font-mono bg-slate-50 text-slate-700 border-slate-200">
              LLM: {llmMode}
            </Badge>
          </div>

        </div>

        {/* Mobile Navigation Tabs */}
        <div className="flex md:hidden items-center space-x-1 overflow-x-auto pb-2 pt-1 border-t border-slate-100">
          {mobileNavItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-2.5 py-1 rounded text-[11px] font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-slate-100 text-slate-900 border border-slate-200 font-semibold'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>

      </div>
    </header>
  );
};

