---
name: wan-2.7
description: Use when the user asks to generate or edit images/videos with Alibaba Cloud Bailian/DashScope Wan 2.7 or Wan video models, including 文生图, 图生图, 文生视频, 图生视频, 参考生视频, 视频编辑, or 通义万相.
---

# Wan 2.7

Use this skill to execute Wan image and video generation requests, not to merely explain the API.

## What this skill does

- Supports text-to-image.
- Supports image-to-image with one or more local files or public URLs.
- Supports text-to-video through Wan video models.
- Supports wan2.7 image-to-video with `media` inputs:
  - first frame
  - first frame + last frame
  - first clip continuation
  - optional driving audio
- Supports structured video specs for:
  - reference-to-video
  - VACE video editing
  - legacy first/last-frame image-to-video
- Supports chat-side interactive portrait prompt building backed by local carrier / trigger data.
- Supports the V1 demo parameter set:
  - `size`
  - `n`
  - `seed`
  - `watermark`
  - `enable_sequential`
  - `thinking_mode`
  - `color_palette`
  - `bbox_list`
- Saves request/response artifacts and downloaded image or video outputs locally.
- Returns local file paths so the caller can inline-display generated images or link generated videos.

## Prompt construction

Do not treat all prompts as the same shape.

Portrait-centric requests need a separate chat-side workflow before the final prompt is written.

The official Wan 2.7 image-edit doc describes a few distinct usage patterns:

- general instruction-following edits
- multi-image fusion
- subject-feature preservation
- precise local editing with `bbox_list`
- multi-panel / continuous output for wan2.7 models

This local skill also adds one structured chat-side pattern:

- interactive portrait construction using local carrier / trigger data

For this local skill, choose a prompt task type first, then write the prompt with the matching template.

Canonical reference:

- [prompt-task-types.md](F:/Documents/Playground/wan2.7-image-demo/references/prompt-task-types.md)
- [video-prompt-task-types.md](F:/Documents/Playground/wan2.7-image-demo/references/video-prompt-task-types.md)
- [chat-onboarding-flow.md](F:/Documents/Playground/wan2.7-image-demo/references/chat-onboarding-flow.md)
- [video-api-notes.md](F:/Documents/Playground/wan2.7-image-demo/references/video-api-notes.md)
- [video-runner-spec.md](F:/Documents/Playground/wan2.7-image-demo/references/video-runner-spec.md)
- [portrait-chat-flow.md](F:/Documents/Playground/wan2.7-image-demo/references/portrait-chat-flow.md)
- [portrait-data-schema.md](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data-schema.md)
- [triggers_by_dim.json](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data/triggers_by_dim.json)
- [carriers.json](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data/carriers.json)

Hard boundaries:

- Do not invent hidden prompt-rewrite behavior. Image tasks do not expose `negative_prompt` or `prompt_extend`; video tasks may expose model-specific `negative_prompt` or `prompt_extend` through the video runner.
- Do not claim dedicated detection/segmentation task support in this runner until the request/response contract is verified locally.
- For multi-image input, explicitly assign each image a role in the prompt.
- For editing tasks, state preservation constraints before the requested change.
- Portrait flow is a chat-side overlay, not a new runner mode.
- Do not dump every available portrait trigger into one message.
- Do not override `carrier.fixed` fields in place; switch to a compatible carrier instead.
- For video tasks, use public HTTP/HTTPS media URLs. The local video runner does not upload local files.

## Portrait prompt workflow

When the user wants any human-centered result and face / age / ethnicity / hairstyle / expression are primary controls, switch into the portrait workflow before writing the final prompt.

This is mandatory.

If the primary subject is a person, do not jump directly from the user's sentence to a freehand final prompt.
Even when the user already gave a detailed description, you must still trigger the portrait workflow:

- pre-fill the slots already implied by the request
- ask only the unresolved or high-impact slots
- then assemble the final descriptor from carrier data

Typical triggers:

- `人物`
- `人像`
- `证件照`
- `头像`
- `avatar`
- `headshot`
- `保持这个人的长相不变`

Use the local portrait data files as the source of truth:

- `references/portrait-data/triggers_by_dim.json`
- `references/portrait-data/carriers.json`
- `references/portrait-data-schema.md`

Workflow rules:

1. Start with build depth:
   - `快速成型`
   - `标准捏脸`
   - `深度定制`
2. Recommend 2-4 compatible carriers based on carrier data, in this order:
   - `use_cases`
   - `build_depth`
   - `fixed`
   - `slots` count only as a tiebreaker
3. Treat `carrier.fixed` as hard constraints. If the user wants conflicting traits, change carriers instead of editing fixed fields.
4. Walk `carrier.slots` in order, one slot at a time.
5. Resolve slot options this way:
   - no `slot_source` -> `triggers_by_dim[slot]`
   - `slot_source.kind = dim_union` -> ask category first, then concrete values
   - `slot_source.kind = literal_values` -> use the literal values directly
   - `slot_source.kind = filtered_dim` -> use the declared subset from the referenced dimension
   - any other shape is invalid portrait data
6. At each step, show only a small option set plus:
   - `随机`
   - `跳过`
   - `自定义`
7. If the user already supplied exact traits, pre-fill those slots and only ask unresolved ones.
8. After core face slots are done, optionally offer enhancement packs:
   - hair
   - makeup
   - expression
   - accessories
   - clothing
   - background / lighting / camera style
9. Assemble the final descriptor from the selected carrier template plus any optional pack clauses.

Routing rules:

- no input image + portrait request -> `t2i_scene` with portrait overlay
- input image + identity must stay stable -> `subject_preserve` with portrait overlay
- input image + general portrait edit -> `edit_rewrite` with portrait overlay
- local portrait-region edit -> `bbox_precise_edit` with portrait overlay

Detailed chat guidance lives here:

- [portrait-chat-flow.md](F:/Documents/Playground/wan2.7-image-demo/references/portrait-chat-flow.md)

## BBox boundary

- Structured `bbox_list` is supported in this version.
- The chat layer may propose boxes from the visible image and the user's natural-language target.
- The runner does not do object detection or natural-language localization.
- Do not describe this as fully automatic bbox localization.
- Default workflow for regional edits:
  - chat proposes a candidate box
  - user confirms or adjusts
  - runner sends the confirmed `bbox_list`
- If the image is not visible in the current chat context, do not pretend the chat layer can propose a reliable box.

## Authentication

The Python runner loads the API key in this order:

1. `<workspace-root>/api_key.txt`
2. `DASHSCOPE_API_KEY`

The key file must contain only the raw API key.

Region keys are not interchangeable. Beijing and Singapore must use their own API keys and base URLs.

## Workspace Defaults

The runner also supports a non-secret workspace config file:

- `<workspace-root>/wan2.7-image-demo.json`

Use this to store default model and per-mode defaults such as:

- default image size
- default `n`
- default `watermark`
- default `thinking_mode` for `t2i`
- default `base_url`

Keep secrets out of this file. Store the API key only in `api_key.txt`.

Recommended shape:

```json
{
  "model": "wan2.7-image",
  "base_url": "https://dashscope.aliyuncs.com/api/v1",
  "defaults": {
    "t2i": {
      "size": "1024*1024",
      "n": 1,
      "watermark": false,
      "thinking_mode": true
    },
    "i2i": {
      "size": "1024*1024",
      "n": 1,
      "watermark": false
    },
    "video": {
      "t2v": {
        "model": "wan2.6-t2v",
        "size": "1280*720",
        "duration": 2,
        "prompt_extend": true,
        "watermark": false
      },
      "i2v": {
        "model": "wan2.7-i2v",
        "resolution": "720P",
        "duration": 5,
        "prompt_extend": true,
        "watermark": false
      },
      "videoedit": {
        "model": "wan2.7-videoedit",
        "resolution": "720P",
        "duration": 0,
        "prompt_extend": true,
        "watermark": false,
        "audio_setting": "origin"
      }
    }
  }
}
```

For first-use initialization, write concrete pixel sizes into this file.

- If the user says `1:1`, `16:9`, or similar, convert that ratio in chat first.
- Persist the resolved `size` such as `1024*1024` or `1344*768`.
- Do not add a separate `ratio` field to workspace config.
- Existing legacy configs that already use `1K/2K/4K` remain readable for compatibility.
- For video defaults, use `defaults.video` and keep it separate from image `t2i/i2i`.
- For text-to-video, save concrete `size` such as `1280*720`; do not save `1K/2K`.
- For Wan 2.7 image-to-video and video editing, prefer conservative `resolution: 720P` defaults unless the user explicitly chooses 1080P.

### First-use behavior

- On first use in a workspace, check whether `api_key.txt` and `wan2.7-image-demo.json` exist.
- If either is missing, do not guess hidden defaults.
- If the config exists but `defaults.video` is missing and the user asks for video, offer to add video defaults without rewriting image defaults.
- Ask the user whether to initialize workspace config.
- Prefer a two-step choice:
  - `快速推荐`
  - `自定义`
- If the user agrees, gather the values in chat and write the files automatically.
- In `快速推荐`, ask for:
  - region
  - API key
  - resolution tier (`1K/2K`, and `4K` only for explicit pro t2i defaults)
  - aspect ratio
  - primary usage pattern
- For video defaults in `快速推荐`, do not ask a separate long questionnaire.
- Use conservative defaults:
  - text-to-video: `wan2.6-t2v`, `1280*720`, `2s`, `prompt_extend=true`, `watermark=false`
  - image-to-video: `wan2.7-i2v`, `720P`, `5s`, `prompt_extend=true`, `watermark=false`
  - video editing: `wan2.7-videoedit`, `720P`, `duration=0`, `audio_setting=origin`, `watermark=false`
- When the user gives `resolution tier + aspect ratio`, convert that pair to a concrete pixel `size` before writing config.
- Prefer the initializer script instead of hand-writing JSON in chat.
- For existing image-only configs, prefer `update_video_defaults.py` instead of overwriting the whole config.
- After initialization, continue the current task using the saved defaults.

Recommended onboarding reference:

- [chat-onboarding-flow.md](F:/Documents/Playground/wan2.7-image-demo/references/chat-onboarding-flow.md)

Practical rule:

- first save stable defaults
- then offer task-template suggestions
- do not merge onboarding and template education into one long questionnaire

Initializer path:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/init_workspace_config.py \
  --workspace-root /absolute/path/to/workspace \
  --api-key "your-api-key" \
  --model wan2.7-image \
  --t2i-size 1024*1024 \
  --t2i-n 1 \
  --t2i-watermark false \
  --t2i-thinking-mode true \
  --i2i-size 1024*1024 \
  --i2i-n 1 \
  --i2i-watermark false \
  --video-t2v-model wan2.6-t2v \
  --video-t2v-size 1280*720 \
  --video-t2v-duration 2 \
  --video-t2v-prompt-extend true \
  --video-t2v-watermark false \
  --video-i2v-model wan2.7-i2v \
  --video-i2v-resolution 720P \
  --video-i2v-duration 5 \
  --video-i2v-prompt-extend true \
  --video-i2v-watermark false \
  --videoedit-model wan2.7-videoedit \
  --videoedit-resolution 720P \
  --videoedit-duration 0 \
  --videoedit-prompt-extend true \
  --videoedit-watermark false \
  --videoedit-audio-setting origin
```

Add video defaults to an existing image-only config:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/update_video_defaults.py \
  --workspace-root /absolute/path/to/workspace \
  --video-t2v-size 1280*720 \
  --video-t2v-duration 2 \
  --video-i2v-resolution 720P \
  --video-i2v-duration 5 \
  --videoedit-resolution 720P \
  --videoedit-duration 0 \
  --videoedit-audio-setting origin
```

`update_video_defaults.py` merges explicit fields by default.
Use `--reset` only when replacing the whole `defaults.video` block intentionally.

## Preferred execution path

Prefer the Python standard-library runner. It avoids OS-specific shell logic.

### Simple CLI usage

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/run_wan27_image.py \
  --prompt "A cinematic orange cat astronaut on the moon" \
  --size 1K \
  --n 1
```

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/run_wan27_image.py \
  --model wan2.7-image-pro \
  --prompt "Turn this into a high-end product poster" \
  --image "/absolute/path/to/ref.png" \
  --size 1K \
  --seed 12345
```

### Structured usage for complex requests

For multi-image or parameter-heavy requests, prefer `--spec-file`:

```json
{
  "prompt": "Generate a unified concept-art sheet for these references",
  "images": [
    "/absolute/path/to/ref-1.png",
    "/absolute/path/to/ref-2.jpg"
  ],
  "parameters": {
    "size": "1K",
    "n": 2,
    "enable_sequential": true,
    "watermark": false,
    "color_palette": [
      { "hex": "#C2D1E6", "ratio": "40.00%" },
      { "hex": "#636574", "ratio": "35.00%" },
      { "hex": "#C0B5B4", "ratio": "25.00%" }
    ]
  }
}
```

Then run:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/run_wan27_image.py \
  --spec-file /absolute/path/to/job.json
```

For regional editing, pass structured `bbox_list` through `parameters`:

```json
{
  "prompt": "把框选区域里的杯子替换成透明玻璃杯，保持光线和透视自然",
  "images": [
    "/absolute/path/to/ref.png"
  ],
  "parameters": {
    "size": "1K",
    "n": 1,
    "bbox_list": [
      [[820, 540, 980, 760]]
    ]
  }
}
```

Or load the raw bbox array with `--bbox-file`:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/run_wan27_image.py \
  --prompt "把框选区域里的杯子替换成透明玻璃杯，保持光线和透视自然" \
  --image "/absolute/path/to/ref.png" \
  --bbox-file /absolute/path/to/bbox.json
```

## Video workflow

When the user asks for video generation or editing, route to the video runner and choose a video task type before writing the prompt.

Use these routing defaults:

- no reference media -> text-to-video with `wan2.6-t2v`
- first-frame, first+last-frame, or first-clip continuation -> `wan2.7-i2v`
- character/object reference media -> reference-to-video with `wan2.6-r2v` or `wan2.6-r2v-flash`
- instruction-based editing of an existing video -> `wan2.7-videoedit`
- older VACE local edit / repaint / extension / outpainting modes -> `wan2.1-vace-plus`

Use the video prompt templates here:

- [video-prompt-task-types.md](F:/Documents/Playground/wan2.7-image-demo/references/video-prompt-task-types.md)

Use the API constraints here:

- [video-api-notes.md](F:/Documents/Playground/wan2.7-image-demo/references/video-api-notes.md)
- [video-runner-spec.md](F:/Documents/Playground/wan2.7-image-demo/references/video-runner-spec.md)

Simple text-to-video:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/run_wan27_video.py \
  --model wan2.6-t2v \
  --prompt "A slow cinematic product shot of a transparent glass cup on wet black stone, single continuous camera push-in, soft rim light" \
  --size 1280*720 \
  --duration 5 \
  --prompt-extend true
```

Simple Wan 2.7 image-to-video:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/run_wan27_video.py \
  --prompt "The character slowly walks forward, natural cloth motion, stable face identity, cinematic lighting" \
  --media first_frame=https://example.com/frame.png \
  --resolution 720P \
  --duration 5 \
  --prompt-extend true
```

Wan 2.7 video editing:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/run_wan27_video.py \
  --model wan2.7-videoedit \
  --prompt "Change the video into watercolor animation style while preserving motion, composition, and main subject identity" \
  --media video=https://example.com/input.mp4 \
  --media reference_image=https://example.com/style.png \
  --resolution 720P \
  --ratio 16:9 \
  --audio-setting origin
```

Structured video spec:

```json
{
  "model": "wan2.7-i2v",
  "input": {
    "prompt": "一只黑猫从首帧姿态自然起身，走向镜头，动作连贯，面部不变形",
    "media": [
      {
        "type": "first_frame",
        "url": "https://example.com/first.png"
      },
      {
        "type": "last_frame",
        "url": "https://example.com/last.png"
      }
    ]
  },
  "parameters": {
    "resolution": "720P",
    "duration": 5,
    "prompt_extend": true,
    "watermark": false
  }
}
```

Then run:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/run_wan27_video.py \
  --spec-file /absolute/path/to/video-job.json
```

Video boundary rules:

- Video inputs must be public HTTP/HTTPS URLs.
- Do not pass local video/image/audio paths to the video runner.
- Download the returned `video_url` immediately; the runner does this automatically.
- Do not claim a model-specific parameter is supported unless it is listed in `video-api-notes.md` or the user supplied it in a raw spec based on current docs.

## Caller workflow

1. Decide whether the request is image or video.
2. Gather:
   - prompt
   - zero or more image paths/URLs for image tasks, or public media URLs for video tasks
   - optional parameters
3. Run the Python entrypoint.
4. Read the JSON summary printed to stdout.
5. Inline-display local image paths from `local_images` or link local video paths from `local_videos`.

When the user request is still underspecified, prefer this follow-up order:

Portrait-centric requests are the exception: use the portrait workflow instead of this generic sequence.

1. what must stay unchanged
2. what should change
3. which image plays which role
4. whether the edit is global or local
5. if local, whether a bbox should be proposed and confirmed

Default resolution order:

1. explicit user request for this run
2. `spec-file` values and explicit CLI flags
3. workspace defaults from `wan2.7-image-demo.json`
4. code-level fallback defaults

## Input interpretation rules

- No input images: treat as text-to-image.
- One or more input images: treat as image-to-image.
- Keep multi-image order exactly as provided.
- The current runtime payload uses `input.messages`, based on live endpoint probe results.
- Unless the user explicitly overrides a setting, prefer workspace defaults from `wan2.7-image-demo.json`.
- No input images + portrait / avatar / headshot intent: still classify as `t2i_scene`, but run the portrait workflow first.
- Portrait edits that require identity stability: classify as `subject_preserve`, but run the portrait workflow first and use it as the preservation contract.
- Any people-centric generation request must trigger portrait workflow first, even if the user already wrote a near-complete descriptor.
- For chat guidance, classify requests into task types before composing prompts:
  - no image -> `t2i_scene`
  - multi-image composition intent -> `multi_image_fusion`
  - subject identity preservation intent -> `subject_preserve`
  - localized edit intent -> `bbox_precise_edit`
  - continuous multi-panel intent -> `sequential_series`
  - otherwise -> `edit_rewrite`
- Reject `thinking_mode` if there are input images or `enable_sequential` is true.
- Reject `color_palette` if `enable_sequential` is true.
- Accept `bbox_list` only when there is at least one input image.
- Require `bbox_list` length to equal the number of input images.
- Require each image entry in `bbox_list` to contain at most 2 boxes.
- Accept model names `wan2.7-image` and `wan2.7-image-pro`.
- Reject `4K` for `wan2.7-image`; reject `4K` for image-to-image and sequential mode even on `wan2.7-image-pro`.
- Reject unsupported parameters explicitly. Do not silently drop them.
- If a parameter is missing, let the runner use conservative defaults rather than inventing extra behavior.
- For video generation, accept `wan2.7-i2v`, `wan2.7-videoedit`, `wan2.6-t2v`, `wan2.6-r2v`, `wan2.6-r2v-flash`, legacy i2v, and VACE models through the video runner.
- For `wan2.7-i2v`, require `input.media` with a supported first-frame / first+last / first-clip combination.
- For `wan2.7-videoedit`, require exactly one `media` item of type `video` and allow up to three reference images.

## Error handling expectations

If the runner fails, report:

- what stage failed
- the actionable reason
- where request/response artifacts were written

Do not dump secrets. Do not echo the API key. Do not claim success unless at least one image or video was downloaded locally.
