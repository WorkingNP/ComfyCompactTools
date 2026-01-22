# Manifest Specification

## Overview

The `manifest.json` file defines:
1. Workflow metadata (name, description, version)
2. Available parameters and their types
3. How parameters map to template nodes (patch definitions)
4. Validation rules
5. Optional presets

## Schema

```json
{
  "$schema": "../docs/manifest.schema.json",
  "id": "flux2_dev",
  "name": "Flux 2 Dev",
  "description": "Flux 2 development model with fp8 mixed precision",
  "version": "1.0.0",
  "template_file": "template_api.json",

  "params": {
    "prompt": {
      "type": "string",
      "required": true,
      "description": "The text prompt for image generation",
      "patch": {
        "node_id": "6",
        "field": "inputs.text"
      }
    },
    "seed": {
      "type": "integer",
      "required": false,
      "default": -1,
      "min": -1,
      "max": 2147483647,
      "description": "Random seed (-1 for random)",
      "patch": {
        "node_id": "25",
        "field": "inputs.noise_seed"
      }
    }
  },

  "presets": {
    "default": {
      "steps": 20,
      "width": 1024,
      "height": 1024
    },
    "fast": {
      "steps": 10,
      "width": 512,
      "height": 512
    }
  },

  "quality_checks": {
    "black_threshold": 0.01,
    "white_threshold": 0.99,
    "skip_checks": false
  }
}
```

## Field Reference

### Root Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (matches directory name) |
| `name` | string | Yes | Human-readable name |
| `description` | string | No | Longer description |
| `version` | string | No | Semantic version |
| `template_file` | string | Yes | Relative path to template JSON |
| `params` | object | Yes | Parameter definitions |
| `presets` | object | No | Named parameter presets |
| `quality_checks` | object | No | Image quality check settings |

### Parameter Definition

Each key in `params` is a parameter name. The value is:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | One of: `string`, `integer`, `number`, `boolean` |
| `required` | boolean | No | Default: false |
| `default` | any | No | Default value if not provided |
| `min` | number | No | Minimum value (for integer/number) |
| `max` | number | No | Maximum value (for integer/number) |
| `choices` | array | No | Allowed values |
| `description` | string | No | Human-readable description |
| `patch` | object | Yes | How to apply this param to template |

### Patch Definition

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `node_id` | string | Yes | The node ID in the template |
| `field` | string | Yes | Dot-notation path to the field (e.g., `inputs.seed`) |

## Example: SD 1.5 txt2img

```json
{
  "$schema": "../docs/manifest.schema.json",
  "id": "sd15_txt2img",
  "name": "SD 1.5 Text to Image",
  "description": "Classic Stable Diffusion 1.5 text-to-image workflow",
  "version": "1.0.0",
  "template_file": "template_api.json",

  "params": {
    "prompt": {
      "type": "string",
      "required": true,
      "patch": { "node_id": "2", "field": "inputs.text" }
    },
    "negative_prompt": {
      "type": "string",
      "required": false,
      "default": "",
      "patch": { "node_id": "3", "field": "inputs.text" }
    },
    "checkpoint": {
      "type": "string",
      "required": true,
      "patch": { "node_id": "1", "field": "inputs.ckpt_name" }
    },
    "width": {
      "type": "integer",
      "default": 512,
      "min": 64,
      "max": 2048,
      "patch": { "node_id": "4", "field": "inputs.width" }
    },
    "height": {
      "type": "integer",
      "default": 512,
      "min": 64,
      "max": 2048,
      "patch": { "node_id": "4", "field": "inputs.height" }
    },
    "steps": {
      "type": "integer",
      "default": 20,
      "min": 1,
      "max": 150,
      "patch": { "node_id": "5", "field": "inputs.steps" }
    },
    "cfg": {
      "type": "number",
      "default": 7.0,
      "min": 1.0,
      "max": 30.0,
      "patch": { "node_id": "5", "field": "inputs.cfg" }
    },
    "seed": {
      "type": "integer",
      "default": -1,
      "min": -1,
      "patch": { "node_id": "5", "field": "inputs.seed" }
    },
    "sampler_name": {
      "type": "string",
      "default": "euler",
      "patch": { "node_id": "5", "field": "inputs.sampler_name" }
    },
    "scheduler": {
      "type": "string",
      "default": "normal",
      "patch": { "node_id": "5", "field": "inputs.scheduler" }
    },
    "batch_size": {
      "type": "integer",
      "default": 1,
      "min": 1,
      "max": 16,
      "patch": { "node_id": "4", "field": "inputs.batch_size" }
    }
  },

  "presets": {
    "default": {
      "width": 512,
      "height": 512,
      "steps": 20,
      "cfg": 7.0,
      "sampler_name": "euler",
      "scheduler": "normal"
    },
    "highres": {
      "width": 768,
      "height": 768,
      "steps": 30,
      "cfg": 7.5
    }
  }
}
```

## Validation Rules

1. **Type checking**: Values must match declared type
2. **Required fields**: Must be present if `required: true`
3. **Range checking**: Numbers must be within `min`/`max` if specified
4. **Choices**: Value must be in `choices` array if specified
5. **Patch target exists**: The `node_id` and `field` must exist in template
