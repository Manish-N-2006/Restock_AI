import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Set, Optional
from fastapi import WebSocket

from .events import (
    AgentSeatMeta,
    ExistingAgents,
    AgentCreated,
    AgentClosed,
    AgentStatus,
    AgentToolStart,
    AgentToolDone,
    AgentToolsClear,
    AgentToolPermission,
    AgentToolPermissionClear,
    AgentTeamInfo,
    AgentMoveTo,
    AgentSpeechBubble,
    LayoutLoaded,
    FurnitureAssetsLoaded,
    FloorTilesLoaded,
    WallTilesLoaded,
    CarpetTilesLoaded,
    CharacterSpritesLoaded,
    ProviderCapabilities,
)

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


class AgentState:
    def __init__(
        self,
        id: int,
        name: str,
        department: str,
        palette: int = 0,
        hue_shift: int = 0,
        seat_id: Optional[str] = None,
        is_team_lead: bool = False,
    ):
        self.id = id
        self.name = name
        self.department = department
        self.palette = palette
        self.hue_shift = hue_shift
        self.seat_id = seat_id
        self.is_team_lead = is_team_lead
        self.status: str = "waiting"  # "active" or "waiting"
        self.awaiting_input: bool = False
        self.current_tool: Optional[Dict[str, Any]] = None
        self.permission_active: bool = False

    def to_meta(self) -> AgentSeatMeta:
        return AgentSeatMeta(
            palette=self.palette,
            hueShift=self.hue_shift,
            seatId=self.seat_id,
        )


class OfficeService:
    def __init__(self):
        self.active_websockets: Set[WebSocket] = set()
        self.websocket_sessions: Dict[WebSocket, str] = {}
        
        # Load assets from json cache
        self.characters_assets = self._load_json("characters.json", [])
        self.floors_assets = self._load_json("floors.json", [])
        self.walls_assets = self._load_json("walls.json", [])
        self.carpets_assets = self._load_json("carpets.json", [])
        self.furniture_sprites = self._load_json("furniture_sprites.json", {})
        self.furniture_catalog = self._load_json("furniture_catalog.json", [])
        self.default_layout = self._load_json("default_layout.json", None)

        # Initialize Default Workforce (CEO + 6 Specialists)
        self.agents: Dict[int, AgentState] = {}
        self._init_default_workforce()

        # Tools that show reading book/doc animation instead of typing
        self.reading_tools = [
            "get_inventory_risk",
            "search_historical_recovery",
            "get_transfer_status",
            "InspectStock",
            "AuditRisk",
            "ReviewSLA",
            "AnalyzeDemand",
        ]

    def _load_json(self, filename: str, fallback: Any) -> Any:
        path = os.path.join(ASSETS_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
        return fallback

    def _init_default_workforce(self):
        workforce = [
            AgentState(1, "Sarah Chen (CEO)", "Executive Operations", palette=0, is_team_lead=True, seat_id="seat-ceo"),
            AgentState(2, "Marcus Vance (Inventory)", "Inventory Management", palette=1, seat_id="seat-inventory"),
            AgentState(3, "Elena Rostova (Strategy)", "Recovery Strategy", palette=2, seat_id="seat-recovery"),
            AgentState(4, "David Kim (Logistics)", "Logistics & Dispatch", palette=3, seat_id="seat-logistics"),
            AgentState(5, "Aisha Patel (Commerce)", "Commerce & Sales", palette=4, seat_id="seat-commerce"),
            AgentState(6, "Tom Becker (Fulfillment)", "Warehouse & Transit", palette=5, seat_id="seat-fulfillment"),
            AgentState(7, "Linda Zhang (Finance)", "Finance & Settlement", palette=1, hue_shift=140, seat_id="seat-finance"),
        ]
        for a in workforce:
            self.agents[a.id] = a

    async def connect(self, websocket: WebSocket, session_jti: Optional[str] = None):
        await websocket.accept()
        self.active_websockets.add(websocket)
        if session_jti:
            self.websocket_sessions[websocket] = session_jti
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_websockets)}")
        
        # Send complete initial hydration sequence
        try:
            await self._send_initial_hydration(websocket)
        except Exception as e:
            logger.error(f"Error during hydration: {e}")
            await self.disconnect(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_websockets.discard(websocket)
        self.websocket_sessions.pop(websocket, None)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_websockets)}")

    async def close_sessions_by_jti(self, jti: str):
        """Actively close all live WebSocket connections bound to a logged-out session JTI."""
        if not jti:
            return
        matching = [ws for ws, ws_jti in list(self.websocket_sessions.items()) if ws_jti == jti]
        for ws in matching:
            self.active_websockets.discard(ws)
            self.websocket_sessions.pop(ws, None)
            try:
                await ws.close(code=1008, reason="Session logged out")
            except Exception as exc:
                logger.debug("Ignoring close error for logged-out WebSocket: %s", exc)

    async def broadcast(self, message: Any):
        payload = message.model_dump() if hasattr(message, "model_dump") else message
        payload_str = json.dumps(payload)
        
        dead_sockets = []
        sockets = list(self.active_websockets)

        for ws in sockets:
            try:
                await asyncio.wait_for(ws.send_text(payload_str), timeout=0.5)
            except Exception as e:
                logger.warning(f"Error broadcasting to client: {e}")
                dead_sockets.append(ws)

        if dead_sockets:
            for ws in dead_sockets:
                self.active_websockets.discard(ws)

    async def _send_initial_hydration(self, websocket: WebSocket):
        # 1. Provider Capabilities
        await websocket.send_text(
            ProviderCapabilities(
                readingTools=self.reading_tools,
                subagentToolNames=["Task", "Agent", "Collaborate"],
            ).model_dump_json()
        )

        # 2. Pre-decoded tile and character assets
        if self.characters_assets:
            await websocket.send_text(CharacterSpritesLoaded(characters=self.characters_assets).model_dump_json())
        if self.floors_assets:
            await websocket.send_text(FloorTilesLoaded(sprites=self.floors_assets).model_dump_json())
        if self.walls_assets:
            await websocket.send_text(WallTilesLoaded(sets=self.walls_assets).model_dump_json())
        if self.carpets_assets:
            await websocket.send_text(CarpetTilesLoaded(sets=self.carpets_assets).model_dump_json())
        if self.furniture_catalog and self.furniture_sprites:
            await websocket.send_text(
                FurnitureAssetsLoaded(
                    catalog=self.furniture_catalog,
                    sprites=self.furniture_sprites,
                ).model_dump_json()
            )

        # 3. Existing agents roster
        agent_ids = list(self.agents.keys())
        agent_meta = {str(k): v.to_meta() for k, v in self.agents.items()}
        dir_names = {str(k): v.department for k, v in self.agents.items()}

        await websocket.send_text(
            ExistingAgents(
                agents=agent_ids,
                agentMeta=agent_meta,
                directoryNames=dir_names,
            ).model_dump_json()
        )

        # 4. Agent Team Metadata
        for agent in self.agents.values():
            await websocket.send_text(
                AgentTeamInfo(
                    id=agent.id,
                    teamName="ReStockAI Autonomous Workforce",
                    agentName=agent.name,
                    isTeamLead=agent.is_team_lead,
                    leadAgentId=1 if not agent.is_team_lead else None,
                ).model_dump_json()
            )

        # 5. Layout loaded (Triggers canvas creation and seat allocation in webview)
        await websocket.send_text(
            LayoutLoaded(layout=self.default_layout).model_dump_json()
        )

        # 6. Settings loaded
        await websocket.send_text(
            json.dumps({
                "type": "settingsLoaded",
                "soundEnabled": False,
                "extensionVersion": "1.3.0",
                "lastSeenVersion": "1.2",
                "showAreas": True,
            })
        )

        # 7. Replay active agent states (active status, running tools, permission alerts)
        for agent in self.agents.values():
            if agent.status == "active":
                await websocket.send_text(AgentStatus(id=agent.id, status="active").model_dump_json())
                if agent.current_tool:
                    await websocket.send_text(AgentToolStart(**agent.current_tool).model_dump_json())
            elif agent.awaiting_input:
                await websocket.send_text(AgentStatus(id=agent.id, status="waiting", awaitingInput=True).model_dump_json())

            if agent.permission_active:
                await websocket.send_text(AgentToolPermission(id=agent.id).model_dump_json())

    async def send_hydration(self, websocket: WebSocket):
        """Public method to deliver full hydration to a client upon webviewReady request."""
        await self._send_initial_hydration(websocket)

    def update_seats(self, seats: Dict[str, Any]):
        """Persist seat positions reported by the office frontend."""
        for agent_id_str, seat_id in seats.items():
            try:
                aid = int(agent_id_str)
                if aid in self.agents:
                    self.agents[aid].seat_id = str(seat_id)
            except (ValueError, TypeError):
                pass

    # --- Live State Management & Event Broadcasting ---

    async def set_agent_active(self, agent_id: int, is_active: bool, awaiting_input: bool = False):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = "active" if is_active else "waiting"
            agent.awaiting_input = awaiting_input
            status_event = AgentStatus(
                id=agent_id,
                status="active" if is_active else "waiting",
                awaitingInput=awaiting_input,
            )
            await self.broadcast(status_event)

    async def start_tool(
        self,
        agent_id: int,
        tool_id: str,
        status: str,
        tool_name: Optional[str] = None,
        permission_active: bool = False,
    ):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = "active"
            tool_data = {
                "id": agent_id,
                "toolId": tool_id,
                "status": status,
                "toolName": tool_name or tool_id,
                "permissionActive": permission_active,
            }
            agent.current_tool = tool_data
            
            # First activate character so they walk to desk
            await self.broadcast(AgentStatus(id=agent_id, status="active"))
            # Then start tool
            await self.broadcast(AgentToolStart(**tool_data))

    async def done_tool(self, agent_id: int, tool_id: str):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.current_tool = None
            await self.broadcast(AgentToolDone(id=agent_id, toolId=tool_id))

    async def clear_tools(self, agent_id: int):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.current_tool = None
            await self.broadcast(AgentToolsClear(id=agent_id))

    async def set_permission(self, agent_id: int, required: bool):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.permission_active = required
            if required:
                await self.broadcast(AgentToolPermission(id=agent_id))
            else:
                await self.broadcast(AgentToolPermissionClear(id=agent_id))

    async def move_agent_to(self, agent_id: int, destination: str):
        """Send an agent to a specific destination ('workstation', 'conference', 'approval', 'breakroom', 'ceo_briefing', 'ceo_reporting')."""
        if agent_id in self.agents:
            await self.broadcast(AgentMoveTo(id=agent_id, destination=destination))

    async def send_speech_bubble(
        self,
        agent_id: int,
        message: str,
        kind: str = "general",
        duration_sec: float = 4.0,
    ):
        """Broadcast a floating speech bubble event to be rendered over the agent avatar."""
        if agent_id in self.agents:
            await self.broadcast(
                AgentSpeechBubble(
                    id=agent_id,
                    message=message,
                    kind=kind,
                    durationSec=duration_sec,
                )
            )

    async def reset_agent_idle(self, agent_id: int):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = "waiting"
            agent.awaiting_input = False
            agent.current_tool = None
            agent.permission_active = False
            await self.broadcast(AgentToolsClear(id=agent_id))
            await self.broadcast(AgentToolPermissionClear(id=agent_id))
            await self.broadcast(AgentStatus(id=agent_id, status="waiting", awaitingInput=False))

    async def reset_all(self):
        for agent_id in self.agents:
            await self.reset_agent_idle(agent_id)


# Global Singleton Service instance
office_service = OfficeService()
