# Submission Checklist

## What Gets Submitted (Docker Image)

These files are **INCLUDED** in your Docker image:

```
✅ src/                          # Your actual agent code
  ✅ agent/
    ✅ executor.py               # Task execution logic
    ✅ pipeline.py               # Processing pipeline
  ✅ config/
    ✅ constants.py              # Task categories
    ✅ settings.py               # Environment config
    ✅ logging.py                # Logging setup
  ✅ io/
    ✅ reader.py                 # Read tasks.json
    ✅ writer.py                 # Write results.json
    ✅ validator.py              # Validation
  ✅ llm/
    ✅ client.py                 # Fireworks API client
    ✅ parser.py                 # Response parsing
    ✅ token_tracker.py          # Token tracking
  ✅ models/
    ✅ task.py                   # Task models
    ✅ result.py                 # Result models
    ✅ response.py               # Response models
  ✅ prompts/
    ✅ builder.py                # Prompt templates
  ✅ routing/
    ✅ router.py                 # Task routing logic
    ✅ rules.py                  # Routing rules
  ✅ app.py                      # Main application
  ✅ main.py                     # Entry point

✅ main.py                       # Container entry point
✅ Dockerfile                    # Build instructions
✅ pyproject.toml                # Dependencies
✅ README.md                     # Documentation
```

## What's Excluded (Testing Only)

These files are **NOT SUBMITTED** (in .gitignore):

```
❌ test_track1*.py               # Local testing scripts
❌ test_ollama.*                 # Ollama test scripts
❌ tests/test_ollama*.py         # Ollama test suite
❌ examples/ollama_example.py    # Ollama examples
❌ scripts/test_with_ollama.py   # Interactive testing

❌ src/llm/ollama_client.py      # Ollama client (not used in submission)

❌ README_OLLAMA.md              # Ollama documentation
❌ GET_STARTED.md                # Ollama setup guide
❌ TRACK1_TESTING.md             # Testing documentation
❌ TRACK1_QUICKSTART.txt         # Quick reference
❌ docs/OLLAMA_TESTING.md        # Detailed Ollama guide
❌ docs/QUICK_START_OLLAMA.md    # Ollama quick start

❌ output/results.json           # Test outputs
❌ baseline.txt                  # Benchmark results
❌ optimized.txt                 # Optimization results
```

## Pre-Submission Checklist

### 1. Code Quality
- [ ] Run tests: `pytest tests/` (excluding test_ollama*.py)
- [ ] Run linter: `ruff check src/`
- [ ] Run type checker: `mypy src/`
- [ ] No hardcoded API keys or secrets
- [ ] No hardcoded model names (reads from `ALLOWED_MODELS`)

### 2. Test with Ollama (Development)
```bash
# Test locally first
python test_track1_improved.py --backend ollama

# Check results
# - Accuracy: Should be reasonable (60-80%+ with small models)
# - Tokens: Note baseline
# - Pipeline: Completes without errors
```

### 3. Validate with Fireworks (Pre-Submission)
```bash
# ONE test run with real API
export FIREWORKS_API_KEY=your_key
export FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1
export ALLOWED_MODELS=<published-models>

python test_track1_improved.py --backend fireworks

# Expected results:
# - Accuracy: 85%+ (must pass gate)
# - Tokens: Record actual count
```

### 4. Build Docker Image
```bash
# Build
docker build -t your-username/track1-agent:latest .

# Check size (must be < 10GB compressed)
docker images your-username/track1-agent:latest
```

### 5. Test Docker Image Locally
```bash
# Create test environment
export FIREWORKS_API_KEY=your_key
export FIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1
export ALLOWED_MODELS=model1,model2,model3

# Run container
docker run --rm \
  -v $(pwd)/input:/input:ro \
  -v $(pwd)/output:/output \
  -e FIREWORKS_API_KEY \
  -e FIREWORKS_BASE_URL \
  -e ALLOWED_MODELS \
  your-username/track1-agent:latest

# Verify output
cat output/results.json
# Should be: [{"task_id": "...", "answer": "..."}]
```

### 6. Push to DockerHub
```bash
# Login
docker login

# Push
docker push your-username/track1-agent:latest

# Verify
docker pull your-username/track1-agent:latest
```

### 7. Submit
- [ ] Submit image name to competition portal
- [ ] Image name: `your-username/track1-agent:latest`
- [ ] Image size: < 10GB compressed
- [ ] Image is public (can be pulled without credentials)

## Common Issues

### Issue: "Model not found"
**Cause**: Hardcoded model name instead of reading from `ALLOWED_MODELS`

**Fix**: Verify `src/config/settings.py` reads from environment:
```python
allowed_models=[
    model.strip() 
    for model in os.environ["ALLOWED_MODELS"].split(",") 
    if model.strip()
]
```

### Issue: "File not found: /input/tasks.json"
**Cause**: Docker container doesn't have correct volume mounts

**Fix**: Verify paths in `src/app.py`:
```python
tasks = await load_tasks(Path("/input/tasks.json"))
await save_results(results, Path("/output/results.json"))
```

### Issue: "Submission rejected - accuracy too low"
**Cause**: Agent accuracy < 85% on competition tasks

**Fix**:
1. Test with Fireworks before submitting
2. Improve prompts (see `src/prompts/builder.py`)
3. Use larger/better models for hard categories

### Issue: "Submission ranked low - too many tokens"
**Cause**: Prompts are too verbose

**Fix**:
1. Shorten prompts in `src/prompts/builder.py`
2. Use smaller models for easy categories (sentiment, NER)
3. Remove unnecessary instructions
4. Test token count with Ollama first

## What Files to Git Commit?

Commit only production code:

```bash
# Production files (commit these)
git add src/
git add main.py
git add Dockerfile
git add pyproject.toml
git add README.md

# Optionally commit
git add .claude/           # Claude Code configuration
git add tests/             # Tests (but not test_ollama*.py)

# Never commit
# (already in .gitignore)
# - test_track1*.py
# - test_ollama.*
# - *OLLAMA*.md
# - output/results.json
```

## Final Checks Before Submission

- [ ] Tested with Ollama (development)
- [ ] Validated with Fireworks (accuracy 85%+)
- [ ] Docker image builds successfully
- [ ] Docker image size < 10GB
- [ ] Docker image tested locally
- [ ] Image pushed to DockerHub
- [ ] Image is public
- [ ] No secrets in image
- [ ] Ready to submit!

---

**Remember**: The test scripts help you develop, but **only the Docker image is submitted** to the competition.

Good luck! 🚀
