import React from 'react';
import { VirtualAgent } from '../types/office';
import { Bot, ShieldAlert, Clock, Activity } from 'lucide-react';

interface AgentRosterProps {
  agents: VirtualAgent[];
  selectedAgentId: number | null;
  onSelectAgent: (id: number) => void;
}

export const AgentRoster: React.FC<AgentRosterProps> = ({
  agents,
  selectedAgentId,
  onSelectAgent,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-5 flex flex-col space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-100 text-emerald-800">
            <Bot className="w-4 h-4" />
          </div>
          <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-800">
            Workforce Roster ({agents.length})
          </h2>
        </div>
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          Strands AI
        </span>
      </div>

      <div className="space-y-2.5 overflow-y-auto max-h-[460px] pr-1">
        {agents.map((agent) => {
          const isSelected = agent.id === selectedAgentId;
          const isWorking = agent.status === 'working';
          const isWaitingApproval = agent.status === 'waiting_approval' || agent.isPermissionActive;

          return (
            <div
              key={agent.id}
              onClick={() => onSelectAgent(agent.id)}
              className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                isSelected
                  ? 'bg-slate-900 text-white border-slate-800 shadow-md ring-2 ring-emerald-500/30'
                  : 'bg-slate-50/70 hover:bg-slate-100/90 text-slate-800 border-slate-200/60'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                {/* Agent Number / Color Bubble */}
                <div
                  className="w-8 h-8 rounded-xl flex items-center justify-center font-extrabold text-xs text-white shadow-xs shrink-0"
                  style={{ backgroundColor: agent.color }}
                >
                  #{agent.id}
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className={`text-xs font-extrabold truncate ${isSelected ? 'text-white' : 'text-slate-900'}`}>
                      {agent.name}
                    </p>
                    {agent.id === 1 && (
                      <span className="text-[9px] font-extrabold bg-blue-500/20 text-blue-400 px-1.5 py-0.2 rounded border border-blue-500/30 shrink-0">
                        LEAD
                      </span>
                    )}
                  </div>
                  <p className={`text-[10px] font-semibold truncate ${isSelected ? 'text-slate-300' : 'text-slate-500'}`}>
                    {agent.role}
                  </p>
                  <p className={`text-[9px] font-medium tracking-wide truncate ${isSelected ? 'text-slate-400' : 'text-slate-400'}`}>
                    📍 {agent.department}
                  </p>
                </div>
              </div>

              {/* Status Badge */}
              <div className="shrink-0 flex flex-col items-end gap-1">
                {isWaitingApproval ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-500/20 text-rose-400 border border-rose-500/40 flex items-center gap-1 animate-pulse">
                    <ShieldAlert className="w-3 h-3" /> APPROVAL
                  </span>
                ) : isWorking ? (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1">
                    <Activity className="w-3 h-3 animate-spin" /> WORKING
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-200/50 text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> IDLE
                  </span>
                )}

                {agent.currentTool && (
                  <span className="text-[9px] font-mono font-bold text-emerald-400 truncate max-w-[90px]">
                    ⚙️ {agent.currentTool}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
