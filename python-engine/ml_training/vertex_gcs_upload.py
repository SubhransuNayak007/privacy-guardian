import os
from google.cloud import storage

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """
    Uploads a file to Google Cloud Storage so it can be used by Vertex AI.
    """
    # Initialize the GCS client. This requires GOOGLE_APPLICATION_CREDENTIALS 
    # to be set in your environment variables.
    try:
        storage_client = storage.Client()
    except Exception as e:
        print("Failed to initialize Google Cloud client.")
        print("Did you set GOOGLE_APPLICATION_CREDENTIALS pointing to your service account JSON?")
        print(f"Error: {e}")
        return

    # Check if bucket exists, if not, create it
    bucket = storage_client.bucket(bucket_name)
    if not bucket.exists():
        print(f"Bucket {bucket_name} does not exist. Creating it...")
        try:
            # Create bucket in the standard multi-region (e.g. US)
            bucket = storage_client.create_bucket(bucket_name, location="US")
            print(f"Bucket {bucket.name} created.")
        except Exception as e:
            print(f"Failed to create bucket: {e}")
            return

    # Upload the file
    print(f"Uploading {source_file_name} to {bucket_name}/{destination_blob_name}...")
    blob = bucket.blob(destination_blob_name)
    
    try:
        # We upload as application/jsonl so Vertex AI can read it properly
        blob.upload_from_filename(source_file_name, content_type='application/jsonl')
        print(f"File {source_file_name} successfully uploaded.")
        print(f"GCS URI: gs://{bucket_name}/{destination_blob_name}")
        print("\nNext Steps for Vertex AI:")
        print("1. Go to Google Cloud Console -> Vertex AI -> Model Garden.")
        print("2. Select a base model (e.g., Llama-3 or Gemini).")
        print("3. Click 'Fine-tune' and provide the GCS URI shown above as your training data!")
    except Exception as e:
        print(f"Failed to upload file: {e}")

if __name__ == "__main__":
    # You must set your GCP Project environment variable:
    # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/your/credentials.json"
    
    # Define your globally unique bucket name and local dataset file
    my_bucket_name = "vertex-ai-training-datasets-12345" # Must be unique across all GCP
    local_dataset_path = "datasets/qlora_train.jsonl"
    gcs_destination_path = "qlora_train.jsonl"
    
    if not os.path.exists(local_dataset_path):
        print(f"Error: Could not find {local_dataset_path}. Please run prepare_qlora_data.py first.")
    else:
        upload_to_gcs(my_bucket_name, local_dataset_path, gcs_destination_path)
