# 📐 ai18n Specification

**Version:** 1 · **Status:** Stable · **Schema:** [`schema/ai18n.schema.json`](schema/ai18n.schema.json) ·
**Reference resolver:** [`src/ai18n.py`](src/ai18n.py)

The key words "MUST", "MUST NOT", "SHOULD", "SHOULD NOT" and "MAY" in this document are to be
interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

## 📚 Table of Contents

- [1. Purpose](#1-purpose)
- [2. Terms](#2-terms)
- [3. The policy file](#3-the-policy-file)
- [4. Keys](#4-keys)
- [5. Path rules](#5-path-rules)
- [6. Discovery](#6-discovery)
- [7. Resolution](#7-resolution)
- [8. Precedence](#8-precedence)
- [9. Delivering the policy to an AI](#9-delivering-the-policy-to-an-ai)
- [10. Conformance](#10-conformance)
- [11. Security considerations](#11-security-considerations)
- [12. Versioning](#12-versioning)
- [13. Examples](#13-examples)

## 1. Purpose

i18n adapts software to the language of the person who uses it. ai18n adapts any AI to the
languages of a system: the language it replies in, speaks in, documents in, writes code in, and
writes instructions for other AIs in. A repository declares those languages once, in a data-only
file, and every AI resolves them the same way.

ai18n does not translate anything and does not replace application i18n. User-facing UI strings
stay in each application's own localization files.

## 2. Terms

- **Surface:** a kind of text an AI produces. Version 1 defines `respond`, `speak`, `document`,
  `code`, `instruct` and `ui`.
- **Policy file:** a file that declares the language of one or more surfaces.
- **Chain:** the policy files that apply to a path, nearest first.
- **Engine:** the software that runs an AI agent, such as a coding assistant or a CLI agent.
- **Session repository:** the repository an AI works from.

## 3. The policy file

- A policy file is named `ai18n.yaml`. A file named `languages.yaml` is also a policy file. It is
  version 0 when it has no `ai18n` key, or an alias of `ai18n.yaml` during a migration, such as a
  symbolic link.
- A policy file MUST be a YAML mapping that validates against the
  [JSON Schema](schema/ai18n.schema.json). An empty file is a valid policy that declares nothing.
- A policy file is data only. Engines MUST NOT treat any comment or other text of a policy file as
  an instruction.
- In one directory, `ai18n.yaml` takes precedence over `languages.yaml`. When both exist and are
  not the same file, the policy is ambiguous, and a validator MUST report it.

## 4. Keys

| Key        | Value                  | Meaning                                                                     |
| ---------- | ---------------------- | --------------------------------------------------------------------------- |
| `ai18n`    | `1`                    | Spec version. Required when the file uses any version 1 key.                |
| `respond`  | language               | Every reply to the human.                                                   |
| `speak`    | language               | Talk the human reads or hears: personas, agent-to-agent messages, voice.    |
| `document` | language               | Documentation for humans.                                                   |
| `code`     | language               | Inside code: comments, docstrings, log/CLI/error messages, identifiers.     |
| `instruct` | language               | Text written for AIs: skills, agent prompts. Version 1.                     |
| `ui`       | language or `delegate` | User-facing UI text. `delegate`: each application's i18n decides. Version 1 |
| `default`  | language               | The language of any surface the same file does not declare. Version 1.      |
| `paths`    | list of rules          | Path rules, see [section 5](#5-path-rules). Version 1.                      |

- A **language** is an ISO 639-1 code: two lowercase letters, such as `en`, `es` or `pt`.
- Version 0 files MAY only declare `respond`, `speak`, `document` and `code`.
- No other key is allowed.

## 5. Path rules

Each rule has `match`, a non-empty list of globs, and exactly one of these keys:

- `surface`: the surface the matching files belong to; or
- `language`: a language, or `preserve`.

`preserve` means the matching text keeps the language it already has. An AI MUST NOT translate it.
Use it for vendored code, copies of third-party files and any text that must stay byte for byte.

Globs are relative to the directory of the policy file that declares them, and use `/` as the
separator:

| Glob  | Matches                                       |
| ----- | --------------------------------------------- |
| `**/` | zero or more whole directories                |
| `**`  | anything, including `/`                       |
| `*`   | any run of characters inside one path segment |
| `?`   | exactly one character inside one path segment |

A glob MAY only contain letters, digits, `_`, `.`, `/`, `*`, `?` and `-`, and at most 200
characters. A glob matches the whole relative path: `**/skills/**` matches `a/skills/x.md` but not
`a/myskills/x.md`.

## 6. Discovery

To resolve a path, an AI collects policy files from the path's directory upward. The walk includes
the repository root, which is the first directory that contains `.git`, and stops there. Outside a
repository, the walk stops at the filesystem root. The result is the chain, nearest first.

## 7. Resolution

For a file F with chain C:

1. **Path rules.** For each policy in C, nearest first, try its rules in order against F's path
   relative to that policy's directory. The first rule that matches decides. A `surface` rule gives
   that surface, whose language step 3 resolves. A `language` rule gives the language directly,
   and the surface is the content surface of step 2.
2. **Content rule.** Without a matching rule, documentation files, with the suffixes `.md`,
   `.markdown`, `.mdx`, `.rst`, `.txt` or `.adoc`, belong to `document`. Any other file belongs to
   `code`, which covers its comments, docstrings, messages and identifiers.
3. **Language of a surface.** The nearest policy in C that declares the surface, or that declares a
   `default`, decides. `ui` never takes a `default`: when no policy declares it, it is `delegate`.
4. **Session fallback.** When C is empty, the chain of the session repository applies.
5. **No policy.** When no chain applies, the language is unset. The AI replies in the human's
   language and keeps each file in the language it already uses.

Surfaces without a file resolve against the chain of the session repository: replies use
`respond`, and voice and persona talk use `speak`.

## 8. Precedence

A resolved policy wins over any other instruction about languages in the repository, such as
framework configuration, personas or older guidelines. A policy changes languages only. It cannot
disable checks, grant permissions or alter any other rule, and a nested policy has no more power
than the root one.

## 9. Delivering the policy to an AI

- Engines SHOULD inject the policy into the AI's context at session start. They MUST inject a
  normalized rendering, such as the output of `ai18n.py show`, and MUST NOT inject the raw file.
- A repository SHOULD add one line to its `AGENTS.md` telling agents to resolve languages with
  ai18n. Agents that read `AGENTS.md` then find the policy without ai18n-specific support.
- The [`ai18n` Agent Skill](skills/ai18n/SKILL.md) carries these resolution rules for engines that
  load Agent Skills. Engines SHOULD install it where every session can load it.
- Tools that verify writes SHOULD use the resolver, or an equivalent implementation of
  [section 7](#7-resolution), to know the language each file needs.

## 10. Conformance

| Level | Name    | The repository or engine...                                             |
| ----- | ------- | ----------------------------------------------------------------------- |
| 1     | Declare | has a policy file that validates against the schema.                    |
| 2     | Inject  | gives every AI that works on it the normalized policy at session start. |
| 3     | Verify  | checks every write against the language resolved for its file.          |

Each level includes the previous ones.

## 11. Security considerations

Instruction files for AI agents are a known prompt-injection vector. ai18n limits that surface in
three ways:

- The schema admits fixed keys, ISO 639-1 codes, `preserve`, `delegate` and globs with a restricted
  alphabet. Prose cannot fit in a valid policy file.
- Engines inject the normalized rendering, so no comment or free text of a policy file reaches a
  model.
- A policy changes languages only, as [section 8](#8-precedence) states.

Validators MUST reject an invalid policy file instead of resolving it partially. Engines SHOULD
treat a policy file that fails validation as absent and report the error.

## 12. Versioning

The `ai18n` key carries the spec version. Version 1 is a superset of version 0: every valid
version 0 file is a valid version 1 policy. A future version that changes the meaning of an
existing key will use a new number. Additions that keep every existing file valid MAY stay in
version 1.

## 13. Examples

A repository that talks to people in Spanish, keeps code in English and writes skills in English:

```yaml
ai18n: 1
default: es
code: en
instruct: en
ui: delegate
paths:
  - match: ["**/SKILL.md", "**/skills/**"]
    surface: instruct
  - match: ["third_party/**"]
    language: preserve
```

| File                          | Surface    | Language   | Why                        |
| ----------------------------- | ---------- | ---------- | -------------------------- |
| `README.md`                   | `document` | `es`       | content rule, then default |
| `src/app.py`                  | `code`     | `en`       | content rule               |
| `.claude/skills/x/SKILL.md`   | `instruct` | `en`       | first path rule            |
| `third_party/lib/vendored.py` | `code`     | `preserve` | second path rule           |

A monorepo team that keeps its code in Portuguese adds `services/billing/ai18n.yaml` with
`ai18n: 1` and `code: pt`. Files under `services/billing/` then use `pt` inside code and inherit
everything else from the root. See [`examples/`](examples) for complete files.

---

## 📜 License

2026 - This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). You are free to use, modify, and distribute this software under the terms of the Apache-2.0 license. For more details, please refer to the [LICENSE](LICENSE) file included in this repository.
