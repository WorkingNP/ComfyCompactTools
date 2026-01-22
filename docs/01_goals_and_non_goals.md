# Goals and Non-Goals

## Goals

### Primary Goal
Transform ComfyCompactTools from a fixed-workflow system to a **template-driven, manifest-based architecture** that supports multiple workflows without code changes.

### Specific Goals

1. **Workflow as Data**
   - Workflows are defined by JSON templates + manifest files, not hardcoded in Python
   - Adding a new workflow requires no code changes - just add files to `workflows/<id>/`

2. **Template Immutability**
   - Template JSON files are read-only at runtime
   - All parameter changes are applied via deep copy + patch
   - No file mutations during execution

3. **Clean Separation**
   - `template_api.json`: The ComfyUI API prompt (exported via "Save API Format")
   - `manifest.json`: Parameter definitions + patch mapping + validation rules

4. **Backward Compatibility**
   - Existing `/api/jobs` endpoint continues to work
   - Default to `sd15_txt2img` when no `workflow_id` is specified

5. **Testability**
   - Unit tests run without ComfyUI
   - Integration tests mock HTTP responses
   - E2E tests require ComfyUI but are optional/skipable

6. **Extensibility**
   - Future features (ControlNet, xyz plot, img2img) can be added as new workflows
   - No core code changes required for new parameter types

## Non-Goals

1. **Complete UI Rewrite**
   - The existing UI will get minimal changes
   - Dynamic form generation is a future enhancement

2. **Breaking API Changes**
   - We will NOT remove existing endpoints or change their signatures
   - New functionality is additive only

3. **Automatic Workflow Discovery**
   - We won't scan arbitrary directories for workflows
   - Workflows must be explicitly placed in `workflows/`

4. **Real-time Template Editing**
   - Templates are loaded at startup (or on first access)
   - Hot-reloading is out of scope

5. **Complex Validation**
   - We validate required fields and basic types
   - Cross-field validation (e.g., "if X then Y must be Z") is out of scope

6. **Multiple ComfyUI Instances**
   - One ComfyUI backend per cockpit instance
   - Load balancing is out of scope
