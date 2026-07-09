# Fireworks AI Agent - Track 1

Autonomous AI agent for the Fireworks AI "General-Purpose AI Agent" challenge.

## Architecture

```
Docker Starts
      │
      ▼
Read Environment Variables
      │
      ├── FIREWORKS_API_KEY
      ├── FIREWORKS_BASE_URL
      └── ALLOWED_MODELS
      │
      ▼
Create Fireworks Client
      │
      ▼
Read /input/tasks.json
      │
      ▼
Route Tasks
      │
      ▼
Call Fireworks
      │
      ▼
Write /output/results.json
      │
      ▼
Exit
```

## Configuration

All configuration is managed through a single `settings` object in `src/config/settings.py`.

### Required Environment Variables

- `FIREWORKS_API_KEY` - Your Fireworks API key
- `FIREWORKS_BASE_URL` - Fireworks API base URL
- `ALLOWED_MODELS` - Comma-separated list of allowed model IDs

### Optional Environment Variables

- `MAX_CONCURRENCY` - Maximum concurrent tasks (default: 10)
- `TIMEOUT` - Request timeout in seconds (default: 60)

### Usage in Code

```python
from src.config import settings

# Access configuration values
api_key = settings.api_key
base_url = settings.base_url
models = settings.allowed_models
```

Never read `os.environ` directly - always import and use the `settings` object.

## Development

```bash
# Install dependencies
uv pip install -e .

# Set environment variables
export FIREWORKS_API_KEY="your_key"
export FIREWORKS_BASE_URL="https://api.fireworks.ai/inference/v1"
export ALLOWED_MODELS="model1,model2"

# Run locally
python -m src.main

# Run tests
pytest
```

## Docker

```bash
# Build image
docker build -t fireworks-agent .

# Run container
docker run \
  -e FIREWORKS_API_KEY="your_key" \
  -e FIREWORKS_BASE_URL="https://api.fireworks.ai/inference/v1" \
  -e ALLOWED_MODELS="model1,model2" \
  -v $(pwd)/input:/input \
  -v $(pwd)/output:/output \
  fireworks-agent
```

### Production Docker layout

The container is a batch worker:

- reads `/input/tasks.json`
- writes `/output/results.json`
- exits with code `0` on success

Build the image:

```bash
docker build -t your-dockerhub-user/fireworks-agent:latest .
```

Run locally with the development compose file:

```bash
docker compose up --build
```

For Linux hosts, it is often helpful to align the container user with your local user before
starting compose:

```bash
export UID=$(id -u)
export GID=$(id -g)
docker compose up --build
```

For file-sync rebuilds, use:

```bash
docker compose watch
```

Run the production compose file:

```bash
docker compose -f docker-compose.prod.yml up --build
```

Publish to Docker Hub:

```bash
docker login
docker tag fireworks-agent:latest your-dockerhub-user/fireworks-agent:latest
docker push your-dockerhub-user/fireworks-agent:latest
```

Recommended runtime environment variables:

- `FIREWORKS_API_KEY`
- `FIREWORKS_BASE_URL`
- `ALLOWED_MODELS`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`

The image does not bake secrets, and the entrypoint simply starts the batch worker:

```bash
python -m src.main
```

On startup, the container drops privileges to the dedicated `appuser` account before running
the batch worker.

## Task Categories

The agent handles 8 task categories:

1. Factual knowledge
2. Mathematical reasoning
3. Sentiment classification
4. Text summarization
5. Named entity recognition
6. Code debugging
7. Logical/deductive reasoning
8. Code generation

## Performance Goals

- **Accuracy**: Must pass LLM-judge evaluation
- **Token efficiency**: Ranked by total tokens used (lower is better)
- **Runtime**: Under 10 minutes for full batch
- **Image size**: Under 10GB compressed
