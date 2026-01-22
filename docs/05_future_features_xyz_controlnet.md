# Future Features: XYZ Plot and ControlNet

## Overview

The template + manifest architecture is designed to support these advanced features without core code changes.

## XYZ Plot

### Concept
Run the same workflow multiple times with varying parameters, then combine results into a grid.

### Implementation Approach

1. **New endpoint**: `POST /api/jobs/xyz`
2. **Request body**:
```json
{
  "workflow_id": "sd15_txt2img",
  "base_params": { "prompt": "a cat", "seed": 42 },
  "x_axis": { "param": "steps", "values": [10, 20, 30] },
  "y_axis": { "param": "cfg", "values": [5.0, 7.0, 9.0] },
  "z_axis": null
}
```

3. **Server logic**:
   - Generate all combinations: 3 x 3 = 9 jobs
   - Queue them as a batch
   - After completion, stitch into grid image

4. **Manifest extension**:
```json
{
  "params": {
    "steps": {
      "type": "integer",
      "xyz_capable": true,
      "xyz_suggested_values": [10, 20, 30, 40, 50]
    }
  }
}
```

### Why It Works
- Each combination is just a different `params` dict
- The patcher handles each independently
- No workflow code changes needed

## ControlNet

### Concept
Add conditioning images (depth maps, edge detection, pose) to guide generation.

### Implementation Approach

1. **New workflow**: `workflows/sd15_controlnet_canny/`
2. **Template includes ControlNet nodes**:
```json
{
  "10": {
    "class_type": "ControlNetLoader",
    "inputs": {"control_net_name": "__CONTROLNET_MODEL__"}
  },
  "11": {
    "class_type": "ControlNetApply",
    "inputs": {
      "image": ["12", 0],
      "control_net": ["10", 0],
      "strength": 1.0
    }
  },
  "12": {
    "class_type": "LoadImage",
    "inputs": {"image": "__CONTROL_IMAGE__"}
  }
}
```

3. **Manifest**:
```json
{
  "params": {
    "control_image": {
      "type": "image",
      "required": true,
      "description": "Control image (will be uploaded to ComfyUI)",
      "patch": {"node_id": "12", "field": "inputs.image"}
    },
    "controlnet_model": {
      "type": "string",
      "required": true,
      "patch": {"node_id": "10", "field": "inputs.control_net_name"}
    },
    "controlnet_strength": {
      "type": "number",
      "default": 1.0,
      "min": 0.0,
      "max": 2.0,
      "patch": {"node_id": "11", "field": "inputs.strength"}
    }
  }
}
```

4. **Image upload flow**:
   - Client uploads image to `/api/upload`
   - Server stores in ComfyUI's input folder
   - Returns filename
   - Client includes filename in job params

### New Param Type: `image`
```python
# In patcher.py
if param_def["type"] == "image":
    # Value is a filename in ComfyUI's input folder
    # Just patch it directly
    pass
```

## Img2Img

### Concept
Start from an existing image instead of noise.

### Implementation Approach

1. **New workflow**: `workflows/sd15_img2img/`
2. **Template replaces EmptyLatentImage with LoadImage + VAEEncode**
3. **New params**:
```json
{
  "init_image": {
    "type": "image",
    "required": true,
    "patch": {"node_id": "load_img", "field": "inputs.image"}
  },
  "denoise": {
    "type": "number",
    "default": 0.75,
    "min": 0.0,
    "max": 1.0,
    "patch": {"node_id": "ksampler", "field": "inputs.denoise"}
  }
}
```

## Architecture Considerations

### Keeping It Simple

1. **Don't overengineer**
   - Start with basic ControlNet workflow
   - Add complexity only when needed

2. **One workflow per use case**
   - `sd15_txt2img`
   - `sd15_controlnet_canny`
   - `sd15_controlnet_depth`
   - Not one mega-workflow with conditionals

3. **UI can be generated from manifest**
   - Future enhancement
   - Read params, generate form fields
   - Hide/show based on param visibility flags

### File Upload Strategy

Option A: Upload to server, copy to ComfyUI
- More control
- Works with remote ComfyUI

Option B: Direct upload to ComfyUI
- Simpler
- Requires ComfyUI to be accessible from client

Recommendation: Start with Option A for flexibility.

## Timeline Considerations

1. **Phase 1** (Current): Core refactoring
   - Workflow Registry + Patcher
   - Multiple workflows working

2. **Phase 2**: Image upload support
   - `/api/upload` endpoint
   - `image` param type

3. **Phase 3**: ControlNet workflows
   - One workflow per ControlNet type
   - Basic UI support

4. **Phase 4**: XYZ Plot
   - Batch job execution
   - Grid stitching

5. **Phase 5**: Dynamic UI
   - Form generation from manifest
   - Advanced controls
