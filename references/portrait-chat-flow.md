# Wan 2.7 Portrait Chat Flow

This file defines the chat-side flow for building portrait / people prompts in the local `wan-2.7` skill.

Goal:

- treat people prompts as structured slot filling instead of adjective dumping
- reuse local carrier/template data instead of relying on memory
- keep the interaction stepwise, like a character creator
- avoid asking for every possible dimension when the user only needs a simple portrait

Core references:

- [triggers_by_dim.json](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data/triggers_by_dim.json)
- [carriers.json](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data/carriers.json)
- [portrait-data-schema.md](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data-schema.md)

## Trigger this flow when

Use the portrait flow whenever the user wants a human-centered result and facial / identity traits are part of the request.

This is mandatory for people-centric generation requests.

If the primary subject is a person, the chat layer must enter portrait guidance before final prompt assembly.
If the user already supplied many traits, pre-fill those slots and continue from the unresolved ones.

Typical triggers:

- `人物`
- `人像`
- `半身像`
- `头像`
- `证件照`
- `写真`
- `avatar`
- `headshot`
- `生成一个东亚女青年`
- `给我做一个长相很凶但萌的男生`
- `保持这个人的长相不变`

Do not trigger it when a person is only incidental background clutter and the user does not care about identity traits.

## First principles

1. Portrait flow is a chat-side prompt-building overlay, not a new runner mode.
2. `carrier.fixed` is a hard constraint. If the user wants conflicting traits, switch carriers instead of mutating fixed fields in place.
3. Ask one decision at a time. Do not dump twenty dimensions in one message.
4. By default, show only a small option slice for the current step.
5. Always include:
   - `随机`
   - `跳过`
   - `自定义`
6. If the user already specified a trait clearly, pre-fill that slot and do not ask it again.
7. Do not force a full-face questionnaire for a simple headshot request.

## Flow

### 1. Pick the build depth

Start with one of these modes:

- `快速成型`
- `标准捏脸`
- `深度定制`

Recommended mapping:

- `快速成型`
  - recommend carriers with 1-5 slots
  - good for证件照、基础头像、快速试风格
- `标准捏脸`
  - recommend carriers with 5-12 slots
  - good for明确脸型、眼型、鼻型、唇型、肤色
- `深度定制`
  - recommend full-face or high-variance carriers
  - only use when the user explicitly wants heavy control

### 2. Pick the carrier

Use `carriers.json` as the source of truth.

Carrier selection rules:

- narrow candidates first by carrier data, not by free-text guessing:
  - `use_cases`
  - `build_depth`
  - `fixed`
- use `slots` length only as a tiebreaker
- present 2-4 compatible carriers, not the full catalog
- show:
  - `carrier_id`
  - `name`
  - `description`
  - `build_depth`
  - `use_cases`
  - which traits are fixed
  - which slots will be asked

If the user later requests a trait that conflicts with `carrier.fixed`, do this:

1. stop
2. explain the conflict precisely
3. switch to a compatible carrier

Do not silently override fixed fields.

### 3. Walk slots one by one

After a carrier is selected, follow the exact order in `carrier.slots`.

Slot resolution rules:

- if the slot has no `slot_source`, use `triggers_by_dim[slot]`
- if `slot_source[slot].kind = dim_union`, treat it as a dimension union
  - example: `expression -> { kind: dim_union, dims: [G1_表情正面, G2_表情中性, G3_表情负面] }`
  - first ask the user which expression family they want, then show concrete options
- if `slot_source[slot].kind = literal_values`, use the declared values directly
  - example: `J0_性别 -> { kind: literal_values, values: [男性, 女性] }`
- if `slot_source[slot].kind = filtered_dim`, resolve from the referenced dimension and apply the declared subset
- any other shape is invalid and should be treated as broken data, not guessed at runtime

At each step:

- show 4-8 options, not the full dimension, unless the user asks for more
- keep the options contrasted and representative
- include `随机 / 跳过 / 自定义`
- after selection, update the partial descriptor in one short line

Recommended prompt to the user:

```text
第 3 步：选眼型（B1_眼型）
1. 杏仁眼
2. 丹凤眼
3. 圆眼
4. 狐狸眼
5. 深邃眼窝
6. 随机
7. 跳过
8. 自定义
```

### 4. Offer optional enhancement packs

After the carrier core slots are done, ask whether the user wants to keep going.

Use packs instead of raw dimension soup:

- `发型包`
  - `E1-E7`, plus `E8` when applicable
- `妆容包`
  - `F1-F4`
- `表情包`
  - `G1-G3`
- `配饰包`
  - `G4-G7`
- `服装包`
  - `H1-H3`
- `摄影场景包`
  - `K1-K5`

Only open a pack when the user wants more control there.

### 5. Assemble the final portrait descriptor

Assembly rules:

- start from `carrier.template`
- fill placeholders from the collected slot values
- preserve the template order
- do not reorder the sentence structure unless the template is broken
- if the user chose optional enhancement-pack traits that are not already in the template, append them as short clauses after the base template

Routing rules:

- no input image -> use the assembled descriptor inside `t2i_scene`
- input image + identity must stay stable -> use the assembled descriptor as the preservation block inside `subject_preserve`
- input image + person edit without strong identity preservation -> use it inside `edit_rewrite`
- local face-region edits with confirmed boxes -> use it inside `bbox_precise_edit`

## Hard boundaries

- Do not paste the raw JSON into chat.
- Do not ask every slot in the catalog for a simple request.
- Do not override `carrier.fixed` in place.
- Do not invent dimensions that are not present in the portrait data files.
- Do not collapse the whole process into one giant questionnaire.
- Do not bypass portrait guidance for people-centric generation requests.
