const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

async function run() {
  const outputDir = "D:\\CA_app_videos";
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  const browser = await chromium.launch({
    headless: true,
    slowMo: 150,
  });

  const context = await browser.newContext({
    viewport: { width: 1366, height: 768 },
    recordVideo: {
      dir: outputDir,
      size: { width: 1366, height: 768 },
    },
  });

  const page = await context.newPage();

  try {
    await page.goto("http://127.0.0.1:3000", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);
    await page.mouse.wheel(0, 450);
    await page.waitForTimeout(1500);
    await page.mouse.wheel(0, -450);
    await page.waitForTimeout(1000);

    const chatInput = page.locator('input[placeholder*="Ask about"]');
    if ((await chatInput.count()) > 0) {
      await chatInput.fill("What is my net profit?");
      await page.click("button:has-text('Send')");
      await page.waitForTimeout(3500);
    }

    await page.goto("http://127.0.0.1:3000/compliance", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2000);

    await page.goto("http://127.0.0.1:3000/reports", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2000);

    await page.evaluate(() => localStorage.setItem("role", "admin"));
    await page.goto("http://127.0.0.1:3000/admin/rates", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);

    await page.goto("http://127.0.0.1:8000/docs", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(2500);
    await page.mouse.wheel(0, 700);
    await page.waitForTimeout(1200);

    await page.goto("http://127.0.0.1:8000/pnl/1", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1800);

    await page.goto("http://127.0.0.1:8000/balance-sheet/1", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1800);

    await page.goto("http://127.0.0.1:8000/financial-health/1", {
      waitUntil: "domcontentloaded",
    });
    await page.waitForTimeout(1800);

    await page.goto("http://127.0.0.1:3000", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(3000);

    const rawVideoPath = await page.video().path();
    await context.close();
    await browser.close();

    const targetPath = path.join(outputDir, `webapp_walkthrough_${Date.now()}.webm`);
    fs.copyFileSync(rawVideoPath, targetPath);
    console.log(targetPath);
    return;
  } catch (error) {
    await context.close();
    await browser.close();
    throw error;
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
