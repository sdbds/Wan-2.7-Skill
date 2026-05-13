# Wan 2.7 Image API Notes

This file tracks the parts of the official Wan 2.7 API behavior that the local demo runner currently relies on.

It also tracks local runner behavior that affects caller expectations, such as workspace default resolution.

## Official doc facts reflected in the runner

Source: user-provided updated Wan 2.7 API reference text in this thread.

- Supported models:
  - `wan2.7-image`
  - `wan2.7-image-pro`
- The doc positions wan2.7 models as especially suitable for:
  - precise local editing
  - multi-panel / continuous output
- The doc headline also lists:
  - multi-image fusion
  - subject-feature preservation
- Region-specific endpoints:
  - Beijing base URL: `https://dashscope.aliyuncs.com/api/v1`
  - Singapore base URL: `https://dashscope-intl.aliyuncs.com/api/v1`
- Region-specific API keys are not interchangeable.
- Async create endpoint:
  - `/services/aigc/image-generation/generation`
- Poll endpoint:
  - `/tasks/{task_id}`
- Sync endpoint also exists in docs:
  - `/services/aigc/multimodal-generation/generation`
- Request payload uses:
  - top-level `model`
  - top-level `input.messages`
  - top-level `parameters`
- Multi-image input rule:
  - `content` contains multiple `{ "image": "<string>" }` items
  - `image` itself is a single string, not an array
- Task results are retained for 24 hours and should be downloaded immediately.

## Parameters currently supported by the demo runner

- `size`
- `n`
- `seed`
- `watermark`
- `enable_sequential`
- `thinking_mode`
- `color_palette`
- `bbox_list`

## Validation rules implemented locally

- `model` must be `wan2.7-image` or `wan2.7-image-pro`.
- `wan2.7-image` preset sizes:
  - `1K`
  - `2K`
- `wan2.7-image-pro` preset sizes:
  - `1K`
  - `2K`
  - `4K`
- `4K` is rejected for:
  - `wan2.7-image`
  - any image-input scenario
  - sequential mode
- Pixel-size strings (`WIDTH*HEIGHT`) are validated against the doc-level total-pixel and aspect-ratio constraints.
- `thinking_mode` is only accepted when:
  - no input image
  - `enable_sequential = false`
- `color_palette` is only accepted when:
  - `enable_sequential = false`
  - item count is between 3 and 10
  - each item has valid `hex` and `ratio`
  - total ratio equals `100.00%`
- `bbox_list` is only accepted when:
  - there is at least one input image
  - outer list length equals input image count
  - each image entry contains at most 2 boxes
  - each box is `[x1, y1, x2, y2]`
  - coordinates are non-negative
  - `x1 < x2` and `y1 < y2`

## Official size facts

From the official 2.7 API reference:

- for `wan2.7-image-pro`, preset `size` supports:
  - `1K`
  - `2K`
  - `4K`
- for `wan2.7-image`, preset `size` supports:
  - `1K`
  - `2K`
- official preset total pixels are:
  - `1K` -> `1024*1024`
  - `2K` -> `2048*2048`
  - `4K` -> `4096*4096`
- when there is image input and preset `size` is used, the output ratio follows the input image
  - for multi-image input, it follows the last image
- when there is no image input and preset `size` is used, the output is square

This matters for chat onboarding:

- the workspace config still stores concrete pixel sizes
- if chat accepts `resolution tier + aspect ratio`, that pair is converted into a concrete pixel `size`
- do not confuse this onboarding mapping with the API's own preset-size runtime behavior

## Prompt-side interpretation

The official doc widens the prompt-side use cases, but not every headline capability is a new transport parameter.

What this means for the local skill:

- many user intents should be modeled as prompt task types, not as new API branches
- verified prompt-side task types are documented in:
  - [prompt-task-types.md](F:/Documents/Playground/wan2.7-image-demo/references/prompt-task-types.md)

What we still do not claim:

- dedicated detection / segmentation request handling

Reason:

- the current official page mentions that capability at a high level, but the local runner does not yet have a verified request/response contract for it

## Chat-assisted bbox boundary

- The runner now exposes structured `bbox_list`.
- The runner still does not do natural-language localization or object detection.
- In this workspace, bbox proposal belongs to the chat layer when the image is visible in the current conversation.
- Therefore the honest workflow is:
  - chat proposes a candidate box
  - user confirms or adjusts it
  - runner sends the structured `bbox_list`
- Local validation in V1 guarantees structure and image-to-box alignment.
- Full "inside-image" range proof is not guaranteed for every input type, especially remote URLs.
- Any remaining out-of-range rejection is delegated to the API.

## Runtime choice kept intentionally simple

The runner still uses the async create endpoint by default because:

1. It is already proven against live traffic in this workspace.
2. It keeps one code path for long-running jobs.
3. It avoids mixing sync and async response handling in the same CLI.

If sync support is added later, it should be introduced as a separate transport mode, not folded into the current path with more branching.

## Workspace default resolution

The runner supports an optional workspace config file:

- `<workspace-root>/wan2.7-image-demo.json`

Design intent:

- keep secrets in `api_key.txt`
- keep ordinary defaults in JSON config
- avoid repeating the same flags on every run

Resolution order:

1. explicit values for the current run
2. `spec-file` and explicit CLI values
3. workspace defaults from `wan2.7-image-demo.json`
4. code-level fallback defaults

Mode-specific defaults matter:

- `t2i` defaults may include `thinking_mode`
- `i2i` defaults must not rely on `thinking_mode`

This prevents bad global defaults from forcing extra special-case branches later.

For first-use initialization in this workspace:

- chat may accept ratio language such as `1:1` or `16:9`
- the initializer must resolve that to a concrete pixel `size`
- `wan2.7-image-demo.json` should store concrete sizes such as `1024*1024`
- the config file should not grow a separate `ratio` field
- legacy configs that already contain `1K/2K/4K` are still accepted by the runner
