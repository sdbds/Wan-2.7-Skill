# Wan 2.7 Prompt Task Types

This file defines prompt-side task types for the local `wan-2.7` skill.

Design goal:

- keep the runner generic
- keep prompt construction explicit
- avoid hidden prompt rewriting
- map common user intents to a small number of stable templates

These task types are based on the official Wan 2.7 image-edit doc's verified capability surface:

- text instruction is the primary control channel
- multi-image input is supported
- `bbox_list` enables precise regional editing
- wan2.7 models are suitable for precise local edits and multi-panel continuous output

Not included on purpose:

- detection / segmentation as a dedicated task type

Reason:

- the doc headline mentions it, but the current page does not define a dedicated request/response contract for the local runner to rely on
- the local runner currently only guarantees image-generation/editing flows, not structured detection outputs

## Task Type Table

| Task type | Use when | Image count | Extra parameter hint |
| --- | --- | --- | --- |
| `t2i_scene` | user wants pure text-to-image | 0 | none |
| `edit_rewrite` | user wants single-image or multi-image instruction-based edit | 1-9 | none |
| `multi_image_fusion` | one image provides scene/base, others provide objects/styles/materials | 2-9 | none |
| `subject_preserve` | user wants to keep identity / product / object traits stable while changing scene or action | 1-9 | none |
| `bbox_precise_edit` | user wants local editing in a known region | 1-9 | `bbox_list` |
| `sequential_series` | user wants multiple coherent frames / panels / series images | 0-9 | `enable_sequential=true` |

## Portrait overlay

Portrait / avatar / headshot /证件照 requests are not a separate runner task type.

They are a chat-side prompt-building overlay on top of the existing task types:

- no input image -> `t2i_scene`
- input image + identity preservation -> `subject_preserve`
- input image + general portrait edit -> `edit_rewrite`
- localized portrait edit with confirmed box -> `bbox_precise_edit`

Before writing the final prompt for a people-centric request, run the portrait chat flow:

- [portrait-chat-flow.md](F:/Documents/Playground/wan2.7-image-demo/references/portrait-chat-flow.md)
- [portrait-data-schema.md](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data-schema.md)

Use the local carrier / trigger data as the source of truth:

- [triggers_by_dim.json](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data/triggers_by_dim.json)
- [carriers.json](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data/carriers.json)

This keeps portrait prompting structured without polluting the runner with a fake new mode.

This is not optional.

If the primary subject is a person, portrait guidance must run before final prompt assembly.
When the user already gave many traits, pre-fill them and ask only the remaining slots instead of skipping the flow.

## Template Rules

- Always assign a role to each input image when there are multiple images.
- State what must stay unchanged before stating what should change.
- For editing tasks, ask for natural fusion of perspective, lighting, scale, edge transition, and shadows.
- Because the image runner does not support `negative_prompt` or `prompt_extend`, write image prompts explicitly instead of relying on hidden cleanup.
- Keep prompts concrete. Do not stack style adjectives without target objects, scene constraints, and preservation rules.

## `t2i_scene`

Use for pure text-to-image generation.

If the request is portrait-centric, first build the person descriptor through the portrait flow, then place the result in `主体与关键元素`.

Template:

```text
生成一张[主体]的图像。
主体与关键元素：[主体外观、数量、材质、服饰、道具]
场景与动作：[场景、动作、互动关系]
构图与镜头：[远景/中景/特写、视角、景别]
光线与色彩：[时间、光源、整体色调]
风格与质感：[写实/插画/电影感/产品图等]
输出要求：[清晰度、细节重点、是否需要留白]
```

Short example:

```text
生成一张透明玻璃杯的产品图。
主体与关键元素：单个高脚透明玻璃杯，杯壁干净通透，桌面有少量水珠。
场景与动作：放置在浅灰色石材台面上，无其他干扰物。
构图与镜头：中近景，轻微俯拍，主体居中。
光线与色彩：柔和侧光，冷白色调，反射自然。
风格与质感：高端电商产品摄影，写实。
输出要求：边缘清晰，玻璃高光自然，不过曝。
```

## `edit_rewrite`

Use for general instruction-based editing without explicit bbox.

Template:

```text
基于图像进行编辑，只修改[目标内容]。
修改内容：[要替换/新增/删除/移动的内容]
必须保留：[主体身份、姿态、构图、背景、材质、文字等]
融合要求：编辑结果与原场景的透视、光线、阴影、尺度和边缘过渡自然一致。
画面要求：[写实/海报感/插画感/商品图等]
```

Short example:

```text
基于图像进行编辑，只修改桌面上的杯子。
修改内容：把原来的马克杯替换为透明玻璃杯，杯中加入少量清水。
必须保留：桌面材质、相机视角、周围物体位置和整体构图不变。
融合要求：透视、反光、阴影和边缘过渡自然一致。
画面要求：写实摄影风格。
```

## `multi_image_fusion`

Use when each image plays a different role.

Template:

```text
以图1作为[主场景/底图/主体来源]。
以图2作为[物体/风格/纹理/动作]参考。
[若有图3/图4，继续明确角色]
执行目标：[把哪个元素放到哪里 / 融合什么关系]
必须保留：[图1的场景结构 / 图2的关键特征 / 图3的风格等]
融合要求：元素尺度正确，接触关系合理，光线、透视、材质和阴影自然统一。
```

Short example:

```text
以图1作为主场景和底图。
以图2作为涂鸦图案参考。
执行目标：把图2的涂鸦喷绘在图1的汽车侧门上。
必须保留：图1汽车造型、车身透视、场景环境不变；图2图案的主要颜色和笔触风格保持。
融合要求：喷绘位置贴合车身曲面，光线和反射自然。
```

## `subject_preserve`

Use when identity consistency matters.

If the subject is a person, treat the portrait flow result as the preservation contract instead of improvising identity traits freehand.

Template:

```text
保持图1主体的核心特征不变：[脸型/发型/肤色/服装关键件/产品外形/品牌元素]
在此基础上修改：[场景 / 动作 / 服饰局部 / 背景 / 风格]
必须保持一致：[身份识别特征、材质、比例、关键标识]
允许变化：[姿态、镜头、环境、附属道具]
画面要求：结果自然，不出现主体身份漂移或结构变形。
```

Short example:

```text
保持图1人物的脸型、发型、五官特征和白色外套不变。
在此基础上修改：把背景改成城市夜景街头，并让人物手里拿一把透明雨伞。
必须保持一致：人物身份特征、年龄感和服装主体不变。
允许变化：姿态轻微调整，环境和灯光可变化。
画面要求：写实自然，不出现换脸感。
```

## `bbox_precise_edit`

Use when the edit target is localized and a box is available or can be proposed in chat.

Template:

```text
仅编辑框选区域。
编辑目标：[替换 / 新增 / 删除 / 搬运的对象]
[若多图] 图1提供[对象/元素]，图2的框选区域是目标位置。
框外内容保持不变。
融合要求：编辑结果与周围区域的光线、透视、尺度、材质、阴影和边缘过渡自然一致。
```

Short example:

```text
仅编辑框选区域。
图1提供闹钟，图2的框选区域是目标位置。
把图1的闹钟放到图2框选的位置。
框外内容保持不变。
融合要求：与桌面、花瓶和环境光自然融合，尺度和透视正确。
```

## `sequential_series`

Use when the user wants multiple related outputs with continuity.

Template:

```text
生成一组连续画面，共[n]张。
统一约束：[主角身份、服饰、画风、镜头语言、色调]
第1张：[画面1内容]
第2张：[画面2内容]
第3张：[画面3内容]
[继续列出]
要求：各张图之间角色和世界观保持一致，情节连续，构图有明显区分。
```

Short example:

```text
生成一组连续画面，共3张。
统一约束：同一个橙色短毛猫宇航员，白色宇航服，电影感写实风格，冷暖对比光。
第1张：猫宇航员走出飞船舱门，回头看向月面基地。
第2张：猫宇航员在月面插下一面小旗，脚边有扬起的月尘。
第3张：猫宇航员坐在月球岩石上看向远处地球。
要求：角色造型和服装保持一致，三张图像具有连贯叙事关系。
```
