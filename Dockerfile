FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY linkedin_decision_maker_extractor.py .
COPY cli.py .

# Make CLI script executable
RUN chmod +x cli.py

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the CLI by default
ENTRYPOINT ["python", "cli.py"]

# Default command line arguments (can be overridden)
CMD ["--help"]