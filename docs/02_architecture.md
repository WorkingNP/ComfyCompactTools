# Architecture

## Overview

```
+------------------+     +-------------------+     +------------------+
|   Client (UI)    | --> |   FastAPI Server  | --> |    ComfyUI       |
+------------------+     +-------------------+     +------------------+
                               |
                               v
                    +---------------------+
                    |  Workflow Registry  |
                    +---------------------+
                               |
              +----------------+----------------+
              |                                 |
              v                                 v
    +------------------+             +------------------+
    | template_api.json|             |  manifest.json   |
    +------------------+             +------------------+
```

## Components

### 1. Workflow Registry (`server/workflow_registry.py`)

Responsible for:
- Discovering available workflows in `workflows/` directory
- Loading and caching template + manifest pairs
- Validating manifest structure
- Providing workflow metadata to API consumers

```python
class WorkflowRegistry:
    def list_workflows() -> List[WorkflowInfo]
    def get_workflow(workflow_id: str) -> Workflow
    def reload() -> None
```

### 2. Patcher (`server/workflow_patcher.py`)

A pure function that applies parameters to a template:

```python
def apply_patch(
    template: dict,
    manifest: dict,
    params: dict
) -> dict:
    """
    1. Deep copy the template
    2. For each param in params:
       - Look up patch definition in manifest
       - Navigate to node_id.field
       - Set the value
    3. Return the patched template
    """
```

Key principles:
- **Pure function**: No side effects, no mutations
- **Deterministic**: Same inputs always produce same output
- **Detailed errors**: Clear messages about what failed and why

### 3. Directory Structure

```
workflows/
├── sd15_txt2img/
│   ├── template_api.json    # ComfyUI API format
│   └── manifest.json        # Parameter definitions
├── flux2_dev/
│   ├── template_api.json
│   └── manifest.json
└── flux2_klein_distilled/
    ├── template_api.json
    └── manifest.json
```

### 4. Request Flow

```
1. Client sends POST /api/jobs with:
   - workflow_id: "flux2_dev"  (optional, defaults to "sd15_txt2img")
   - params: { prompt: "...", steps: 30, ... }

2. Server:
   a. Loads workflow from registry
   b. Validates params against manifest
   c. Applies patches to create final prompt
   d. Submits to ComfyUI
   e. Returns job info

3. WebSocket events flow back to client
```

## Data Flow

### Template Loading (Startup)

```
workflows/<id>/template_api.json
        |
        v
   JSON.parse()
        |
        v
   Cached in Registry
        |
        v
   Deep copy on each request
```

### Parameter Patching (Per Request)

```
User Params          Manifest Patch Definitions
    |                           |
    v                           v
+-----------------------------------+
|         apply_patch()             |
+-----------------------------------+
                |
                v
      Patched Template (new dict)
                |
                v
         ComfyUI /prompt
```

## Error Handling

| Error Type | Where Caught | User Message |
|------------|--------------|--------------|
| Workflow not found | Registry | "Unknown workflow_id: X" |
| Invalid param type | Patcher | "Param 'X' must be int, got str" |
| Missing required param | Patcher | "Missing required param: X" |
| Template patch failed | Patcher | "Cannot patch node 'X' field 'Y': not found" |
| ComfyUI error | ComfyClient | Passed through from ComfyUI |
