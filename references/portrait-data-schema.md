# Wan 2.7 Portrait Data Schema

This file defines the expected schema for portrait data used by the local `wan-2.7` skill.

Design goal:

- keep portrait selection rules in data, not only in prose
- avoid polymorphic guessing in `slot_source`
- keep carrier selection deterministic across implementations

## Trigger dimensions

Source file:

- [triggers_by_dim.json](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data/triggers_by_dim.json)

Rules:

- each top-level key is a selectable dimension
- each value is a non-empty array of strings
- gender and age are separate dimensions
  - `J0_性别`
  - `J1_年龄段`
- the legacy mixed dimension `J1_性别年龄` must not be used

## Carrier shape

Source file:

- [carriers.json](F:/Documents/Playground/wan2.7-image-demo/references/portrait-data/carriers.json)

Each carrier must provide:

- `carrier_id`
- `name`
- `description`
- `template`
- `slots`
- `build_depth`
- `use_cases`

Optional:

- `fixed`
- `slot_source`

## Carrier selection metadata

Carrier recommendation must use data fields, not only free-text descriptions.

Required data fields:

- `build_depth`
  - allowed: `quick`, `standard`, `deep`
- `use_cases`
  - non-empty string array such as:
    - `id_photo`
    - `general_portrait`
    - `documentary_portrait`
    - `child_portrait`
    - `senior_portrait`
    - `full_face`
    - `expression_test`
- `fixed`
  - hard constraints such as gender, age, ethnicity

Selection order:

1. user intent -> `use_cases`
2. requested control depth -> `build_depth`
3. hard demographic constraints -> `fixed`
4. `slots` length only as a tiebreaker

## `slot_source` schema

`slot_source` must be explicit. No inferred list semantics.

Allowed forms:

### 1. No `slot_source`

Meaning:

- use `triggers_by_dim[slot]`

### 2. `literal_values`

```json
{
  "kind": "literal_values",
  "values": ["男性", "女性"]
}
```

Meaning:

- use the listed values directly

### 3. `dim_union`

```json
{
  "kind": "dim_union",
  "dims": ["G1_表情正面", "G2_表情中性", "G3_表情负面"]
}
```

Meaning:

- the slot is backed by multiple dimensions
- chat should ask the user which family to enter first, then show concrete values

### 4. `filtered_dim`

```json
{
  "kind": "filtered_dim",
  "dim": "J1_年龄段",
  "values": ["青年（18-30岁）", "中青年（30-45岁）"]
}
```

Meaning:

- use only the listed subset from the referenced dimension

## Invariants

- `template` placeholders must exactly match `slots`
- all `fixed` values must belong to real trigger dimensions
- all `slot_source` objects must use one of the supported `kind` values
- no mixed or inferred list semantics are allowed in `slot_source`
