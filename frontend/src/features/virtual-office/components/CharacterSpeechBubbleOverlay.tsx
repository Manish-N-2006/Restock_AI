import React, { useEffect, useState, useRef } from 'react';
import { OfficeState } from '../office/engine/officeState';
import { CharacterState } from '../office/types';
import { AgentSpeechBubbleItem } from '../types/office';
import {
  MessageSquare,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Brain,
} from 'lucide-react';

interface CharacterSpeechBubbleOverlayProps {
  officeState: OfficeState;
  zoom: number;
  panRef: React.MutableRefObject<{ x: number; y: number }>;
  speechBubbles: Record<number, AgentSpeechBubbleItem>;
  onDismissBubble?: (agentId: number) => void;
}

interface BubbleRenderData {
  agentId: number;
  screenX: number;
  screenY: number;
  offsetX: number;
  charCenterX: number;
  charFeetScreenY: number;
  charHeadScreenY: number;
  pointerDirection: 'down' | 'left' | 'right';
  bubble: AgentSpeechBubbleItem;
}

const AGENT_NAMES: Record<number, string> = {
  1: 'Sarah Chen (CEO)',
  2: 'Marcus Vance (Inventory)',
  3: 'Elena Rostova (Strategy)',
  4: 'David Kim (Logistics)',
  5: 'Aisha Patel (Commerce)',
  6: 'Tom Becker (Fulfillment)',
  7: 'Linda Zhang (Finance)',
};

export const CharacterSpeechBubbleOverlay: React.FC<CharacterSpeechBubbleOverlayProps> = ({
  officeState,
  zoom,
  panRef,
  speechBubbles,
  onDismissBubble,
}) => {
  const [positions, setPositions] = useState<BubbleRenderData[]>([]);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;

    const updateBubblePositions = () => {
      const now = Date.now();
      const rawPositions: BubbleRenderData[] = [];

      Object.values(speechBubbles).forEach((bubble) => {
        if (now > bubble.expiresAt) return;

        const char = officeState.characters.get(bubble.agentId);
        if (!char) return;

        const pan = panRef.current;
        const isSeated = char.state === CharacterState.TYPE;
        const sittingOffset = isSeated ? 6 : 0;

        // char.x is the center of the character in world coordinates
        const charCenterX = Math.round(pan.x + char.x * zoom);

        // Accurate sprite dimensions (renderer draws sprite with cached.height = 32 * zoom)
        const spriteHeight = 32 * zoom;
        const charFeetScreenY = Math.round(pan.y + (char.y + sittingOffset) * zoom);
        const charHeadScreenY = Math.round(charFeetScreenY - spriteHeight);

        // Safe clearance gap between character head and bottom of bubble pointer
        // Guaranteed minimum 18px clearance so the pointer and bubble NEVER touch or hide the character
        const clearanceGap = Math.max(18, Math.round(12 * zoom));
        const targetAboveScreenY = Math.round(charHeadScreenY - clearanceGap);

        let screenX = charCenterX;
        let screenY = targetAboveScreenY;
        let offsetX = 0;
        let pointerDirection: 'down' | 'left' | 'right' = 'down';

        // Check if character is too close to top boundary of the canvas (< 85px)
        // If so, NEVER flip downward over other rooms or characters!
        // Instead, shift horizontally right next to the character with clear side clearance!
        if (targetAboveScreenY < 85) {
          // Determine side based on position so bubble never clips off-screen
          const shiftLeft = charCenterX > 260;
          const sideOffset = Math.round(8 * zoom + 16);
          pointerDirection = shiftLeft ? 'right' : 'left';
          offsetX = shiftLeft ? -sideOffset : sideOffset;
          // Vertically center alongside head/shoulders, clamped cleanly away from top edge
          screenY = Math.max(46, Math.round(charHeadScreenY + 10 * zoom));
        } else {
          // Ensure wide bubbles above don't clip off left edge of canvas while keeping arrow aimed at head
          if (charCenterX < 110) {
            offsetX = 110 - charCenterX;
          }
        }

        rawPositions.push({
          agentId: bubble.agentId,
          screenX,
          screenY,
          offsetX,
          charCenterX,
          charFeetScreenY,
          charHeadScreenY,
          pointerDirection,
          bubble,
        });
      });

      // Avoid horizontal collision if multiple bubbles ever render simultaneously
      if (rawPositions.length >= 2) {
        for (let i = 0; i < rawPositions.length; i++) {
          for (let j = i + 1; j < rawPositions.length; j++) {
            const b1 = rawPositions[i];
            const b2 = rawPositions[j];
            const dx = (b2.screenX + b2.offsetX) - (b1.screenX + b1.offsetX);
            const dy = Math.abs(b2.screenY - b1.screenY);

            if (Math.abs(dx) < 170 && dy < 60) {
              const shift = 45;
              if (dx >= 0) {
                b1.offsetX -= shift;
                b2.offsetX += shift;
              } else {
                b1.offsetX += shift;
                b2.offsetX -= shift;
              }
            }
          }
        }
      }

      if (active) {
        setPositions(rawPositions);
        animFrameRef.current = requestAnimationFrame(updateBubblePositions);
      }
    };

    animFrameRef.current = requestAnimationFrame(updateBubblePositions);

    return () => {
      active = false;
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [officeState, zoom, panRef, speechBubbles]);

  if (positions.length === 0) return null;

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-20">
      {/* 1. Speaking Character Spotlight Halo - renders at character's feet so the agent is vividly visible */}
      {positions.map(({ agentId, charCenterX, charFeetScreenY, bubble }) => {
        const isApproval = bubble.kind === 'approval';
        const ringBorder = isApproval
          ? 'border-rose-400 bg-rose-500/20 shadow-[0_0_16px_rgba(244,63,94,0.7)]'
          : 'border-emerald-400 bg-emerald-400/20 shadow-[0_0_16px_rgba(52,211,153,0.7)]';

        return (
          <div
            key={`spotlight-${agentId}`}
            style={{
              left: `${charCenterX}px`,
              top: `${charFeetScreenY - 4}px`,
              transform: 'translate(-50%, -50%)',
              width: `${Math.round(26 * Math.max(zoom, 1))}px`,
              height: `${Math.round(13 * Math.max(zoom, 1))}px`,
            }}
            className={`absolute rounded-full border ${ringBorder} animate-pulse pointer-events-none z-10`}
          />
        );
      })}

      {/* 2. Floating On-Character Speech Bubble - guaranteed clearance above character */}
      {positions.map(({ agentId, screenX, screenY, offsetX, pointerDirection, bubble }) => {
        const isInstruction = bubble.kind === 'instruction';
        const isWorking = bubble.kind === 'working';
        const isReporting = bubble.kind === 'reporting';
        const isApproval = bubble.kind === 'approval';
        const isFailure = bubble.kind === 'failure';

        let badgeBg = 'bg-slate-900/85 text-slate-200 border-slate-700/80 shadow-slate-950/60';
        let badgeIcon = <MessageSquare className="w-2.5 h-2.5 text-slate-400" />;
        let title = 'Message';

        if (isInstruction) {
          badgeBg = 'bg-indigo-950/85 text-indigo-200 border-indigo-500/60 shadow-indigo-950/60';
          badgeIcon = <Brain className="w-2.5 h-2.5 text-indigo-400 animate-pulse" />;
          title = 'CEO Briefing';
        } else if (isWorking) {
          badgeBg = 'bg-amber-950/85 text-amber-200 border-amber-500/60 shadow-amber-950/60';
          badgeIcon = <Sparkles className="w-2.5 h-2.5 text-amber-400 animate-spin" />;
          title = 'Specialist Task';
        } else if (isReporting) {
          badgeBg = 'bg-emerald-950/85 text-emerald-200 border-emerald-500/60 shadow-emerald-950/60';
          badgeIcon = <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />;
          title = 'Report to CEO';
        } else if (isApproval) {
          badgeBg = 'bg-rose-950/90 text-rose-200 border-rose-500/70 shadow-rose-950/70 animate-pulse';
          badgeIcon = <ShieldAlert className="w-2.5 h-2.5 text-rose-400" />;
          title = 'Human Approval';
        } else if (isFailure) {
          badgeBg = 'bg-red-950/90 text-red-200 border-red-500/70 shadow-red-950/70';
          badgeIcon = <AlertTriangle className="w-2.5 h-2.5 text-red-400" />;
          title = 'Alert';
        }

        const agentName = AGENT_NAMES[agentId] || `Agent ${agentId}`;
        const arrowOffset = -offsetX;

        // Transform logic depending on pointer direction
        let containerTransform = 'translate(-50%, -100%)';
        if (pointerDirection === 'right') {
          containerTransform = 'translate(-100%, -50%)';
        } else if (pointerDirection === 'left') {
          containerTransform = 'translate(0%, -50%)';
        }

        return (
          <div
            key={agentId}
            style={{
              left: `${screenX + offsetX}px`,
              top: `${screenY}px`,
              transform: containerTransform,
            }}
            className="absolute transition-transform duration-100 pointer-events-auto z-20"
          >
            <div
              className={`relative max-w-[190px] sm:max-w-[205px] min-w-[130px] rounded-lg px-2.5 py-1.5 text-xs backdrop-blur-md border shadow-2xl flex flex-col gap-1 animate-in fade-in zoom-in-95 duration-150 ${badgeBg}`}
            >
              {/* Header Badge */}
              <div className="flex items-center justify-between gap-1 border-b border-white/10 pb-0.5">
                <div className="flex items-center gap-1 font-bold uppercase tracking-wider text-[8.5px] truncate">
                  {badgeIcon}
                  <span className="truncate">{title} &bull; {agentName.split(' ')[0]}</span>
                </div>
                {onDismissBubble && (
                  <button
                    onClick={() => onDismissBubble(agentId)}
                    className="text-white/60 hover:text-white cursor-pointer text-xs leading-none px-0.5"
                    title="Dismiss"
                  >
                    &times;
                  </button>
                )}
              </div>

              {/* Message Content */}
              <p className="font-medium text-slate-100 text-[10px] leading-tight break-words">
                {bubble.message}
              </p>

              {/* Dynamic pointer arrow triangle pointing towards character */}
              {pointerDirection === 'down' && (
                <div
                  className="absolute bottom-0 w-2.5 h-2.5 bg-inherit border-r border-b border-inherit rotate-45"
                  style={{
                    left: `calc(50% + ${arrowOffset}px)`,
                    transform: 'translate(-50%, 50%)',
                  }}
                />
              )}
              {pointerDirection === 'right' && (
                <div
                  className="absolute right-0 top-1/2 w-2.5 h-2.5 bg-inherit border-t border-r border-inherit rotate-45"
                  style={{
                    transform: 'translate(50%, -50%)',
                  }}
                />
              )}
              {pointerDirection === 'left' && (
                <div
                  className="absolute left-0 top-1/2 w-2.5 h-2.5 bg-inherit border-b border-l border-inherit rotate-45"
                  style={{
                    transform: 'translate(-50%, -50%)',
                  }}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
