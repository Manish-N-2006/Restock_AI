from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class AgentSeatMeta(BaseModel):
    palette: Optional[int] = 0
    hueShift: Optional[int] = 0
    seatId: Optional[str] = None


class ExistingAgents(BaseModel):
    type: Literal["existingAgents"] = "existingAgents"
    agents: List[int]
    agentMeta: Dict[str, AgentSeatMeta]
    directoryNames: Dict[str, str] = Field(default_factory=dict)
    externalAgents: Dict[str, bool] = Field(default_factory=dict)


class AgentCreated(BaseModel):
    type: Literal["agentCreated"] = "agentCreated"
    id: int
    directoryName: Optional[str] = None
    isExternal: Optional[bool] = False
    palette: Optional[int] = 0
    hueShift: Optional[int] = 0


class AgentClosed(BaseModel):
    type: Literal["agentClosed"] = "agentClosed"
    id: int


class AgentStatus(BaseModel):
    type: Literal["agentStatus"] = "agentStatus"
    id: int
    status: Literal["active", "waiting"]
    awaitingInput: Optional[bool] = False


class AgentToolStart(BaseModel):
    type: Literal["agentToolStart"] = "agentToolStart"
    id: int
    toolId: str
    status: str
    toolName: Optional[str] = None
    permissionActive: Optional[bool] = False
    runInBackground: Optional[bool] = False
    isTeammateSpawn: Optional[bool] = False


class AgentToolDone(BaseModel):
    type: Literal["agentToolDone"] = "agentToolDone"
    id: int
    toolId: str


class AgentToolsClear(BaseModel):
    type: Literal["agentToolsClear"] = "agentToolsClear"
    id: int


class AgentToolPermission(BaseModel):
    type: Literal["agentToolPermission"] = "agentToolPermission"
    id: int


class AgentToolPermissionClear(BaseModel):
    type: Literal["agentToolPermissionClear"] = "agentToolPermissionClear"
    id: int


class SubagentToolStart(BaseModel):
    type: Literal["subagentToolStart"] = "subagentToolStart"
    id: int
    parentToolId: str
    toolId: str
    status: str


class SubagentToolDone(BaseModel):
    type: Literal["subagentToolDone"] = "subagentToolDone"
    id: int
    parentToolId: str
    toolId: str


class SubagentClear(BaseModel):
    type: Literal["subagentClear"] = "subagentClear"
    id: int
    parentToolId: str


class AgentTeamInfo(BaseModel):
    type: Literal["agentTeamInfo"] = "agentTeamInfo"
    id: int
    teamName: Optional[str] = None
    agentName: Optional[str] = None
    isTeamLead: Optional[bool] = False
    leadAgentId: Optional[int] = None
    teamUsesTmux: Optional[bool] = False


class AgentMoveTo(BaseModel):
    type: Literal["agentMoveTo"] = "agentMoveTo"
    id: int
    destination: Literal["workstation", "conference", "approval", "breakroom", "ceo_briefing", "ceo_reporting"]


class AgentSpeechBubble(BaseModel):
    type: Literal["agentSpeechBubble"] = "agentSpeechBubble"
    id: int
    message: str
    kind: Literal["instruction", "working", "reporting", "approval", "success", "failure", "general"] = "general"
    durationSec: Optional[float] = 6.0


class LayoutLoaded(BaseModel):
    type: Literal["layoutLoaded"] = "layoutLoaded"
    layout: Optional[Dict[str, Any]] = None
    wasReset: Optional[bool] = False


class FurnitureAssetsLoaded(BaseModel):
    type: Literal["furnitureAssetsLoaded"] = "furnitureAssetsLoaded"
    catalog: List[Dict[str, Any]]
    sprites: Dict[str, Any]


class FloorTilesLoaded(BaseModel):
    type: Literal["floorTilesLoaded"] = "floorTilesLoaded"
    sprites: List[Any]


class WallTilesLoaded(BaseModel):
    type: Literal["wallTilesLoaded"] = "wallTilesLoaded"
    sets: List[Any]


class CarpetTilesLoaded(BaseModel):
    type: Literal["carpetTilesLoaded"] = "carpetTilesLoaded"
    sets: List[Any]


class CharacterSpritesLoaded(BaseModel):
    type: Literal["characterSpritesLoaded"] = "characterSpritesLoaded"
    characters: List[Any]


class ProviderCapabilities(BaseModel):
    type: Literal["providerCapabilities"] = "providerCapabilities"
    readingTools: List[str] = Field(default_factory=list)
    subagentToolNames: List[str] = Field(default_factory=list)

