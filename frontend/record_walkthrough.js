const { chromium } = require('playwright');

(async () => {
  console.log("Starting browser to record dashboard walkthrough...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    recordVideo: {
      dir: './walkthrough_video/',
      size: { width: 1280, height: 720 }
    },
    viewport: { width: 1280, height: 720 }
  });
  const page = await context.newPage();

  const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  try {
    console.log("Navigating to Dashboard...");
    await page.goto('http://localhost:3000');
    await wait(4000);
    
    // Scroll down to the archetypes section
    await page.evaluate(() => window.scrollBy({ top: 500, behavior: 'smooth' }));
    await wait(3000);
    
    // Click the first archetype card
    console.log("Clicking into the first archetype...");
    await page.click('.archetype-card');
    await wait(4000);
    
    // We are now on the Archetype details page. The "Evidence" tab is selected by default.
    console.log("Showing Evidence tab...");
    await page.evaluate(() => window.scrollBy({ top: 400, behavior: 'smooth' }));
    await wait(3000);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    await wait(2000);
    
    // Click Statistics tab
    console.log("Switching to Statistics tab...");
    await page.click('button:has-text("Statistics")');
    await wait(2000);
    await page.evaluate(() => window.scrollBy({ top: 300, behavior: 'smooth' }));
    await wait(3000);
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
    await wait(2000);
    
    // Click Related Themes tab
    console.log("Switching to Related Themes tab...");
    await page.click('button:has-text("Related Themes")');
    await wait(2000);
    await page.evaluate(() => window.scrollBy({ top: 300, behavior: 'smooth' }));
    await wait(3000);
    
  } catch (err) {
    console.error("Error during recording:", err);
  } finally {
    console.log("Closing browser and saving video...");
    await context.close();
    await browser.close();
    console.log("Video saved to frontend/walkthrough_video directory");
  }
})();
