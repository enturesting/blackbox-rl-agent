const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    console.log('Navigating to http://localhost:3000/home...');
    await page.goto('http://localhost:3000/home');
    
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    // Take a screenshot
    await page.screenshot({ path: 'screenshot.png' });
    console.log('Screenshot saved to screenshot.png');
    
    // Get some content to prove access
    const content = await page.content();
    console.log('Page content length:', content.length);
    
  } catch (error) {
    console.error('Error accessing website:', error);
  } finally {
    await browser.close();
  }
})();

