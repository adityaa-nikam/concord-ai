'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ListOrdered, ShieldAlert, Cpu, ShieldCheck, PlayCircle, Presentation, ChevronRight
} from 'lucide-react';
import { ConcordLogo } from '@/components/ConcordLogo';
import { fetchDemoHealth } from '@/lib/api';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const [healthInfo, setHealthInfo] = useState<any>(null);

  useEffect(() => {
    fetchDemoHealth().then(data => setHealthInfo(data)).catch(() => {});
  }, []);

  const navGroups = [
    {
      heading: 'Operations',
      items: [
        { label: 'Payment Exceptions', href: '/cases', icon: ListOrdered },
        { label: 'Human Ops Queue', href: '/escalations', icon: ShieldAlert },
      ]
    },
    {
      heading: 'Controls',
      items: [
        { label: 'Policy Rules', href: '/scenarios', icon: PlayCircle },
        { label: 'Audit Trail', href: '/audit', icon: ShieldCheck },
        { label: 'Agent Runs', href: '/agent-runs', icon: Cpu },
      ]
    },
    {
      heading: 'Demo',
      items: [
        { label: 'Presentation Mode', href: '/demo', icon: Presentation },
      ]
    }
  ];

  const llmMode = healthInfo?.llm_mode || 'MOCK';

  return (
    <aside className="w-56 bg-white border-r border-slate-200 flex flex-col justify-between hidden md:flex shrink-0 min-h-screen font-sans">
      <div>
        {/* Brand Header */}
        <div className="p-4 border-b border-slate-100">
          <Link href="/" className="block group">
            <div className="flex items-center justify-between">
              <ConcordLogo variant="horizontal" iconSize={24} />
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 font-medium">
                v2.4
              </span>
            </div>
            <div className="text-[11px] text-slate-500 mt-1 font-normal">
              Payment Operations
            </div>
          </Link>
        </div>

        {/* Navigation Sections */}
        <nav className="p-3 space-y-4">
          {navGroups.map((group) => (
            <div key={group.heading} className="space-y-0.5">
              <div className="px-2 py-1 text-[10px] font-medium tracking-wider text-slate-400 uppercase font-sans">
                {group.heading}
              </div>
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href)) || (pathname === '/' && item.href === '/cases');
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                      isActive
                        ? 'bg-slate-100 text-slate-900 font-semibold text-slate-900'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-slate-900' : 'text-slate-400'}`} />
                      <span>{item.label}</span>
                    </div>
                    {isActive && <ChevronRight className="w-3 h-3 text-slate-400" />}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* Footer System Status & Environment */}
      <div className="p-3 border-t border-slate-200 space-y-2 bg-slate-50/50">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
          <span>STATUS</span>
          <span className="text-emerald-700 font-medium flex items-center gap-1 font-sans text-[10px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Operational
          </span>
        </div>

        <div className="bg-white p-2 rounded border border-slate-200 text-[10px] font-mono space-y-1 text-slate-600">
          <div className="flex items-center justify-between">
            <span>ENV</span>
            <span className="text-slate-800 font-medium">UPI SANDBOX</span>
          </div>
          <div className="flex items-center justify-between">
            <span>LLM ENGINE</span>
            <span className="text-slate-800 font-medium">
              {llmMode}
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};

