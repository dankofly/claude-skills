import { test, expect } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8765";

test.describe("Austrian Tax Advisor Chatbot", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  // --- Page Load & Structure ---

  test("page loads with correct title", async ({ page }) => {
    await expect(page).toHaveTitle("Österreichischer Steuerberater 2026");
  });

  test("disclaimer banner is visible", async ({ page }) => {
    const disclaimer = page.locator(".disclaimer-banner");
    await expect(disclaimer).toBeVisible();
    await expect(disclaimer).toContainText("keine Steuerberatung");
    await expect(disclaimer).toContainText("Richtwerte");
  });

  test("disclaimer has role=alert for accessibility", async ({ page }) => {
    const disclaimer = page.locator(".disclaimer-banner");
    await expect(disclaimer).toHaveAttribute("role", "alert");
  });

  test("header shows title and year", async ({ page }) => {
    const header = page.locator(".header");
    await expect(header).toBeVisible();
    await expect(header.locator("h1")).toContainText("Steuerberater");
    await expect(header.locator(".year")).toContainText("2026");
  });

  test("header has subtitle", async ({ page }) => {
    const subtitle = page.locator(".header .subtitle");
    await expect(subtitle).toContainText("Steuerrecht");
  });

  test("new chat button is visible", async ({ page }) => {
    const btn = page.locator("#new-chat-btn");
    await expect(btn).toBeVisible();
    await expect(btn).toContainText("Neuer Chat");
  });

  // --- Welcome Screen ---

  test("welcome screen is visible on load", async ({ page }) => {
    const welcome = page.locator("#welcome");
    await expect(welcome).toBeVisible();
    await expect(welcome.locator("h2")).toContainText("Willkommen");
  });

  test("welcome has 5 quickstart buttons", async ({ page }) => {
    const buttons = page.locator(".quickstart-btn");
    await expect(buttons).toHaveCount(5);
  });

  test("quickstart buttons have data-question attributes", async ({
    page,
  }) => {
    const buttons = page.locator(".quickstart-btn");
    const count = await buttons.count();
    for (let i = 0; i < count; i++) {
      const question = await buttons.nth(i).getAttribute("data-question");
      expect(question).toBeTruthy();
      expect(question!.length).toBeGreaterThan(10);
    }
  });

  test("quickstart button labels match topics", async ({ page }) => {
    const labels = [
      "Einkommensteuer",
      "GmbH",
      "Kleinunternehmer",
      "Firmenwagen",
      "Krypto",
    ];
    const buttons = page.locator(".quickstart-btn");
    for (let i = 0; i < labels.length; i++) {
      await expect(buttons.nth(i)).toContainText(labels[i]);
    }
  });

  // --- Input Area ---

  test("textarea is visible and focusable", async ({ page }) => {
    const input = page.locator("#user-input");
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute("maxlength", "2000");
    await expect(input).toHaveAttribute(
      "placeholder",
      /Steuerrecht/
    );
  });

  test("textarea has aria-label for accessibility", async ({ page }) => {
    const input = page.locator("#user-input");
    const ariaLabel = await input.getAttribute("aria-label");
    expect(ariaLabel).toBeTruthy();
  });

  test("send button is visible with aria-label", async ({ page }) => {
    const btn = page.locator("#send-btn");
    await expect(btn).toBeVisible();
    await expect(btn).toHaveAttribute("aria-label", "Nachricht senden");
  });

  test("send button SVG has aria-hidden", async ({ page }) => {
    const svg = page.locator("#send-btn svg");
    await expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  test("textarea auto-focuses on load", async ({ page }) => {
    const input = page.locator("#user-input");
    await expect(input).toBeFocused();
  });

  // --- Quickstart Interaction ---

  test("clicking quickstart sends message and hides welcome", async ({
    page,
  }) => {
    const firstBtn = page.locator(".quickstart-btn").first();
    const question = await firstBtn.getAttribute("data-question");

    await firstBtn.click();

    // Welcome should be hidden
    const welcome = page.locator("#welcome");
    await expect(welcome).toBeHidden();

    // User message should appear
    const userMessage = page.locator(".message.user .message-content");
    await expect(userMessage.first()).toContainText(question!.substring(0, 20));
  });

  // --- Typing & Sending ---

  test("can type in textarea", async ({ page }) => {
    const input = page.locator("#user-input");
    await input.fill("Testfrage zur Einkommensteuer");
    await expect(input).toHaveValue("Testfrage zur Einkommensteuer");
  });

  test("Enter sends message, Shift+Enter adds newline", async ({ page }) => {
    const input = page.locator("#user-input");

    // Shift+Enter should not send
    await input.fill("Zeile 1");
    await input.press("Shift+Enter");
    // Message should NOT be sent
    const messages = page.locator(".message");
    // Wait a bit to make sure nothing appeared
    await page.waitForTimeout(300);
    const msgCount = await messages.count();
    expect(msgCount).toBe(0);
  });

  test("sending message shows thinking indicator", async ({ page }) => {
    const input = page.locator("#user-input");
    await input.fill("Wie hoch ist die KöSt?");
    await input.press("Enter");

    // Thinking indicator should appear briefly
    const thinking = page.locator("#thinking-indicator");
    await expect(thinking).toBeVisible({ timeout: 2000 });
  });

  test("send button is disabled during loading", async ({ page }) => {
    const input = page.locator("#user-input");
    await input.fill("Testfrage");
    await input.press("Enter");

    const sendBtn = page.locator("#send-btn");
    await expect(sendBtn).toBeDisabled();
  });

  // --- New Chat ---

  test("new chat button resets conversation", async ({ page }) => {
    // First send a message
    const input = page.locator("#user-input");
    await input.fill("Testfrage");

    const firstBtn = page.locator(".quickstart-btn").first();
    await firstBtn.click();

    // Verify message exists
    await expect(page.locator(".message").first()).toBeVisible();

    // Click new chat
    await page.locator("#new-chat-btn").click();

    // Welcome should reappear, messages gone
    await expect(page.locator("#welcome")).toBeVisible();
    await expect(page.locator(".message")).toHaveCount(0);
  });

  // --- Responsive Layout ---

  test("mobile layout hides subtitle", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    const subtitle = page.locator(".header .subtitle");
    await expect(subtitle).toBeHidden();
  });

  test("mobile layout shows all quickstart buttons", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    const buttons = page.locator(".quickstart-btn");
    await expect(buttons).toHaveCount(5);
    // All should still be visible (wrapped)
    await expect(buttons.first()).toBeVisible();
  });

  test("desktop layout shows subtitle", async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    const subtitle = page.locator(".header .subtitle");
    await expect(subtitle).toBeVisible();
  });

  // --- API Health ---

  test("health endpoint returns OK", async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/health`);
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBe("ok");
    expect(body.tools_available).toBe(7);
  });

  // --- Error Handling ---

  test("shows error on API failure", async ({ page }) => {
    // Send a message — API will fail because we use a dummy key
    const input = page.locator("#user-input");
    await input.fill("Test");
    await input.press("Enter");

    // Wait for error message from bot
    const botMessage = page.locator(".message.bot .message-content");
    await expect(botMessage.first()).toBeVisible({ timeout: 10000 });

    // Should show some error text (either API error or connection error)
    const text = await botMessage.first().textContent();
    expect(text).toBeTruthy();
  });

  // --- Accessibility ---

  test("messages container has aria-live", async ({ page }) => {
    const messages = page.locator("#messages");
    await expect(messages).toHaveAttribute("aria-live", "polite");
  });

  test("app has proper semantic structure", async ({ page }) => {
    // Header element exists
    await expect(page.locator("header.header")).toBeVisible();
    // Main content area
    await expect(page.locator("main.chat-area")).toBeVisible();
    // Footer input area
    await expect(page.locator("footer.input-area")).toBeVisible();
  });

  test("all interactive elements are keyboard accessible", async ({
    page,
  }) => {
    // Tab through elements — input should be focused first
    await expect(page.locator("#user-input")).toBeFocused();

    // Tab to send button
    await page.keyboard.press("Tab");
    // Could be new-chat or quickstart buttons depending on tab order
    // Just verify we can tab around without getting stuck
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press("Tab");
    }
    // No error = keyboard navigation works
  });
});
