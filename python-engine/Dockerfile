FROM python:3.12-slim

# Create a non-root user that Hugging Face Spaces requires
RUN useradd -m -u 1000 user

WORKDIR /app

# Install system dependencies for OpenCV and other packages
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code and give ownership to the non-root user
COPY --chown=user:user . .

# Switch to the non-root user
USER user

# Set Hugging Face environment variables
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# Hugging Face mandates exposing port 7860
EXPOSE 7860

# Command to run the application on port 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
