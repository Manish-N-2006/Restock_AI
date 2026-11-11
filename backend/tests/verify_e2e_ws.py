import asyncio
import json
import time
import requests
import websockets

BACKEND_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/office"

async def verify_e2e():
    print(f"Connecting to {WS_URL}...")
    async with websockets.connect(WS_URL) as ws:
        print("Connected to WebSocket successfully!")
        
        # 1. Receive and verify initial hydration sequence
        received_types = []
        for _ in range(20):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                msg = json.loads(raw)
                msg_type = msg.get("type")
                received_types.append(msg_type)
                print(f"<- Received Hydration Event: {msg_type}")
                if msg_type == "layoutLoaded":
                    break
            except asyncio.TimeoutError:
                break

        assert "providerCapabilities" in received_types, "Missing providerCapabilities"
        assert "characterSpritesLoaded" in received_types, "Missing characterSpritesLoaded"
        assert "existingAgents" in received_types, "Missing existingAgents"
        assert "layoutLoaded" in received_types, "Missing layoutLoaded"
        print("[OK] Initial state hydration verified!")

        # 2. Trigger task simulation via REST API
        print("\nTriggering simulation sequence via REST API...")
        res = requests.post(
            f"{BACKEND_URL}/api/office/test/simulate-sequence",
            json={
                "agent_id": 2,
                "task_name": "E2E Stock Audit for SKU-104",
                "tool_name": "InspectStock",
                "step_delay_sec": 0.5,
            },
            timeout=5.0
        )
        assert res.status_code == 200, f"Simulate sequence failed: {res.text}"
        print(f"[OK] Simulation triggered: {res.json()}")

        # 3. Stream and verify real-time events over WebSocket
        event_types = []
        print("\nStreaming real-time events from WebSocket...")
        t_end = time.time() + 6.0
        while time.time() < t_end:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                msg = json.loads(raw)
                msg_type = msg.get("type")
                event_types.append(msg_type)
                print(f"<- Live Event: {msg_type} -> {msg}")
                if msg_type == "agentStatus" and msg.get("status") == "waiting":
                    break
            except asyncio.TimeoutError:
                break

        assert "agentStatus" in event_types, "Missing agentStatus event"
        assert "agentToolStart" in event_types, "Missing agentToolStart event"
        assert "agentToolDone" in event_types, "Missing agentToolDone event"
        assert "agentToolsClear" in event_types, "Missing agentToolsClear event"
        print("[OK] All live sequence events received in real time!")
        print("\nALL E2E VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(verify_e2e())
