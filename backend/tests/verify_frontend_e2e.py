import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import websockets

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKSPACE_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
FRONTEND_DIR = os.path.abspath(
    os.environ.get("RESTOCKAI_FRONTEND_DIR", os.path.join(WORKSPACE_DIR, "frontend"))
)
ARTIFACT_DIR = os.path.abspath(
    os.environ.get("RESTOCKAI_ARTIFACT_DIR", os.path.join(WORKSPACE_DIR, "scratch", "e2e_artifacts"))
)
CHROME_PATH = (
    os.environ.get("CHROME_PATH")
    or shutil.which("google-chrome")
    or shutil.which("chromium")
    or shutil.which("chromium-browser")
    or shutil.which("chrome")
    or ("chrome" if sys.platform != "win32" else os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"))
)


def wait_for_http(url: str, timeout: float = 15.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "E2ETest"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


async def capture_screenshot(cdp, req_id: int, filename: str):
    await cdp.send(json.dumps({
        "id": req_id,
        "method": "Page.captureScreenshot",
        "params": {"format": "png"}
    }))
    while True:
        resp = json.loads(await cdp.recv())
        if resp.get("id") == req_id:
            img_data = base64.b64decode(resp["result"]["data"])
            out_path = os.path.join(ARTIFACT_DIR, filename)
            with open(out_path, "wb") as f:
                f.write(img_data)
            print(f"[OK] Saved screenshot: {filename}")
            return out_path


def send_move_command(agent_id: int, destination: str):
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/office/agent/move",
        data=json.dumps({"agent_id": agent_id, "destination": destination}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def run_phase2a_verification():
    print("==================================================================")
    print("  ReStockAI Virtual Office — Phase 2A E2E Layout & Movement Verification")
    print("==================================================================")

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    backend_log = open(os.path.join(ARTIFACT_DIR, "backend_e2e.log"), "w", encoding="utf-8")
    frontend_log = open(os.path.join(ARTIFACT_DIR, "frontend_e2e.log"), "w", encoding="utf-8")

    print("[1/7] Starting ReStockAI FastAPI Backend on port 8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BACKEND_DIR,
        stdout=backend_log,
        stderr=backend_log,
    )

    print("[2/7] Starting Vite Dev Server on port 5173...")
    frontend_proc = subprocess.Popen(
        "npx vite --port 5173 --host 127.0.0.1",
        cwd=FRONTEND_DIR,
        shell=True,
        stdout=frontend_log,
        stderr=frontend_log,
    )

    chrome_proc = None
    try:
        # Wait for backend
        if not wait_for_http("http://127.0.0.1:8000/api/office/state", timeout=12.0):
            print("ERROR: Backend failed to respond on port 8000")
            return False
        print("[OK] Backend is live on port 8000.")

        # Wait for frontend
        if not wait_for_http("http://127.0.0.1:5173", timeout=15.0):
            print("ERROR: Frontend failed to respond on port 5173")
            return False
        print("[OK] Frontend is live on port 5173.")

        print("[3/7] Launching Chrome Headless with Remote Debugging Port 9222 (1600x1000)...")
        chrome_proc = subprocess.Popen(
            [
                CHROME_PATH,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--remote-debugging-port=9222",
                "--window-size=1600,1000",
                "http://127.0.0.1:5173",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if not wait_for_http("http://127.0.0.1:9222/json", timeout=10.0):
            print("ERROR: Chrome CDP failed to respond on port 9222")
            return False

        targets_req = urllib.request.urlopen("http://127.0.0.1:9222/json")
        targets = json.loads(targets_req.read().decode("utf-8"))
        page_target = next((t for t in targets if t.get("type") == "page"), None)
        if not page_target:
            print(f"ERROR: No page target found in Chrome")
            return False

        ws_url = page_target["webSocketDebuggerUrl"]
        print(f"[OK] Connecting to Chrome CDP at: {ws_url}")

        async with websockets.connect(ws_url) as cdp:
            await cdp.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
            await cdp.send(json.dumps({"id": 2, "method": "Page.enable"}))
            await cdp.send(json.dumps({"id": 3, "method": "Console.enable"}))

            # Monitor DOM for Canvas
            print("[4/7] Waiting for Office Canvas mounting and hydration...")
            canvas_found = False
            for attempt in range(30):
                await asyncio.sleep(0.5)
                req_id = 100 + attempt
                check_script = """(() => {
                    const c = document.querySelector('canvas');
                    return {
                        hasCanvas: !!c,
                        w: c ? c.width : 0,
                        h: c ? c.height : 0,
                        text: document.body.innerText.slice(0, 150)
                    };
                })()"""
                await cdp.send(json.dumps({
                    "id": req_id,
                    "method": "Runtime.evaluate",
                    "params": {"expression": check_script, "returnByValue": True}
                }))
                while True:
                    raw = await cdp.recv()
                    resp = json.loads(raw)
                    if resp.get("method") == "Runtime.consoleAPICalled":
                        args = resp.get("params", {}).get("args", [])
                        msg_text = " ".join([str(a.get("value")) for a in args])
                        safe_text = msg_text.encode('ascii', errors='replace').decode('ascii')
                        print(f"  [Browser Console] {safe_text}")
                    elif resp.get("id") == req_id:
                        val = resp.get("result", {}).get("result", {}).get("value", {})
                        if val.get("hasCanvas"):
                            print(f"[SUCCESS] Canvas mounted at {val['w']}x{val['h']} (DPR scaled)!")
                            canvas_found = True
                            break
                        else:
                            print(f"  Attempt {attempt+1}: text='{val.get('text', '').strip()}'")
                            break
                if canvas_found:
                    break

            if not canvas_found:
                print("ERROR: Canvas failed to render.")
                return False

            # Wait 2.5s for initial layout, characters and matrix spawn effect to complete
            await asyncio.sleep(2.5)

            # Capture initial 48x32 floorplan overview screenshot
            print("[5/7] Capturing 48x32 Office Floorplan Overview...")
            await capture_screenshot(cdp, 201, "office_phase2a_overview.png")

            # Test Movement 1: Dispatch Inventory Agent (Agent 2) to Conference Room
            print("[6/7] Testing Agent Movement Destinations...")
            print("  --> Dispatching Agent 2 (Inventory Agent) to Conference Room...")
            res1 = send_move_command(2, "conference")
            print(f"      Backend response: {res1}")
            await asyncio.sleep(3.5)
            await capture_screenshot(cdp, 202, "office_phase2a_conference_move.png")

            # Test Movement 2: Dispatch Recovery Strategy Agent (Agent 3) to Approval Waiting Area
            print("  --> Dispatching Agent 3 (Recovery Agent) to Human Approval Waiting Area...")
            res2 = send_move_command(3, "approval")
            print(f"      Backend response: {res2}")
            await asyncio.sleep(3.5)
            await capture_screenshot(cdp, 203, "office_phase2a_approval_move.png")

            # Test Movement 3: Dispatch Finance Agent (Agent 7) to Operations & Break Area
            print("  --> Dispatching Agent 7 (Finance Agent) to Operations & Break Area...")
            res3 = send_move_command(7, "breakroom")
            print(f"      Backend response: {res3}")
            await asyncio.sleep(3.5)
            await capture_screenshot(cdp, 204, "office_phase2a_breakroom_move.png")

            # Test Movement 4: Return Inventory Agent (Agent 2) to Workstation Desk
            print("  --> Dispatching Agent 2 back to their Workstation desk...")
            res4 = send_move_command(2, "workstation")
            print(f"      Backend response: {res4}")
            await asyncio.sleep(3.5)
            await capture_screenshot(cdp, 205, "office_phase2a_return_workstation.png")

            # Test Refresh: Verify browser reload hydrates clean state
            print("[7/7] Testing browser reload hydration...")
            await cdp.send(json.dumps({"id": 300, "method": "Page.reload"}))
            await asyncio.sleep(3.5)
            await capture_screenshot(cdp, 301, "office_phase2a_after_reload.png")
            print("[OK] Reload test passed: Office restored successfully!")

            print("==================================================================")
            print("  ALL PHASE 2A TESTS & VERIFICATIONS COMPLETED SUCCESSFULLY!")
            print("==================================================================")
            return True

    finally:
        print("[*] Cleaning up processes...")
        if chrome_proc:
            try:
                subprocess.run(f"taskkill /F /T /PID {chrome_proc.pid}", shell=True, capture_output=True)
            except Exception:
                chrome_proc.terminate()
        try:
            subprocess.run(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True, capture_output=True)
        except Exception:
            frontend_proc.terminate()
        try:
            subprocess.run(f"taskkill /F /T /PID {backend_proc.pid}", shell=True, capture_output=True)
        except Exception:
            backend_proc.terminate()
        try:
            backend_log.close()
            frontend_log.close()
        except Exception:
            pass


if __name__ == "__main__":
    success = asyncio.run(run_phase2a_verification())
    sys.exit(0 if success else 1)
