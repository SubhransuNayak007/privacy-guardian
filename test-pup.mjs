import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));

  console.log('Navigating to http://localhost:3000');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle2' });

  // Simulate file upload with an image
  console.log('Simulating file upload...');
  const inputUploadHandle = await page.$('input[type=file]');
  
  if (inputUploadHandle) {
    // We need an image. We can create a fake dummy image file
    const fs = await import('fs/promises');
    const path = await import('path');
    
    // Create a dummy image
    const base64Image = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
    const buffer = Buffer.from(base64Image, 'base64');
    await fs.writeFile('dummy.png', buffer);
    
    console.log('Uploading dummy.png...');
    await inputUploadHandle.uploadFile('dummy.png');
    
    console.log('Waiting for scanning to finish...');
    // The page will transition to /preview/:id, then scanning happens.
    // Let's just wait to see any console errors that pop up!
    await new Promise(r => setTimeout(r, 10000));
  } else {
    console.log('File input not found');
  }

  await browser.close();
})();
