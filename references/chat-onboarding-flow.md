# Wan 2.7 Chat Onboarding Flow

This file defines the recommended chat-side guidance flow for the local `wan-2.7` skill.

Goal:

- keep first use short
- save only stable workspace defaults
- recommend prompt templates without turning them into persistent config
- continue the current task after setup instead of forcing a separate onboarding session

## Design split

Two layers only:

1. workspace initialization
2. task-template guidance

Do not merge them into one long questionnaire.

## First-use trigger

Treat the workspace as not fully initialized when either file is missing:

- `api_key.txt`
- `wan2.7-image-demo.json`

Possible states:

- both missing
- only API key missing
- only config missing
- config exists but `defaults.video` is missing
- both present
- legacy config present but still using `1K/2K/4K`

## First message

Recommended wording:

```text
检测到当前工作区还没有完成 wan2.7 初始化。我可以帮你保存 API Key 和默认参数，后续除非你特别指定，否则直接使用这些默认值。
```

If only one file is missing, say that precisely instead of pretending the whole workspace is empty.

If image defaults exist but video defaults are missing, do not restart full onboarding.
Recommended wording:

```text
当前工作区已有图像默认配置，但还没有视频默认配置。我可以只补齐 defaults.video，不改你的图像参数和 API Key。
```

## Initialization modes

Always offer two modes:

- `快速推荐`
- `自定义`

Reason:

- first use should not ask ten questions by default
- advanced users still need a way to pin exact defaults

## Quick mode

Ask only for:

1. region
2. API key
3. preferred resolution tier
4. preferred aspect ratio
5. primary usage pattern

### Region

Choices:

- Beijing
- Singapore

Maps to:

- Beijing -> `https://dashscope.aliyuncs.com/api/v1`
- Singapore -> `https://dashscope-intl.aliyuncs.com/api/v1`

### Preferred resolution tier

Ask for:

- `1K`
- `2K`
- `4K` only when the user explicitly wants `wan2.7-image-pro` text-to-image defaults

Important:

- this is a chat-side onboarding convenience
- it is not the same as persisting the API preset itself
- the config file still stores concrete pixel `size`

### Preferred aspect ratio

Chat may accept ratio language, but config must store concrete `size`.

Recommended base mapping for `1K`:

- `1:1` -> `1024*1024`
- `4:3` -> `1184*888`
- `3:4` -> `888*1184`
- `16:9` -> `1360*765`
- `9:16` -> `765*1360`
- `3:2` -> `1254*836`
- `2:3` -> `836*1254`

Scaling rule:

- `2K` -> multiply the `1K` width and height by `2`
- `4K` -> multiply the `1K` width and height by `4`

Examples:

- `1:1 + 1K` -> `1024*1024`
- `1:1 + 2K` -> `2048*2048`
- `4:3 + 1K` -> `1184*888`
- `4:3 + 2K` -> `2368*1776`
- `16:9 + 1K` -> `1360*765`
- `16:9 + 2K` -> `2720*1530`

Important distinction:

- API preset `size=1K/2K/4K` has official model-side behavior
- saved workspace defaults here use concrete pixel sizes derived in chat
- do not describe these two mechanisms as the same thing

### Primary usage pattern

Choices:

- `文生图为主`
- `图像编辑为主`
- `混合`

Recommended mapping:

- 文生图为主
  - `t2i.size` = mapped size
  - `t2i.n` = 1
  - `t2i.watermark` = false
  - `t2i.thinking_mode` = true
  - `i2i.size` = mapped size
  - `i2i.n` = 1
  - `i2i.watermark` = false
- 图像编辑为主
  - same as above, but if the user later provides a different i2i preference, prefer changing only `i2i.size`
- 混合
  - same defaults for both modes

Quick mode should stay biased toward low-cost defaults:

- `model = wan2.7-image`
- `n = 1`
- watermark off
- video text-to-video default: `wan2.7-t2v`, `size = 1280*720`, `duration = 2`, `watermark = false`
- video image-to-video default: `wan2.7-i2v`, `resolution = 720P`, `duration = 5`, `watermark = false`
- video editing default: `wan2.7-videoedit`, `resolution = 720P`, `duration = 0`, `audio_setting = origin`

Do not ask for all video models in quick mode.
The only optional quick-mode video question is:

```text
视频默认值用低成本测试配置吗？文生视频 1280*720/2秒，图生视频和视频编辑默认 720P。后续你可以单次覆盖。
```

If the user says yes, write the defaults directly.
If the user wants custom video defaults, switch to custom mode.

## Custom mode

Ask only when the user explicitly wants control.

Collect:

- API key
- model
- base_url
- `t2i.size`
- `t2i.n`
- `t2i.watermark`
- `t2i.thinking_mode`
- `i2i.size`
- `i2i.n`
- `i2i.watermark`
- `defaults.video.t2v`
- `defaults.video.i2v`
- `defaults.video.videoedit`

Do not ask for ratio and pixel size together. Choose one:

- accept `resolution tier + ratio` in chat and convert it
- or ask directly for concrete pixel size

## Persistence rules

Write only:

- `api_key.txt`
- `wan2.7-image-demo.json`

The config may include image defaults and video defaults, but keep them under separate keys.

For a missing `defaults.video` on an existing config, write only:

- `defaults.video.t2v`
- `defaults.video.i2v`
- `defaults.video.videoedit`

Use:

```bash
python /absolute/path/to/wan2.7-image-demo/scripts/update_video_defaults.py \
  --workspace-root /absolute/path/to/workspace
```

This script merges explicit fields by default.
Use `--reset` only when the user explicitly wants to replace the entire video-default block.

Do not persist:

- task type
- favorite prompt templates
- suggested examples
- session-specific editing intent

## After initialization

Do not end with a dead confirmation.

Instead:

1. confirm the saved defaults
2. tell the user the current task can continue
3. offer prompt-template suggestions

Recommended wording:

```text
默认配置已保存。后续除非你特别指定，我会直接使用这些默认值。你现在可以直接说“生成一张……”“把图里的……改成……”“把图2的元素放到图1里……”
```

## Template recommendation layer

Template guidance is session help, not workspace config.

Use the task types defined in:

- [prompt-task-types.md](F:/Documents/Playground/wan2.7-image-demo/references/prompt-task-types.md)
- [video-prompt-task-types.md](F:/Documents/Playground/wan2.7-image-demo/references/video-prompt-task-types.md)

After initialization, show a short capability menu:

- 文生图
- 人物肖像捏脸（人物类请求强制进入）
- 单图编辑
- 多图融合
- 主体保持
- 局部编辑
- 连续组图
- 文生视频
- 图生视频
- 参考生视频
- 视频编辑

Keep examples short and action-oriented.

## Runtime classification rules

Default routing:

- no image -> `t2i_scene`
- multiple images plus "把图2放到图1" semantics -> `multi_image_fusion`
- "保持这个人/商品/主体不变" semantics -> `subject_preserve`
- localized edit semantics such as "局部 / 框选 / 右下角 / 这里" -> `bbox_precise_edit`
- "连续 / 分镜 / 三张 / 系列" semantics -> `sequential_series`
- video intent with no media -> `video_t2v_scene`
- video intent with first-frame / first+last-frame / first-clip media -> `video_i2v_first_frame`, `video_i2v_keyframes`, or `video_i2v_continue`
- video intent with reference character/object media -> `video_reference_performance`
- video editing intent with existing video -> `video_vace_edit`
- otherwise -> `edit_rewrite`

## Follow-up question order

When the user request is incomplete, ask in this order:

1. what must stay unchanged
2. what should change
3. which image plays which role
4. whether the edit is global or local
5. if local, whether a bbox should be proposed and confirmed

This keeps the preservation constraint ahead of the edit instruction.

## Suggested prompts for user education

Examples to show after setup:

- `生成一张透明玻璃杯的高端产品图`
- `做一张东亚女青年证件照，你一步一步让我选脸型、眼型和发型`
- `把图里的马克杯改成透明玻璃杯，其余保持不变`
- `把图2的涂鸦喷绘到图1的汽车侧门上`
- `保持图1人物特征不变，把背景改成城市夜景街头`
- `只改右下角桌面上的杯子`
- `生成3张连续画面，主角保持一致`
- `生成一段5秒产品视频，玻璃杯在黑色石材上慢慢旋转`
- `用这张首帧生成视频，人物向镜头走来，脸部保持稳定`
- `把这个视频改成水彩动画风格，运动和主体不变`

人物相关请求的详细交互流参考：

- [portrait-chat-flow.md](F:/Documents/Playground/wan2.7-image-demo/references/portrait-chat-flow.md)

## Hard boundaries

- Do not persist template preference as config.
- Do not create a `ratio` field in workspace config.
- Do not ask every advanced option on first use.
- Do not pretend detection/segmentation is a verified local task type until its contract is tested.
