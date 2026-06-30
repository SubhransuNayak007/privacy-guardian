import os
from roboflow import Roboflow

def main():
    # To download the dataset, you need a Roboflow API key.
    # You can get a free one by signing up at roboflow.com
    ROBOFLOW_API_KEY = os.environ.get("ROBOFLOW_API_KEY", "YOUR_ROBOFLOW_API_KEY")
    
    if ROBOFLOW_API_KEY == "YOUR_ROBOFLOW_API_KEY":
        print("ERROR: Please set your ROBOFLOW_API_KEY environment variable or edit this file to add it.")
        print("You can get a free API key at https://app.roboflow.com")
        return

    print("Initializing Roboflow...")
    rf = Roboflow(api_key=ROBOFLOW_API_KEY)
    
    # Replace these with the specific dataset you find on Roboflow Universe
    workspace_name = "your-workspace-name" 
    project_name = "your-project-name"
    version_number = 1

    try:
        project = rf.workspace(workspace_name).project(project_name)
        version = project.version(version_number)
        
        # Download the dataset in YOLOv8 format
        print("Downloading dataset...")
        dataset = version.download("yolov8")
        print(f"Dataset successfully downloaded to {dataset.location}")
    except Exception as e:
        print(f"Failed to download dataset: {e}")

if __name__ == "__main__":
    main()
