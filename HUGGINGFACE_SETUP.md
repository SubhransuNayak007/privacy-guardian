# Deploying the AI Backend to Hugging Face Spaces

Hugging Face Spaces is the perfect free hosting solution for this heavy AI backend because it gives you **16GB of RAM and 2 CPUs for free**.

Follow these exact steps to move your Python engine to the cloud:

## 1. Create your Space
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and create a free account if you haven't already.
2. Click **Create new Space**.
3. **Space Name:** `privacy-guardian-api` (or whatever you like).
4. **License:** `mit` (or leave blank).
5. **Select the Space SDK:** Choose **Docker** > **Blank**.
6. **Space Hardware:** `Free (2vCPU, 16GB, 50GB)`.
7. Click **Create Space**.

## 2. Upload the Code
Since this is a Docker space, Hugging Face expects the `Dockerfile` to be in the root directory of the Space.

1. On your new Space page, click the **Files** tab.
2. Click **Add file** -> **Upload files**.
3. On your computer, open the `privacy-guardian/python-engine/` folder.
4. **Drag and drop ALL the files and folders** inside `python-engine` directly into the Hugging Face upload window. *(Make sure the `Dockerfile`, `requirements.txt`, and `backend` folder are at the top level!)*
5. Add a commit message and click **Commit changes to main**.

## 3. Wait for the Build
Hugging Face will automatically see your `Dockerfile` and start building the container.
- It will download PyTorch, PaddleOCR, YOLO, etc.
- This will take about **5 to 10 minutes** the first time.
- You can click the **Logs** button to watch it build!

## 4. Connect Vercel to your new Space!
Once your Space is built and shows "Running", you will get a direct URL to your space. 
It usually looks like this: `https://yourusername-privacy-guardian-api.hf.space`

1. Go to your **Vercel Dashboard** -> Your Project -> **Settings** -> **Environment Variables**.
2. Add a new variable:
   - **Key:** `PYTHON_API_URL`
   - **Value:** `https://yourusername-privacy-guardian-api.hf.space` (Replace with your actual Space URL)
3. Click **Save** and then trigger a **Redeploy** on Vercel.

**That's it!** Your Vercel frontend is now permanently connected to a robust, cloud-hosted AI backend. You will never see a "503 Tunnel Unavailable" error again!
