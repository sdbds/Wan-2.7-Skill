# Wan Video Runner Spec

This file defines the execution contract for the local video runner.

## Mode Classes

The runner has two classes of video tasks.

Managed modes:

- `t2v`: text-to-video convenience path
- `i2v`: `wan2.7-i2v` media-based image-to-video path
- `videoedit`: `wan2.7-videoedit` media-based editing path

Raw mode:

- reference-to-video models such as `wan2.6-r2v`
- VACE models such as `wan2.1-vace-plus`
- legacy image-to-video models such as `wan2.6-i2v` and `wan2.2-kf2v-flash`
- any explicit model that is not one of the managed models

## Defaults

Workspace video defaults are applied only to managed modes.

- `defaults.video.t2v` applies only to text-to-video managed mode.
- `defaults.video.i2v` applies only to `wan2.7-i2v`.
- `defaults.video.videoedit` applies only to `wan2.7-videoedit`.
- Raw mode never receives workspace video defaults.

Reason: advanced API families have model-specific parameter matrices, and local defaults can silently create invalid or expensive requests.

## Validation

Managed mode uses strict local validation:

- reject unsupported input keys
- reject unsupported parameter keys
- normalize common booleans and integers
- validate `wan2.7-i2v` media combinations
- validate `wan2.7-videoedit` media combinations

Raw mode uses minimal envelope validation:

- `model` must be explicit
- `input` and `parameters` must be JSON objects when present
- known URL fields are checked as public HTTP/HTTPS URLs
- `input.media[]` items are checked for object shape and public URLs
- unknown input and parameter keys are preserved for the official API

## Update Semantics

`update_video_defaults.py` must preserve existing video defaults by default.

- If `defaults.video` is missing, create a complete conservative video-default block.
- If `defaults.video` exists, update only fields explicitly supplied on the CLI.
- Use `--reset` only when replacing the whole `defaults.video` block intentionally.

## Download Semantics

Video downloads must stream to disk.

Do not read the entire response body into memory before writing the file.
