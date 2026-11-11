import { useState, useEffect, useRef, useCallback } from 'react';
import { officeTransport } from '../services/officeTransport';
import { apiFetch } from '../../../api/client';
import { OfficeState } from '../office/engine/officeState';
import { setCharacterTemplates } from '../office/sprites/spriteData';
import { setFloorSprites } from '../office/floorTiles';
import { setWallSprites } from '../office/wallTiles';
import { setCarpetSprites } from '../office/sprites/carpetTiles';
import { setPetTemplates } from '../office/sprites/petSpriteData';
import { buildDynamicCatalog } from '../office/layout/furnitureCatalog';
import {
  VirtualAgent,
  AgentRole,
  AgentDepartment,
  PendingApproval,
  TimelineEntry,
  CEOOpsReport,
  AgentSpeechBubbleItem,
} from '../types/office';

const AGENT_METADATA: Record<number, { name: string; role: AgentRole; department: AgentDepartment; color: string }> = {
  1: {
    name: 'Sarah Chen (CEO)',
    role: 'CEO / Operations Supervisor',
    department: 'Executive Office',
    color: '#3b82f6',
  },
  2: {
    name: 'Marcus Vance',
    role: 'Inventory Risk Specialist',
    department: 'AI Agent Workroom',
    color: '#10b981',
  },
  3: {
    name: 'Elena Rostova',
    role: 'Recovery Strategy Specialist',
    department: 'AI Agent Workroom',
    color: '#8b5cf6',
  },
  4: {
    name: 'David Kim',
    role: 'Logistics & Route Specialist',
    department: 'AI Agent Workroom',
    color: '#f59e0b',
  },
  5: {
    name: 'Aisha Patel',
    role: 'Commerce & Markdown Specialist',
    department: 'AI Agent Workroom',
    color: '#ec4899',
  },
  6: {
    name: 'Tom Becker',
    role: 'Fulfillment & Warehouse Specialist',
    department: 'AI Agent Workroom',
    color: '#06b6d4',
  },
  7: {
    name: 'Linda Zhang',
    role: 'Finance & Margins Specialist',
    department: 'AI Agent Workroom',
    color: '#6366f1',
  },
};

export function useOfficeWebSocket() {
  const [connected, setConnected] = useState(false);
  const [agents, setAgents] = useState<VirtualAgent[]>(() =>
    [1, 2, 3, 4, 5, 6, 7].map((id) => ({
      id,
      name: AGENT_METADATA[id].name,
      role: AGENT_METADATA[id].role,
      department: AGENT_METADATA[id].department,
      status: 'idle',
      color: AGENT_METADATA[id].color,
    }))
  );
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(1);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [latestReport, setLatestReport] = useState<CEOOpsReport | null>(null);
  const [isRunningWorkflow, setIsRunningWorkflow] = useState(false);
  const [speechBubbles, setSpeechBubbles] = useState<Record<number, AgentSpeechBubbleItem>>({});

  const showSpeechBubble = useCallback(
    (
      agentId: number,
      message: string,
      kind: 'instruction' | 'working' | 'reporting' | 'approval' | 'success' | 'failure' | 'general' = 'general',
      durationSec = 4.0
    ) => {
      const now = Date.now();
      const durationMs = Math.min(durationSec, 4.5) * 1000;
      setSpeechBubbles(() => {
        // Enforce single active speaker to guarantee zero clutter and zero character occlusion
        return {
          [agentId]: {
            id: agentId,
            agentId,
            message,
            kind,
            expiresAt: now + durationMs,
          },
        };
      });
    },
    []
  );

  // Singleton OfficeState instance for Canvas rendering
  const officeStateRef = useRef<OfficeState | null>(null);
  if (!officeStateRef.current) {
    officeStateRef.current = new OfficeState();
  }
  const officeState = officeStateRef.current;

  // Poll or refresh pending approvals
  const refreshPendingApprovals = useCallback(async () => {
    try {
      const res = await apiFetch('/api/office/approval/pending');
      if (res.ok) {
        const data = await res.json();
        setPendingApprovals(data.approvals || []);
      }
    } catch {
      // Backend may be offline during build
    }
  }, []);

  const addTimelineEvent = useCallback((agentName: string, action: string, details: string) => {
    const timeStr = new Date().toLocaleTimeString();
    setTimeline((prev) => [{ timestamp: timeStr, agent: agentName, action, details }, ...prev.slice(0, 49)]);
  }, []);

  useEffect(() => {
    officeTransport.connect();

    const unsubConn = officeTransport.onConnection((isConnected) => {
      setConnected(isConnected);
      if (isConnected) {
        refreshPendingApprovals();
      }
    });

    const unsubMsg = officeTransport.onMessage((msg: any) => {
      // Assets pre-hydration
      if (msg.type === 'characterSpritesLoaded') {
        if (msg.characters) setCharacterTemplates(msg.characters);
      } else if (msg.type === 'floorTilesLoaded') {
        if (msg.sprites) setFloorSprites(msg.sprites);
      } else if (msg.type === 'wallTilesLoaded') {
        if (msg.sets) setWallSprites(msg.sets);
      } else if (msg.type === 'carpetTilesLoaded') {
        if (msg.sets) setCarpetSprites(msg.sets);
      } else if (msg.type === 'petSpritesLoaded') {
        if (msg.pets) setPetTemplates(msg.pets, msg.petNames);
      } else if (msg.type === 'furnitureAssetsLoaded') {
        if (msg.catalog && msg.sprites) {
          buildDynamicCatalog({ catalog: msg.catalog, sprites: msg.sprites });
        }
      }

      // Layout loaded
      else if (msg.type === 'layoutLoaded' || msg.type === 'layout') {
        if (msg.layout) {
          officeState.rebuildFromLayout(msg.layout);
        }
      }

      // Existing agents registration
      else if (msg.type === 'existingAgents') {
        const agentList: number[] = msg.agents || [];
        const metaDict = msg.agentMeta || {};
        for (const id of agentList) {
          const m = metaDict[id] || metaDict[String(id)] || {};
          officeState.addAgent(id, m.palette ?? (id - 1) % 6, m.hueShift ?? 0, m.seatId, true);
        }
      }

      // Agent created
      else if (msg.type === 'agentCreated') {
        const id = msg.id;
        const meta = AGENT_METADATA[id];
        officeState.addAgent(id, msg.palette ?? (id - 1) % 6, msg.hueShift ?? 0, undefined, true);
        addTimelineEvent(meta?.name || `Agent ${id}`, 'AGENT_CREATED', 'Joined virtual workspace.');
      }

      // Agent team info
      else if (msg.type === 'agentTeamInfo') {
        officeState.setTeamInfo(msg.id, msg.teamName, msg.agentName, msg.isTeamLead, msg.leadAgentId);
      }

      // Agent status update (active / idle)
      else if (msg.type === 'agentStatus') {
        const id = msg.id;
        const isActive = msg.status === 'active';
        officeState.setAgentActive(id, isActive);
        if (msg.awaitingInput) {
          officeState.showWaitingBubble(id, true);
        } else {
          officeState.dismissBubble(id);
        }

        setAgents((prev) =>
          prev.map((a) => {
            if (a.id === id) {
              return {
                ...a,
                status: isActive ? 'working' : 'idle',
                isAwaitingInput: msg.awaitingInput,
              };
            }
            return a;
          })
        );
      }

      // Tool execution start
      else if (msg.type === 'agentToolStart') {
        const id = msg.id;
        const meta = AGENT_METADATA[id];
        officeState.setAgentTool(id, msg.toolName || msg.status);

        setAgents((prev) =>
          prev.map((a) => {
            if (a.id === id) {
              return {
                ...a,
                status: 'working',
                currentTask: msg.status,
                currentTool: msg.toolName,
                isPermissionActive: Boolean(msg.permissionActive),
              };
            }
            return a;
          })
        );

        addTimelineEvent(meta?.name || `Agent ${id}`, 'TASK_STARTED', `${msg.toolName || 'Tool'}: ${msg.status}`);
      }

      // Tool execution done
      else if (msg.type === 'agentToolDone' || msg.type === 'agentToolsClear') {
        const id = msg.id;
        const meta = AGENT_METADATA[id];
        officeState.setAgentTool(id, null);

        setAgents((prev) =>
          prev.map((a) => {
            if (a.id === id) {
              return {
                ...a,
                currentTask: undefined,
                currentTool: undefined,
                isPermissionActive: false,
              };
            }
            return a;
          })
        );

        if (msg.type === 'agentToolDone') {
          addTimelineEvent(meta?.name || `Agent ${id}`, 'TASK_COMPLETED', `Finished execution (${msg.toolId}).`);
        }
      }

      // Permission required
      else if (msg.type === 'agentToolPermission') {
        const id = msg.id;
        const meta = AGENT_METADATA[id];
        officeState.showPermissionBubble(id);

        setAgents((prev) =>
          prev.map((a) => (a.id === id ? { ...a, status: 'waiting_approval', isPermissionActive: true } : a))
        );

        addTimelineEvent(meta?.name || `Agent ${id}`, 'APPROVAL_REQUIRED', 'Waiting for human manager sign-off.');
        refreshPendingApprovals();
      }

      // Permission cleared
      else if (msg.type === 'agentToolPermissionClear') {
        const id = msg.id;
        officeState.clearPermissionBubble(id);

        setAgents((prev) =>
          prev.map((a) => (a.id === id ? { ...a, isPermissionActive: false } : a))
        );
        refreshPendingApprovals();
      }

      // Agent movement
      else if (msg.type === 'agentMoveTo') {
        const id = msg.id;
        const meta = AGENT_METADATA[id];
        addTimelineEvent(meta?.name || `Agent ${id}`, 'AGENT_MOVING', `Navigating to ${msg.destination}.`);
        if (msg.destination === 'workstation') {
          officeState.sendToSeat(id);
        } else {
          officeState.sendToDestination(id, msg.destination);
        }
        // Dismiss previous bubble on move so it doesn't trail behind or obscure character path
        setSpeechBubbles((prev) => {
          if (!prev[id]) return prev;
          const copy = { ...prev };
          delete copy[id];
          return copy;
        });
      }

      // Agent speech bubble
      else if (msg.type === 'agentSpeechBubble') {
        const id = msg.id;
        const now = Date.now();
        const durationMs = Math.min((msg.durationSec || 4.0), 4.5) * 1000;
        setSpeechBubbles(() => {
          // Enforce single active speaker to eliminate multi-bubble overlap and clutter
          return {
            [id]: {
              id,
              agentId: id,
              message: msg.message,
              kind: msg.kind || 'general',
              expiresAt: now + durationMs,
            },
          };
        });
      }
    });

    const interval = setInterval(refreshPendingApprovals, 5000);

    return () => {
      unsubConn();
      unsubMsg();
      clearInterval(interval);
    };
  }, [officeState, addTimelineEvent, refreshPendingApprovals]);

  // Trigger Multi-Agent Workflow
  const triggerWorkflow = async (skuId = 'YOG-001', sourceStoreId = 'STORE_A', autoApprove = false) => {
    setIsRunningWorkflow(true);
    addTimelineEvent('CEO Agent', 'WORKFLOW_TRIGGERED', `Initiating autonomous recovery for ${skuId} at ${sourceStoreId}.`);
    try {
      const res = await apiFetch('/api/office/workflow/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku_id: skuId, source_store_id: sourceStoreId, auto_approve: autoApprove }),
      });
      if (res.ok) {
        const report = (await res.json()) as CEOOpsReport;
        setLatestReport(report);
        if (report.timeline) {
          setTimeline((prev) => [...report.timeline, ...prev].slice(0, 60));
        }
        await refreshPendingApprovals();
        return report;
      }
    } catch (err) {
      console.error('Workflow trigger failed', err);
    } finally {
      setIsRunningWorkflow(false);
    }
    return null;
  };

  // Submit Approval Decision
  const submitApprovalDecision = async (approvalId: string, decision: 'APPROVED' | 'REJECTED', approver = 'Manager') => {
    try {
      const res = await apiFetch('/api/office/approval/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_id: approvalId, decision, approver }),
      });
      if (res.ok) {
        addTimelineEvent('Manager (Human)', 'APPROVAL_DECISION', `Decision submitted: ${decision} for ${approvalId}`);
        await refreshPendingApprovals();
        return true;
      }
    } catch (err) {
      console.error('Decision submission failed', err);
    }
    return false;
  };

  return {
    connected,
    agents,
    selectedAgentId,
    setSelectedAgentId,
    pendingApprovals,
    timeline,
    latestReport,
    isRunningWorkflow,
    officeState,
    speechBubbles,
    setSpeechBubbles,
    showSpeechBubble,
    triggerWorkflow,
    submitApprovalDecision,
    refreshPendingApprovals,
  };
}
