# Wan Video Prompt Task Types

This file defines chat-side prompt templates for video generation in the `wan-2.7` skill.

Use these as guidance for user education and prompt assembly. They are not persistent config.

## Task Type Table

| Task type | Use when | Typical model family |
| --- | --- | --- |
| `video_t2v_scene` | user wants video from text only | `wan2.7-t2v` |
| `video_i2v_first_frame` | user provides a first frame and wants motion | `wan2.7-i2v` |
| `video_i2v_keyframes` | user provides first and last frames | `wan2.7-i2v` |
| `video_i2v_continue` | user provides a first clip and wants continuation | `wan2.7-i2v` |
| `video_reference_performance` | user wants character/object consistency from references | `wan2.7-r2v` |
| `video_vace_edit` | user wants to edit or extend an existing video | `wan2.7-videoedit` or `wan2.1-vace-plus` |

## General Video Prompt Rules

- State subject, action, camera movement, scene, lighting, and timing.
- If continuity matters, describe how the motion evolves from start to end.
- For multi-shot output, explicitly describe shot order.
- For reference-to-video, refer to roles as `character1`, `character2`, etc.
- For first/last-frame generation, describe the transition between frames instead of only describing the final scene.

## `video_t2v_scene`

Template:

```text
生成一段[时长]秒的视频。
主体：[主体外观、数量、服装、材质]
动作：[从开始到结束的动作变化]
场景：[地点、时间、环境元素]
镜头：[景别、视角、运镜、是否单镜头/多镜头]
光线与风格：[光线、色彩、真实感/动画/产品片等]
声音要求：[如果需要有声，描述音乐、环境声或台词]
```

## `video_i2v_first_frame`

Template:

```text
以输入图像作为视频首帧。
保持首帧中的[主体/场景/构图]自然延续。
动作变化：[主体如何运动、镜头如何运动]
场景变化：[哪些元素可以变化，哪些不能变化]
画面要求：运动自然，主体结构稳定，光线和风格延续首帧。
```

## `video_i2v_keyframes`

Template:

```text
以图1作为首帧，以图2作为尾帧。
描述从首帧到尾帧的过渡过程：[主体动作、镜头运动、场景变化]
必须保持：[主体身份、主要物体、画面风格]
允许变化：[姿态、视角、局部环境、光线变化]
画面要求：过渡自然，不出现跳变、断裂或主体漂移。
```

## `video_i2v_continue`

Template:

```text
基于输入视频片段继续生成后续内容。
延续：[主体、场景、镜头语言、运动方向]
后续发展：[接下来发生什么]
节奏：[平稳/加速/转场/停顿]
画面要求：与原片段在风格、光线和运动方向上连续。
```

## `video_reference_performance`

Template:

```text
使用参考素材中的角色顺序：
character1 = [第1个参考中的角色/物体]
character2 = [第2个参考中的角色/物体]
执行内容：[角色动作、互动、台词或表演]
镜头结构：[单镜头/多镜头，以及镜头顺序]
保持要求：角色外观和身份特征来自各自参考素材，动作与场景自然统一。
```

## `video_vace_edit`

Template:

```text
基于输入视频进行编辑。
任务类型：[多图参考 / 视频重绘 / 局部编辑 / 视频延展 / 画面扩展]
编辑目标：[要替换、重绘、扩展或延长的内容]
必须保留：[原视频动作、构图、主体身份、背景或镜头节奏]
变化要求：[新风格、新对象、新背景或扩展方向]
画面要求：编辑区域和未编辑区域过渡自然，视频运动连续。
```

For instruction-based whole-video edits, prefer `wan2.7-videoedit`.

Use VACE (`wan2.1-vace-plus`) only when the user needs an older function-specific mode such as local mask editing, video repainting, extension, or outpainting.
