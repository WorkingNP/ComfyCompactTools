# Test Plan

## Test Categories

### 1. Unit Tests (No ComfyUI Required)

Located in: `server/tests/`

#### test_manifest.py
- [ ] Load valid manifest from JSON file
- [ ] Reject manifest missing required fields (`id`, `name`, `params`)
- [ ] Reject manifest with invalid param types
- [ ] Validate param type declarations
- [ ] Validate patch definitions have required fields

#### test_patcher.py
- [ ] Deep copy preserves original template (mutation test)
- [ ] Simple field patch works (`inputs.text`)
- [ ] Nested field patch works (`inputs.some.nested.field`)
- [ ] Integer coercion from string
- [ ] Float coercion from string
- [ ] Missing param uses default value
- [ ] Missing required param raises error
- [ ] Invalid node_id raises descriptive error
- [ ] Invalid field path raises descriptive error
- [ ] Range validation (min/max)
- [ ] Choice validation

#### test_image_quality.py
- [ ] Detect pure black image (RGB 0,0,0)
- [ ] Detect pure white image (RGB 255,255,255)
- [ ] Detect single-color image
- [ ] Accept valid colorful image
- [ ] Handle grayscale images
- [ ] Handle images with alpha channel

#### test_workflow_registry.py
- [ ] List discovers workflows in directory
- [ ] Get workflow returns manifest and template
- [ ] Get non-existent workflow raises error
- [ ] Registry caches loaded workflows
- [ ] Reload clears cache

### 2. Integration Tests (Mocked HTTP)

Located in: `server/tests/`

#### test_api_integration.py
- [ ] POST /api/jobs with workflow_id
- [ ] POST /api/jobs without workflow_id (default)
- [ ] GET /api/workflows returns list
- [ ] GET /api/workflows/{id} returns manifest
- [ ] Invalid workflow_id returns 404
- [ ] Invalid params return 400 with details

### 3. E2E Tests (ComfyUI Required)

Located in: `server/tests/test_e2e_workflows.py`

Marked with `@pytest.mark.e2e` or skipped when ComfyUI unavailable.

#### test_e2e_flux2_klein.py
- [ ] Generate image with Flux2 Klein workflow
- [ ] Verify image saved to assets
- [ ] Verify not pure black/white
- [ ] Verify recipe stored in DB

#### test_e2e_sd15.py (smoke test)
- [ ] Generate image with SD 1.5 workflow
- [ ] May produce black images (known issue with some models)
- [ ] Marked as xfail or with relaxed quality checks

## Running Tests

### All Unit + Integration Tests (No ComfyUI)
```bash
pytest server/tests/ -v --ignore=server/tests/test_e2e*.py
```

### E2E Tests Only (Requires ComfyUI)
```bash
# First ensure ComfyUI is running on http://127.0.0.1:8188
pytest server/tests/test_e2e*.py -v
```

### Full Test Suite
```bash
pytest -v
```

### With Coverage
```bash
pytest --cov=server --cov-report=html
```

## Test Fixtures

### conftest.py

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_template():
    """A minimal valid template for testing."""
    return {
        "1": {
            "class_type": "TestNode",
            "inputs": {"text": "default", "seed": 0}
        }
    }

@pytest.fixture
def sample_manifest():
    """A minimal valid manifest for testing."""
    return {
        "id": "test_workflow",
        "name": "Test Workflow",
        "template_file": "template_api.json",
        "params": {
            "text": {
                "type": "string",
                "required": True,
                "patch": {"node_id": "1", "field": "inputs.text"}
            },
            "seed": {
                "type": "integer",
                "default": 0,
                "patch": {"node_id": "1", "field": "inputs.seed"}
            }
        }
    }

@pytest.fixture
def workflows_dir(tmp_path):
    """Create a temporary workflows directory for testing."""
    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    return wf_dir

@pytest.fixture
def comfy_available():
    """Check if ComfyUI is available."""
    import httpx
    try:
        r = httpx.get("http://127.0.0.1:8188/system_stats", timeout=2.0)
        return r.status_code == 200
    except:
        return False
```

## CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio
      - run: pytest server/tests/ -v --ignore=server/tests/test_e2e*.py
```
