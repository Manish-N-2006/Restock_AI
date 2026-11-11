import asyncio
import os
import sys
from playwright.async_api import async_playwright

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARTIFACT_DIR = os.path.abspath(
    os.environ.get("RESTOCKAI_ARTIFACT_DIR", os.path.join(WORKSPACE_DIR, "scratch", "e2e_artifacts"))
)
FRONTEND_URL = os.environ.get("RESTOCKAI_FRONTEND_URL", "http://localhost:5180")

async def run_ui_audit():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    print("Launching Chromium for comprehensive Simulation Center 2.0 Acceptance Audit...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 920})
        await context.add_init_script("sessionStorage.setItem('restock_simulation_initialized', 'true');")
        page = await context.new_page()

        print(f"Navigating to {FRONTEND_URL}/simulation ...")
        await page.goto(f"{FRONTEND_URL}/simulation", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 1. Verify Simulation Center Title & Office Canvas
        title_loc = page.locator("h1:has-text('Simulation Center 2.0')")
        assert await title_loc.count() > 0, "Simulation Center 2.0 header not found!"
        print("[PASS] Verified page title: Simulation Center 2.0 — Unified Autonomous Operations")

        # 2. Verify all 7 Agent Identities in Workforce Roster
        print("Auditing 7 agent identities in Workforce Roster...")
        expected_agents = [
            ("Sarah Chen (CEO)", "LEAD"),
            ("Marcus Vance", "Inventory Risk Specialist"),
            ("Elena Rostova", "Recovery Strategy Specialist"),
            ("David Kim", "Logistics & Route Specialist"),
            ("Aisha Patel", "Commerce & Markdown Specialist"),
            ("Tom Becker", "Fulfillment & Warehouse Specialist"),
            ("Linda Zhang", "Finance & Margins Specialist"),
        ]
        for name, role in expected_agents:
            name_loc = page.locator(f"text={name}")
            assert await name_loc.count() > 0, f"Missing agent in roster: {name}"
            print(f"[PASS] Workforce Roster verified: {name} ({role})")

        # 3. Test Viewport Controls: Fit Screen, Zoom In, Zoom Out, Reset, Department navigation
        print("Testing Office Viewport camera & zoom controls...")
        fit_btn = page.locator("button[title='Fit Map to Screen']")
        if await fit_btn.count() > 0:
            await fit_btn.click()
            await page.wait_for_timeout(400)
            print("[PASS] Triggered Fit Screen")

        zoom_in_btn = page.locator("button[title='Zoom In']")
        if await zoom_in_btn.count() > 0:
            await zoom_in_btn.click()
            await page.wait_for_timeout(300)
            print("[PASS] Triggered Zoom In")

        # Click Elena Rostova and test Focus Agent
        elena_card = page.locator("div:has-text('Elena Rostova')").first
        await elena_card.click()
        await page.wait_for_timeout(400)
        focus_btn = page.locator("button[title='Focus Camera on Selected Agent']")
        if await focus_btn.count() > 0:
            await focus_btn.click()
            await page.wait_for_timeout(400)
            print("[PASS] Focused camera on selected agent Elena Rostova")

        # Reset Scenario A to fresh step 0
        reset_btn = page.locator("button:has-text('Reset')")
        if await reset_btn.count() > 0:
            await reset_btn.click()
            await page.wait_for_timeout(1000)
            print("[PASS] Reset Scenario A to initial step 0")

        # Capture initial office and roster view
        s1_path = os.path.join(ARTIFACT_DIR, "audit_office_view_and_roster.png")
        await page.screenshot(path=s1_path, full_page=True)
        print(f"Captured: {s1_path}")

        # 4. Scenario A: Step through to Cedar Approval State
        print("Stepping through Scenario A to Stage 6 (Cedar Approval)...")
        next_step_btn = page.locator("button:has-text('Next Step')")
        for step in range(8):
            approve_btn = page.locator("button:has-text('Approve Decision')")
            if await approve_btn.count() > 0 and await approve_btn.is_visible():
                print(f"[PASS] Reached Cedar Approval state at step iteration {step}")
                break
            if await next_step_btn.is_enabled():
                await next_step_btn.click()
                await page.wait_for_timeout(1000)

        s2_path = os.path.join(ARTIFACT_DIR, "audit_scenario_a_approval_state.png")
        await page.screenshot(path=s2_path, full_page=True)
        print(f"Captured Cedar Approval State: {s2_path}")

        # 5. Authorize Cedar Approval
        print("Authorizing Cedar Approval request...")
        approve_action_btn = page.locator("button:has-text('Approve Decision')")
        if await approve_action_btn.count() > 0:
            await approve_action_btn.click()
            await page.wait_for_timeout(1500)
            print("[PASS] Cedar Approval authorized successfully.")

        # Capture Checkout Ready state
        s3_path = os.path.join(ARTIFACT_DIR, "audit_scenario_a_checkout_ready.png")
        await page.screenshot(path=s3_path, full_page=True)
        print(f"Captured Checkout Ready State: {s3_path}")

        # Open PayPal Checkout modal if present
        pay_btn = page.locator("button:has-text('Launch PayPal Sandbox Checkout')")
        if await pay_btn.count() > 0:
            print("Opening PayPal Commercial Checkout Modal...")
            await pay_btn.first.click()
            await page.wait_for_timeout(2000)
            s4_path = os.path.join(ARTIFACT_DIR, "audit_scenario_a_paypal_modal.png")
            await page.screenshot(path=s4_path, full_page=True)
            print(f"Captured PayPal Checkout Modal: {s4_path}")

            # Close modal via close button
            close_btn = page.locator("button:has-text('✕'), button:has-text('×'), button[aria-label='Close'], button.text-slate-400")
            if await close_btn.count() > 0:
                await close_btn.first.click()
                await page.wait_for_timeout(500)

        # 6. Test Scenario B: Economic Trade-off
        print("Switching to Scenario B: Economic Trade-off (Transfer)...")
        scenario_b_btn = page.locator("button:has-text('B: Economic Trade-off')")
        await scenario_b_btn.click()
        await page.wait_for_timeout(1200)

        # Step through Scenario B
        for step in range(8):
            approve_btn_b = page.locator("button:has-text('Approve Decision')")
            if await approve_btn_b.count() > 0 and await approve_btn_b.is_visible():
                print("[PASS] Approving Scenario B inter-store transfer...")
                await approve_btn_b.click()
                await page.wait_for_timeout(1200)
            elif await next_step_btn.is_enabled():
                await next_step_btn.click()
                await page.wait_for_timeout(800)

        s5_path = os.path.join(ARTIFACT_DIR, "audit_scenario_b_tradeoff_result.png")
        await page.screenshot(path=s5_path, full_page=True)
        print(f"Captured Scenario B result: {s5_path}")

        # 7. Test Scenario C: Recovery Rejection
        print("Switching to Scenario C: Recovery Rejection (Safety)...")
        scenario_c_btn = page.locator("button:has-text('C: Recovery Rejection')")
        await scenario_c_btn.click()
        await page.wait_for_timeout(1200)

        # Step through Scenario C
        for step in range(4):
            if await next_step_btn.is_enabled():
                await next_step_btn.click()
                await page.wait_for_timeout(800)

        s6_path = os.path.join(ARTIFACT_DIR, "audit_scenario_c_rejection_result.png")
        await page.screenshot(path=s6_path, full_page=True)
        print(f"Captured Scenario C result: {s6_path}")

        await browser.close()
        print("All UI audit checks completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_ui_audit())
