import asyncio
from playwright.async_api import async_playwright
from roboflow import Roboflow
import os

ROBOFLOW_API_KEY = os.environ.get("ROBOFLOW_API_KEY", "YOUR_ROBOFLOW_API_KEY")

async def scrape_and_download():
    if ROBOFLOW_API_KEY == "YOUR_ROBOFLOW_API_KEY":
        print("ERROR: Please set your ROBOFLOW_API_KEY environment variable to download datasets.")
        return

    url = "https://universe.roboflow.com/search?q=class%3Aadress"
    
    print("Launching headless browser to bypass Roboflow anti-bot...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print(f"Navigating to {url}...")
        await page.goto(url)
        
        # Wait for the project cards to load
        print("Waiting for dataset results to load...")
        try:
            await page.wait_for_selector('a[href*="/"]', timeout=15000)
        except Exception:
            print("Timeout waiting for page to load. Roboflow might require a captcha.")
            await browser.close()
            return
            
        # Scroll to load more (simplified)
        await page.evaluate("window.scrollBy(0, 2000)")
        await page.wait_for_timeout(2000)
        
        # Extract href links which contain workspace and project (e.g. /workspace-name/project-name)
        links = await page.evaluate('''() => {
            const anchors = Array.from(document.querySelectorAll('a'));
            return anchors.map(a => a.getAttribute('href')).filter(h => h && h.split('/').length === 3);
        }''')
        
        await browser.close()
        
        # Deduplicate and clean
        projects = list(set([l for l in links if l.startswith("/")]))
        print(f"Found {len(projects)} dataset projects matching the search.")
        
        rf = Roboflow(api_key=ROBOFLOW_API_KEY)
        for proj_path in projects[:5]: # Limiting to first 5 to save disk space for demo
            try:
                _, workspace, project_name = proj_path.split("/")
                print(f"Downloading {workspace}/{project_name}...")
                project = rf.workspace(workspace).project(project_name)
                # COCO format is best for VLM fine-tuning because it has rich JSON metadata
                dataset = project.version(1).download("coco") 
                print(f"Successfully downloaded to {dataset.location}")
            except Exception as e:
                print(f"Failed to download {proj_path}: {e}")

if __name__ == "__main__":
    asyncio.run(scrape_and_download())
