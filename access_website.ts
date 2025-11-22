const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: false }); // see it happen
  const page = await browser.newPage();

  await page.goto("http://localhost:3000");

  // Collect every visible, enabled button
  const buttonLocators = page.locator("button:visible, [role='button']:visible");
  const count = await buttonLocators.count();
  console.log(`Found ${count} interactive buttons.`);

  for (let i = 0; i < count; i++) {
    try {
      const button = buttonLocators.nth(i);
      const label = await button.innerText();
      console.log(`Clicking button #${i + 1}: "${label}"`);

      // Take a small screenshot before each click (optional)
      await page.screenshot({ path: `button-${i + 1}-before.png` });

      await button.click({ timeout: 5000 });

      // Wait briefly after click to see effects
      await page.waitForTimeout(1500);

      // Screenshot after click
      await page.screenshot({ path: `button-${i + 1}-after.png`, fullPage: true });
    } catch (err) {
      if (err instanceof Error) {
        console.warn(`Error clicking button #${i + 1}:`, err.message);
      }
    }
  }

  await browser.close();
})();