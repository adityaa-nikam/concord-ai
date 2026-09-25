import React, { useState } from 'react';
import Link from 'next/link';
import { Search, Play, ExternalLink, Filter, RefreshCw } from 'lucide-react';
import { CaseListItem } from '@/lib/types';
import { StatusBadge, PriorityBadge } from './StatusBadge';
import { triggerAgentRun } from '@/lib/api';
import { Button } from '@/components/ui/button';

interface CaseTableProps {
  cases: CaseListItem[];
  onRefresh: () => void;
}

export const CaseTable: React.FC<CaseTableProps> = ({ cases, onRefresh }) => {
  const [search, setSearch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [runningCaseId, setRunningCaseId] = useState<string | null>(null);

  const handleRunAgent = async (e: React.MouseEvent, caseId: string) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      setRunningCaseId(caseId);
      await triggerAgentRun(caseId);
      onRefresh();
    } catch (err: any) {
      alert(`Error running agent: ${err.message}`);
    } finally {
      setRunningCaseId(null);
    }
  };

  const filteredCases = (cases || []).filter((c) => {
    const matchesStatus = selectedStatus === 'ALL' || c.status === selectedStatus;
    const matchesSearch =
      search === '' ||
      c.case_number.toLowerCase().includes(search.toLowerCase()) ||
      c.transaction_utr.toLowerCase().includes(search.toLowerCase()) ||
      c.customer_name.toLowerCase().includes(search.toLowerCase()) ||
      c.customer_upi.toLowerCase().includes(search.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const getTatCountdown = (deadlineStr: string) => {
    const deadline = new Date(deadlineStr).getTime();
    const diffMs = deadline - Date.now();
    if (diffMs <= 0) return <span className="text-rose-600 font-medium font-mono text-[11px]">Breached</span>;
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const mins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    return (
      <span className={`font-mono text-[11px] ${hours < 4 ? "text-amber-700 font-medium" : "text-slate-500"}`}>
        {hours}h {mins}m remaining
      </span>
    );
  };

  return (
    <div className="bg-white border border-slate-200 rounded-md overflow-hidden font-sans">
      
      {/* Search & Filter Toolbar */}
      <div className="p-3 border-b border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row items-center justify-between gap-3">
        
        {/* Search Input */}
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search Case ID, UTR, Name or UPI..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-white border border-slate-200 text-slate-900 text-xs rounded pl-8 pr-3 py-1.5 focus:outline-none focus:border-slate-400 placeholder-slate-400 font-sans"
          />
        </div>

        {/* Filter Dropdown & Refresh */}
        <div className="flex items-center space-x-2 w-full sm:w-auto justify-between sm:justify-end">
          <div className="flex items-center space-x-2 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-white border border-slate-200 text-slate-700 text-xs rounded px-2.5 py-1.5 focus:outline-none focus:border-slate-400 font-sans"
            >
              <option value="ALL">All Statuses</option>
              <option value="NEW">New Complaints</option>
              <option value="INVESTIGATING">Investigating</option>
              <option value="RESOLVED">Resolved</option>
              <option value="ESCALATED">Escalated</option>
            </select>
          </div>

          <Button
            variant="outline"
            size="icon"
            onClick={onRefresh}
            className="h-8 w-8 text-slate-600 border-slate-200 bg-white hover:bg-slate-50"
            title="Refresh Table"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>

      </div>

      {/* Case Data Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50/80 text-slate-500 uppercase tracking-wider border-b border-slate-200 font-sans text-[10px] font-semibold">
            <tr>
              <th className="py-2.5 px-4">Case Reference</th>
              <th className="py-2.5 px-4">Customer / UPI</th>
              <th className="py-2.5 px-4">Dispute Amount</th>
              <th className="py-2.5 px-4">State</th>
              <th className="py-2.5 px-4">Priority</th>
              <th className="py-2.5 px-4">RBI TAT SLA</th>
              <th className="py-2.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {filteredCases.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500 font-sans text-xs">
                  No dispute cases match current search filter.
                </td>
              </tr>
            ) : (
              filteredCases.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                  {/* Case Reference */}
                  <td className="py-3 px-4">
                    <Link href={`/cases/${c.id}`} className="block">
                      <div className="font-mono font-semibold text-slate-900 hover:underline text-xs">
                        {c.case_number}
                      </div>
                      <div className="font-mono text-[11px] text-slate-400 mt-0.5">
                        UTR: {c.transaction_utr}
                      </div>
                    </Link>
                  </td>

                  {/* Customer / UPI */}
                  <td className="py-3 px-4">
                    <div className="font-medium text-slate-900">{c.customer_name}</div>
                    <div className="font-mono text-[11px] text-slate-500">{c.customer_upi}</div>
                  </td>

                  {/* Amount */}
                  <td className="py-3 px-4 font-mono font-semibold text-slate-900 text-xs">
                    ₹{c.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>

                  {/* State */}
                  <td className="py-3 px-4">
                    <StatusBadge status={c.status} />
                  </td>

                  {/* Priority */}
                  <td className="py-3 px-4">
                    <PriorityBadge priority={c.priority} />
                  </td>

                  {/* TAT SLA */}
                  <td className="py-3 px-4">
                    {getTatCountdown(c.tat_deadline)}
                  </td>

                  {/* Actions */}
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button
                        variant={c.status === 'RESOLVED' ? 'outline' : 'default'}
                        size="sm"
                        onClick={(e) => handleRunAgent(e, c.id)}
                        disabled={runningCaseId === c.id || c.status === 'RESOLVED'}
                        className="gap-1 font-sans text-xs h-7 px-2.5"
                      >
                        <Play className={`w-3 h-3 fill-current ${runningCaseId === c.id ? 'animate-spin' : ''}`} />
                        {runningCaseId === c.id ? 'Running...' : 'Run Agent'}
                      </Button>

                      <Link href={`/cases/${c.id}`}>
                        <Button variant="outline" size="icon" className="h-7 w-7 text-slate-500 border-slate-200">
                          <ExternalLink className="w-3 h-3" />
                        </Button>
                      </Link>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
};

