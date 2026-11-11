import React from 'react';
import { TimelineEntry } from '../types/office';
import { History, Activity, ShieldAlert, CheckCircle, Zap } from 'lucide-react';

interface OfficeActivityTimelineProps {
  timeline: TimelineEntry[];
}

export const OfficeActivityTimeline: React.FC<OfficeActivityTimelineProps> = ({ timeline }) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-5 flex flex-col space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-100 text-blue-800">
            <History className="w-4 h-4" />
          </div>
          <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-800">
            Workforce Activity Stream ({timeline.length})
          </h2>
        </div>
        <span className="text-[10px] font-mono font-bold text-slate-400">
          WebSocket Real-time
        </span>
      </div>

      <div className="space-y-2.5 overflow-y-auto max-h-[280px] pr-1">
        {timeline.length === 0 ? (
          <div className="py-10 text-center text-xs text-slate-400 font-bold uppercase tracking-wider">
            No workforce events recorded yet. Run a recovery scenario to view activity.
          </div>
        ) : (
          timeline.map((item, idx) => {
            const isApproval = item.action.includes('APPROVAL');
            const isCompleted = item.action.includes('COMPLETED') || item.action.includes('APPROVED');
            const isStarted = item.action.includes('STARTED') || item.action.includes('ASSIGNED');

            return (
              <div
                key={idx}
                className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs flex items-start gap-2.5 hover:bg-slate-100/70 transition-all"
              >
                <div className="mt-0.5 shrink-0">
                  {isApproval ? (
                    <ShieldAlert className="w-4 h-4 text-rose-500" />
                  ) : isCompleted ? (
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                  ) : isStarted ? (
                    <Zap className="w-4 h-4 text-amber-500" />
                  ) : (
                    <Activity className="w-4 h-4 text-blue-500" />
                  )}
                </div>

                <div className="min-w-0 flex-1 space-y-0.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-extrabold text-slate-900 truncate">
                      {item.agent}
                    </span>
                    <span className="font-mono text-[10px] text-slate-400 shrink-0">
                      {item.timestamp}
                    </span>
                  </div>
                  <div className="flex items-start gap-2 pt-0.5">
                    <span className="text-[9px] font-black uppercase px-1.5 py-0.5 rounded bg-slate-200/90 text-slate-700 shrink-0 mt-0.5">
                      {item.action}
                    </span>
                    <p className="text-[11px] text-slate-700 font-medium leading-relaxed break-words flex-1">
                      {item.details}
                    </p>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

