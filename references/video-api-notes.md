# Wan Video API Notes

This file tracks the video-generation behavior that the local `wan-2.7` skill relies on.

Official references checked:

- [Text-to-video API](https://www.alibabacloud.com/help/zh/model-studio/text-to-video-api-reference)
- [Wan 2.7 image-to-video API](https://www.alibabacloud.com/help/zh/model-studio/image-to-video-general-api-reference)
- [Wan 2.7 video editing API](https://www.alibabacloud.com/help/en/model-studio/wan-video-editing-api-reference)
- [Legacy first-frame image-to-video API](https://www.alibabacloud.com/help/zh/model-studio/legacy-image-to-video-api-reference/)
- [Legacy first/last-frame image-to-video API](https://www.alibabacloud.com/help/zh/model-studio/legacy-image-to-video-by-first-and-last-frame-api-reference)
- [Reference-to-video API](https://www.alibabacloud.com/help/zh/model-studio/wan-video-to-video-api-reference)
- [VACE video editing API](https://www.alibabacloud.com/help/zh/model-studio/legacy-wanx-vace-api-reference)

## Shared Runtime Facts

- Video tasks are async.
- Create endpoint for most current video APIs:
  - `/services/aigc/video-generation/video-synthesis`
- Legacy first/last-frame endpoint:
  - `/services/aigc/image2video/video-synthesis`
- Poll endpoint:
  - `/tasks/{task_id}`
- Required header:
  - `X-DashScope-Async: enable`
- Successful video task responses expose:
  - `output.video_url`
- Generated video URLs are temporary and should be downloaded immediately.
- Output format is MP4 with H.264 encoding.

## Supported Local Runner Path

The local runner is:

- [run_wan27_video.py](F:/Documents/Playground/wan2.7-image-demo/scripts/run_wan27_video.py)

It supports:

- convenience CLI for `wan2.7-i2v` media-based jobs
- convenience CLI for text-to-video when `--model` is supplied
- `--spec-file` for reference-to-video, VACE, and legacy modes

It does not upload local files.

For video APIs, pass public HTTP/HTTPS URLs for:

- images
- audio
- videos
- masks

## Main Video Task Families

| Family | Main model examples | Endpoint | Input shape |
| --- | --- | --- | --- |
| Text-to-video | `wan2.7-t2v`, `wan2.6-t2v`, `wan2.5-t2v-preview` | `video-generation` | `input.prompt`, optional `input.audio_url` |
| Wan 2.7 image-to-video | `wan2.7-i2v` | `video-generation` | `input.media[]` |
| Legacy first-frame image-to-video | `wan2.6-i2v`, `wan2.6-i2v-flash` | `video-generation` | `input.img_url` |
| Legacy first/last-frame image-to-video | `wan2.2-kf2v-flash` | `image2video` | `input.first_frame_url`, `input.last_frame_url` |
| Reference-to-video | `wan2.6-r2v`, `wan2.6-r2v-flash` | `video-generation` | `input.reference_urls[]` |
| Wan 2.7 video editing | `wan2.7-videoedit` | `video-generation` | `input.media[]` with one `video` and optional reference images |
| VACE video editing | `wan2.1-vace-plus` | `video-generation` | `input.function` plus function-specific inputs |

## Wan 2.7 Image-To-Video Media Types

`wan2.7-i2v` uses `input.media` objects:

- `first_frame`
- `last_frame`
- `driving_audio`
- `first_clip`

Supported combinations:

- `first_frame`
- `first_frame + driving_audio`
- `first_frame + last_frame`
- `first_frame + last_frame + driving_audio`
- `first_clip`
- `first_clip + last_frame`

Parameters:

- `resolution`: `720P` or `1080P`, default `1080P`
- `duration`: integer in `[2, 15]`, default `5`
- `prompt_extend`: boolean, default `true`
- `watermark`: boolean, default `false`
- `seed`: integer in `[0, 2147483647]`

## Text-To-Video Notes

Current recommended text-to-video family is `wan2.7-t2v`; keep `wan2.6-t2v` as a compatibility fallback when SDK or account constraints require it.

Important parameters:

- `size`: concrete resolution such as `1280*720` or `1920*1080`
- `duration`: model-dependent, `wan2.7-t2v` and `wan2.6-t2v` support integer seconds in `[2, 15]`
- `prompt_extend`
- `shot_type`: `single` or `multi`, only effective for Wan 2.6 when `prompt_extend=true`
- `audio_url`: optional input field for models that support audio

## Wan 2.7 Video Editing Notes

`wan2.7-videoedit` uses `input.media` objects:

- `video`: required, exactly one source video
- `reference_image`: optional, up to three reference images

The official parameter set includes:

- `resolution`: `720P` or `1080P`, default `1080P`
- `ratio`: optional output aspect ratio, such as `16:9`, `9:16`, `1:1`, `4:3`, or `3:4`
- `duration`: omit or pass `0` to preserve input duration, or use `2` to `10` to truncate
- `audio_setting`: `auto` or `origin`
- `prompt_extend`
- `watermark`
- `seed`

## VACE Function Names

VACE uses `input.function`.

Known functions:

- `image_reference`
- `video_repainting`
- `video_edit`
- `video_extension`
- `video_outpainting`

Function-specific fields are kept in `input` and passed through via structured spec.

## Local Boundary

The local runner validates the common envelope and public URLs.

It does not fully encode every model-specific matrix from the official docs. When using advanced VACE/reference modes, prefer `--spec-file` and let the official API reject model-specific mismatches.

Local runner mode/default behavior is defined in:

- [video-runner-spec.md](F:/Documents/Playground/wan2.7-image-demo/references/video-runner-spec.md)
