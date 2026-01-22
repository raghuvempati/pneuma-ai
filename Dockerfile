# Use the official Ray base image (includes Ray and Python)
FROM rayproject/ray:2.9.0-py310

USER root

# Install system libs for Nebula/Qdrant clients if needed
RUN apt-get update && apt-get install -y build-essential curl

USER ray
WORKDIR /home/ray/pneuma

# Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Source Code
# The directory structure is crucial for Python imports to work across the cluster
COPY src/ src/
COPY main.py .

# Set Python path so 'src' is discoverable
ENV PYTHONPATH="${PYTHONPATH}:/home/ray/pneuma"