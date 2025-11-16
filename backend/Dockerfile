FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libasound2-dev \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Create directories for audio files and transcriptions
RUN mkdir -p audio_recordings transcriptions vosk_models

# Download Vosk model
# Use Python to create directory, download ZIP, extract, and remove ZIP
RUN python -c "import os, urllib.request, zipfile, io; \
url = 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'; \
target_dir = 'vosk_models'; \
os.makedirs(target_dir, exist_ok=True); \
print(f'Downloading {url}...'); \
r = urllib.request.urlopen(url); \
data = r.read(); \
r.close(); \
z = zipfile.ZipFile(io.BytesIO(data)); \
z.extractall(target_dir); \
z.close()"

# Install uv for faster Python package management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Copy and make entrypoint executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Run the application via entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]