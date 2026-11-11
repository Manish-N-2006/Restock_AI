import React, { useRef, useEffect, useState, useCallback } from 'react';
import { OfficeState } from '../office/engine/officeState';
import { renderFrame } from '../office/engine/renderer';
import { startGameLoop } from '../office/engine/gameLoop';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Scan,
  Compass,
  Wifi,
  WifiOff,
  UserCheck,
  RotateCcw,
} from 'lucide-react';
import { AgentSpeechBubbleItem } from '../types/office';
import { CharacterSpeechBubbleOverlay } from './CharacterSpeechBubbleOverlay';

interface VirtualOfficeCanvasProps {
  officeState: OfficeState;
  connected: boolean;
  selectedAgentId: number | null;
  onSelectAgent: (agentId: number) => void;
  className?: string;
  speechBubbles?: Record<number, AgentSpeechBubbleItem>;
  onDismissBubble?: (agentId: number) => void;
}

export const VirtualOfficeCanvas: React.FC<VirtualOfficeCanvasProps> = ({
  officeState,
  connected,
  selectedAgentId,
  onSelectAgent,
  className,
  speechBubbles = {},
  onDismissBubble,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [zoom, setZoom] = useState(2.0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const panRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const hasInitializedFitRef = useRef(false);

  // Helper: Clamp pan to guarantee office map cannot be lost off-screen
  const clampPan = useCallback(
    (px: number, py: number, currentZoom: number, viewW: number, viewH: number) => {
      const layout = officeState.getLayout();
      const mapW = layout.cols * 16 * currentZoom;
      const mapH = layout.rows * 16 * currentZoom;

      // Keep at least 25% of the office inside the viewport
      const minVisibleX = Math.min(viewW * 0.25, mapW * 0.25);
      const minVisibleY = Math.min(viewH * 0.25, mapH * 0.25);

      const minPanX = minVisibleX - mapW;
      const maxPanX = viewW - minVisibleX;
      const minPanY = minVisibleY - mapH;
      const maxPanY = viewH - minVisibleY;

      return {
        x: Math.round(Math.max(minPanX, Math.min(maxPanX, px))),
        y: Math.round(Math.max(minPanY, Math.min(maxPanY, py))),
      };
    },
    [officeState]
  );

  // 1. Fit to Screen calculation
  const handleFitToScreen = useCallback(() => {
    if (!containerRef.current) return;
    const { clientWidth: viewW, clientHeight: viewH } = containerRef.current;
    if (viewW <= 0 || viewH <= 0) return;

    const layout = officeState.getLayout();
    const mapW = layout.cols * 16;
    const mapH = layout.rows * 16;

    // Calculate fit scale with padding
    const paddingX = 48;
    const paddingY = 48;
    const scaleX = (viewW - paddingX) / mapW;
    const scaleY = (viewH - paddingY) / mapH;
    const fitScale = Math.max(1.0, Math.min(4.0, Math.min(scaleX, scaleY)));

    // Center map
    const centeredX = Math.round((viewW - mapW * fitScale) / 2);
    const centeredY = Math.round((viewH - mapH * fitScale) / 2);

    officeState.cameraFollowId = null;
    setZoom(fitScale);
    panRef.current = clampPan(centeredX, centeredY, fitScale, viewW, viewH);
  }, [officeState, clampPan]);

  // 2. Focus on selected agent character
  const handleFocusSelectedAgent = useCallback(() => {
    if (selectedAgentId === null || !containerRef.current) return;
    const char = officeState.characters.get(selectedAgentId);
    if (!char) return;

    const { clientWidth: viewW, clientHeight: viewH } = containerRef.current;
    const targetX = viewW / 2 - char.x * zoom;
    const targetY = viewH / 2 - char.y * zoom;

    officeState.cameraFollowId = selectedAgentId;
    panRef.current = clampPan(targetX, targetY, zoom, viewW, viewH);
  }, [selectedAgentId, officeState, zoom, clampPan]);

  // Camera follow effect when selectedAgentId changes externally (e.g. from Roster click)
  useEffect(() => {
    if (selectedAgentId !== null) {
      officeState.cameraFollowId = selectedAgentId;
      officeState.selectedAgentId = selectedAgentId;
    }
  }, [selectedAgentId, officeState]);

  // 3. ResizeObserver on container to resize canvas & preserve crisp pixel art
  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const width = container.clientWidth;
      const height = container.clientHeight;
      if (width <= 0 || height <= 0) return;

      const displayW = Math.round(width * dpr);
      const displayH = Math.round(height * dpr);

      if (canvas.width !== displayW || canvas.height !== displayH) {
        canvas.width = displayW;
        canvas.height = displayH;
      }

      // Re-clamp pan within new dimensions
      panRef.current = clampPan(panRef.current.x, panRef.current.y, zoom, width, height);

      // Fit to screen on initial mount
      if (!hasInitializedFitRef.current && width > 100 && height > 100) {
        hasInitializedFitRef.current = true;
        handleFitToScreen();
      }
    };

    const observer = new ResizeObserver(() => {
      resize();
    });
    observer.observe(container);
    resize();

    return () => {
      observer.disconnect();
    };
  }, [clampPan, zoom, handleFitToScreen]);

  // 4. Fullscreen change listener
  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      // Small timeout to allow container dimensions to settle
      setTimeout(() => {
        handleFitToScreen();
      }, 100);
    };

    document.addEventListener('fullscreenchange', onFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
    };
  }, [handleFitToScreen]);

  const handleToggleFullscreen = async () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      try {
        await containerRef.current.requestFullscreen();
      } catch (err) {
        console.warn('Fullscreen request failed:', err);
      }
    } else {
      try {
        await document.exitFullscreen();
      } catch (err) {
        console.warn('Exit fullscreen failed:', err);
      }
    }
  };

  // 5. Game loop & canvas rendering with smooth camera follow
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const stopLoop = startGameLoop(canvas, {
      update: (dt: number) => {
        officeState.update(dt);
      },
      render: (renderCtx: CanvasRenderingContext2D) => {
        const dpr = window.devicePixelRatio || 1;
        const rect = canvas.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        renderCtx.save();
        renderCtx.scale(dpr, dpr);

        // Guarantee pixel art is crisp and not blurred
        renderCtx.imageSmoothingEnabled = false;

        // Smooth camera follow lerp
        if (officeState.cameraFollowId !== null) {
          const char = officeState.characters.get(officeState.cameraFollowId);
          if (char) {
            const targetX = rect.width / 2 - char.x * zoom;
            const targetY = rect.height / 2 - char.y * zoom;
            const lerpedX = panRef.current.x + (targetX - panRef.current.x) * 0.12;
            const lerpedY = panRef.current.y + (targetY - panRef.current.y) * 0.12;
            panRef.current = clampPan(lerpedX, lerpedY, zoom, rect.width, rect.height);
          }
        }

        const layout = officeState.getLayout();
        const selectionRender = {
          selectedAgentId: officeState.selectedAgentId,
          hoveredAgentId: officeState.hoveredAgentId,
          hoveredTile: officeState.hoveredTile,
          seats: officeState.seats,
          characters: officeState.characters,
        };

        // Render frame with native Pixel Agents engine
        renderFrame(
          renderCtx,
          rect.width,
          rect.height,
          officeState.tileMap,
          officeState.furniture,
          officeState.getCharacters(),
          zoom,
          panRef.current.x,
          panRef.current.y,
          selectionRender,
          undefined, // editorRenderState
          layout.tileColors,
          layout.cols,
          layout.rows,
          layout.carpetTiles,
          layout.areas,
          layout.areaTiles,
          true, // showAreas
          null, // activeAreaLabel
          officeState.pets,
          officeState.areaLabelOffsets,
          officeState.areaBadgeBounds
        );

        renderCtx.restore();
      },
    });

    return () => {
      stopLoop();
    };
  }, [officeState, zoom, clampPan]);

  // 6. Mouse Drag Pan
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (e.button === 0 || e.button === 1) {
      // Left click or Middle click
      isDraggingRef.current = true;
      dragStartRef.current = {
        x: e.clientX - panRef.current.x,
        y: e.clientY - panRef.current.y,
      };
      officeState.cameraFollowId = null; // Unhook camera follow on manual pan
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDraggingRef.current && containerRef.current) {
      const { clientWidth: viewW, clientHeight: viewH } = containerRef.current;
      const rawX = e.clientX - dragStartRef.current.x;
      const rawY = e.clientY - dragStartRef.current.y;
      panRef.current = clampPan(rawX, rawY, zoom, viewW, viewH);
    }
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDraggingRef.current) return;
    isDraggingRef.current = false;

    // Check if it was a quick click without dragging (< 5px drag distance)
    const dist = Math.hypot(
      e.clientX - (dragStartRef.current.x + panRef.current.x),
      e.clientY - (dragStartRef.current.y + panRef.current.y)
    );

    if (dist < 5) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // Convert screen coordinate to office world coordinate
      const worldX = (mouseX - panRef.current.x) / zoom;
      const worldY = (mouseY - panRef.current.y) / zoom;

      // Hit-test agents
      for (const [id, char] of officeState.characters.entries()) {
        const dx = Math.abs(char.x - worldX);
        const dy = Math.abs(char.y - worldY);
        if (dx < 16 && dy < 24) {
          onSelectAgent(id);
          officeState.selectedAgentId = id;
          officeState.cameraFollowId = id;
          return;
        }
      }
    }
  };

  // 7. Cursor-centred Zoom
  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas || !containerRef.current) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // World coordinate under cursor before zoom
    const worldX = (mouseX - panRef.current.x) / zoom;
    const worldY = (mouseY - panRef.current.y) / zoom;

    // Smooth zoom factor
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
    const newZoom = Math.min(Math.max(zoom * zoomFactor, 1.0), 4.5);

    // Adjust pan so that (worldX, worldY) stays anchored under cursor
    const targetPanX = mouseX - worldX * newZoom;
    const targetPanY = mouseY - worldY * newZoom;

    officeState.cameraFollowId = null; // Unhook camera follow on manual zoom
    setZoom(newZoom);
    panRef.current = clampPan(targetPanX, targetPanY, newZoom, rect.width, rect.height);
  };

  const handleZoomIn = () => {
    if (!containerRef.current) return;
    const { clientWidth: viewW, clientHeight: viewH } = containerRef.current;
    const centerX = viewW / 2;
    const centerY = viewH / 2;
    const worldX = (centerX - panRef.current.x) / zoom;
    const worldY = (centerY - panRef.current.y) / zoom;

    const newZoom = Math.min(zoom + 0.35, 4.5);
    const targetPanX = centerX - worldX * newZoom;
    const targetPanY = centerY - worldY * newZoom;

    officeState.cameraFollowId = null;
    setZoom(newZoom);
    panRef.current = clampPan(targetPanX, targetPanY, newZoom, viewW, viewH);
  };

  const handleZoomOut = () => {
    if (!containerRef.current) return;
    const { clientWidth: viewW, clientHeight: viewH } = containerRef.current;
    const centerX = viewW / 2;
    const centerY = viewH / 2;
    const worldX = (centerX - panRef.current.x) / zoom;
    const worldY = (centerY - panRef.current.y) / zoom;

    const newZoom = Math.max(zoom - 0.35, 1.0);
    const targetPanX = centerX - worldX * newZoom;
    const targetPanY = centerY - worldY * newZoom;

    officeState.cameraFollowId = null;
    setZoom(newZoom);
    panRef.current = clampPan(targetPanX, targetPanY, newZoom, viewW, viewH);
  };

  const handleResetView = () => {
    if (!containerRef.current) return;
    const { clientWidth: viewW, clientHeight: viewH } = containerRef.current;
    const layout = officeState.getLayout();
    const mapW = layout.cols * 16 * 2.0;
    const mapH = layout.rows * 16 * 2.0;

    officeState.cameraFollowId = null;
    setZoom(2.0);
    panRef.current = clampPan(
      Math.round((viewW - mapW) / 2),
      Math.round((viewH - mapH) / 2),
      2.0,
      viewW,
      viewH
    );
  };

  // Department quick navigation
  const jumpToDepartment = (col: number, row: number) => {
    officeState.cameraFollowId = null;
    if (containerRef.current) {
      const { clientWidth, clientHeight } = containerRef.current;
      const targetPanX = Math.round(clientWidth / 2 - col * 16 * zoom);
      const targetPanY = Math.round(clientHeight / 2 - row * 16 * zoom);
      panRef.current = clampPan(targetPanX, targetPanY, zoom, clientWidth, clientHeight);
    }
  };

  return (
    <div
      ref={containerRef}
      className={`relative w-full ${
        isFullscreen ? 'h-screen fixed inset-0 z-50 rounded-none' : 'h-[620px] xl:h-[680px] rounded-2xl'
      } bg-[#181a20] overflow-hidden border border-slate-700/80 shadow-2xl select-none transition-all ${
        className || ''
      }`}
    >
      {/* Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        className="w-full h-full cursor-grab active:cursor-grabbing block touch-none"
        style={{ imageRendering: 'pixelated' }}
      />

      {/* Floating On-Character Speech Bubbles */}
      <CharacterSpeechBubbleOverlay
        officeState={officeState}
        zoom={zoom}
        panRef={panRef}
        speechBubbles={speechBubbles}
        onDismissBubble={onDismissBubble}
      />

      {/* Top Left Status & Connection Pill */}
      <div className="absolute top-4 left-4 flex items-center gap-2.5 z-10">
        <div
          className={`px-3 py-1.5 rounded-xl text-xs font-extrabold flex items-center gap-2 backdrop-blur-md border shadow-lg ${
            connected
              ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/40'
              : 'bg-rose-950/80 text-rose-400 border-rose-500/40'
          }`}
        >
          {connected ? (
            <Wifi className="w-3.5 h-3.5 animate-pulse" />
          ) : (
            <WifiOff className="w-3.5 h-3.5" />
          )}
          <span>{connected ? 'LIVE OFFICE CONNECTED' : 'OFFLINE'}</span>
        </div>

        <div className="px-3 py-1.5 rounded-xl bg-slate-900/80 text-slate-300 border border-slate-700/60 backdrop-blur-md text-xs font-bold shadow-lg">
          7 AI Agents Registered
        </div>
      </div>

      {/* Top Right Quick Jump Controls */}
      <div className="absolute top-4 right-4 flex items-center gap-1.5 z-10 bg-slate-900/85 p-1.5 rounded-xl border border-slate-700/80 backdrop-blur-md shadow-xl text-[11px] font-bold text-slate-300">
        <span className="px-2 text-slate-400 flex items-center gap-1">
          <Compass className="w-3.5 h-3.5" /> Rooms:
        </span>
        <button
          onClick={() => jumpToDepartment(8, 6)}
          className="px-2.5 py-1 rounded-lg hover:bg-slate-800 hover:text-white transition-all cursor-pointer"
        >
          CEO Office
        </button>
        <button
          onClick={() => jumpToDepartment(10, 22)}
          className="px-2.5 py-1 rounded-lg hover:bg-slate-800 hover:text-white transition-all cursor-pointer"
        >
          AI Workroom
        </button>
        <button
          onClick={() => jumpToDepartment(32, 6)}
          className="px-2.5 py-1 rounded-lg hover:bg-slate-800 hover:text-white transition-all cursor-pointer"
        >
          Conference
        </button>
        <button
          onClick={() => jumpToDepartment(26, 22)}
          className="px-2.5 py-1 rounded-lg hover:bg-slate-800 hover:text-amber-400 transition-all cursor-pointer"
        >
          Approval Room
        </button>
        <button
          onClick={() => jumpToDepartment(38, 22)}
          className="px-2.5 py-1 rounded-lg hover:bg-slate-800 hover:text-white transition-all cursor-pointer"
        >
          Breakroom
        </button>
      </div>

      {/* Bottom Right Camera, Zoom & Fullscreen Controls Bar */}
      <div className="absolute bottom-4 right-4 flex items-center gap-1.5 z-10 bg-slate-900/90 p-1.5 rounded-xl border border-slate-700/80 backdrop-blur-md shadow-2xl">
        {selectedAgentId !== null && (
          <button
            onClick={handleFocusSelectedAgent}
            title="Focus Camera on Selected Agent"
            className="p-2 text-amber-400 hover:text-amber-300 hover:bg-slate-800 rounded-lg transition-all flex items-center gap-1 text-xs font-semibold cursor-pointer border-r border-slate-700/60 pr-2.5 mr-0.5"
          >
            <UserCheck className="w-4 h-4" />
            <span className="hidden sm:inline">Focus Agent</span>
          </button>
        )}

        <button
          onClick={handleFitToScreen}
          title="Fit Map to Screen"
          className="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-all flex items-center gap-1 text-xs cursor-pointer"
        >
          <Scan className="w-4 h-4" />
          <span className="hidden sm:inline">Fit Screen</span>
        </button>

        <button
          onClick={handleResetView}
          title="Reset Zoom to 200%"
          className="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-all cursor-pointer"
        >
          <RotateCcw className="w-4 h-4" />
        </button>

        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-all cursor-pointer"
        >
          <ZoomIn className="w-4 h-4" />
        </button>

        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-all cursor-pointer"
        >
          <ZoomOut className="w-4 h-4" />
        </button>

        <button
          onClick={handleToggleFullscreen}
          title={isFullscreen ? 'Exit Full Screen' : 'Full Screen'}
          className="p-2 text-emerald-400 hover:text-emerald-300 hover:bg-slate-800 rounded-lg transition-all cursor-pointer"
        >
          {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
        </button>

        <span className="px-2 text-xs font-mono font-bold text-slate-300 border-l border-slate-700/60">
          {(zoom * 100).toFixed(0)}%
        </span>
      </div>

      {/* Drag & Controls Guide Overlay */}
      <div className="absolute bottom-4 left-4 z-10 px-3 py-1.5 rounded-lg bg-black/70 backdrop-blur-sm text-[10px] font-mono text-slate-400 pointer-events-none border border-slate-800 flex items-center gap-3">
        <span>🖱️ Drag to Pan</span>
        <span>🔍 Scroll to Zoom (Cursor Centred)</span>
        <span>🎯 Click Agent to Focus</span>
      </div>
    </div>
  );
};
