import React from 'react';
import { VirtualAgent } from '../types/office';
import { Cpu, Terminal, MapPin } from 'lucide-react';

interface AgentTaskPanelProps {
  agent: VirtualAgent | undefined;
  onSendToRoom: (agentId: number, room: 'workstation' | 'conference' | 'approval' | 'breakroom') => void;
}

export const AgentTaskPanel: React.FC<AgentTaskPanelProps> = ({ agent, onSendToRoom }) => {
  if (!agent) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 text-center text-slate-400">
        <Cpu className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-xs font-bold">Select an agent from the roster or office canvas</p>
      </div>
    );
  }

  const isWorking = agent.status === 'working';
  const isWaiting = agent.status === 'waiting_approval' || agent.isPermissionActive;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2.5">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center font-black text-xs text-white"
            style={{ backgroundColor: agent.color }}
          >
            {agent.id}
          </div>
          <div>
            <h3 className="text-xs font-extrabold text-slate-900 leading-tight">{agent.name}</h3>
            <p className="text-[10px] font-semibold text-slate-500">{agent.role}</p>
          </div>
        </div>

        <span
          className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${
            isWaiting
              ? 'bg-rose-100 text-rose-800 border border-rose-300'
              : isWorking
              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
              : 'bg-slate-100 text-slate-600'
          }`}
        >
          {agent.status}
        </span>
      </div>

      {/* Task & Tool Activity */}
      <div className="space-y-3">
        <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 space-y-2">
          <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-slate-400" /> Current Subtask
            </span>
            {agent.currentTool && (
              <span className="font-mono text-[10px] text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded">
                Tool: {agent.currentTool}
              </span>
            )}
          </div>

          <p className="text-xs font-medium text-slate-800 leading-relaxed min-h-[36px]">
            {agent.currentTask || 'Idle at designated workstation awaiting CEO assignment.'}
          </p>
        </div>

        {/* Location & Navigation */}
        <div className="flex items-center justify-between text-xs bg-slate-50 p-3 rounded-xl border border-slate-100">
          <div className="flex items-center gap-1.5 text-slate-600 font-semibold text-[11px]">
            <MapPin className="w-3.5 h-3.5 text-slate-400" />
            <span>Assigned Area:</span>
            <span className="font-extrabold text-slate-900">{agent.department}</span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => onSendToRoom(agent.id, 'conference')}
              className="px-2 py-1 bg-white hover:bg-slate-100 text-slate-700 text-[10px] font-bold rounded-lg border border-slate-200 transition-all"
            >
              Conference
            </button>
            <button
              onClick={() => onSendToRoom(agent.id, 'workstation')}
              className="px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-[10px] font-bold rounded-lg border border-emerald-200 transition-all"
            >
              Desk
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
