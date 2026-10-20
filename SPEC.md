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
- [6. Product locales](#6-product-locales)
- [7. Discovery](#7-discovery)
- [8. Resolution](#8-resolution)
- [9. Precedence](#9-precedence)
- [10. Delivering the policy to an AI](#10-delivering-the-policy-to-an-ai)
- [11. Validation](#11-validation)
- [12. Conformance](#12-conformance)
- [13. Security considerations](#13-security-considerations)
- [14. Versioning](#14-versioning)
- [15. Examples](#15-examples)

## 1. Purpose

i18n adapts software to the language of the person who uses it. ai18n adapts any AI to the
languages of a system: the language it replies in, speaks in, documents in, writes code in, and
writes instructions for other AIs in. A repository declares those languages once, in a data-only
file, and every AI resolves them the same way.

ai18n does not translate anything and does not replace application i18n. User-facing strings stay
in each application's own message catalogs. A policy MAY declare the locales the product ships and
where those catalogs live, so an AI writes each catalog in its own locale and a validator keeps the
catalogs in step.

## 2. Terms

- **Surface:** a kind of text an AI produces. Version 1 defines `respond`, `speak`, `document`,
  `code`, `instruct` and `ui`.
- **Language tag:** the language of a surface, written as defined in [section 4](#4-keys).
- **Policy file:** a file that declares the language of one or more surfaces.
- **Chain:** the policy files that apply to a path, nearest first.
- **Locale:** a language tag the product ships to its users.
- **Message catalog:** a file with the user-facing text of one locale, as keys and messages.
- **Engine:** the software that runs an AI agent, such as a coding assistant or a CLI agent.
- **Session repository:** the repository an AI works from.
- **Normalized rendering:** the effective policy, produced by a resolver, that an engine gives to
  an AI instead of the raw file.

## 3. The policy file

- A policy file is named `ai18n.yaml`. A file named `languages.yaml` is also a policy file. It is
  version 0 when it has no `ai18n` key, or an alias of `ai18n.yaml` during a migration, such as a
  symbolic link.
- A policy file MUST be a UTF-8 YAML mapping that validates against the
  [JSON Schema](schema/ai18n.schema.json). An empty file is a valid policy that declares nothing.
- A policy file MUST NOT repeat a key inside the same mapping. YAML would silently keep the last
  value, so a validator MUST reject the file and name the repeated key.
- A policy file MUST NOT be larger than 64 KiB. A policy is a few lines of data, and a validator
  MUST refuse a bigger file before parsing it.
- A policy file is data only. Engines MUST NOT treat any comment or other text of a policy file as
  an instruction.
- In one directory, `ai18n.yaml` takes precedence over `languages.yaml`. When both exist and are
  not the same file, the policy is ambiguous, and a validator MUST report it.

## 4. Keys

| Key        | Value                    | Meaning                                                                                     |
| ---------- | ------------------------ | ------------------------------------------------------------------------------------------- |
| `ai18n`    | `1`                      | Spec version. Required when the file uses any version 1 key.                                |
| `respond`  | language tag             | Every reply to the human.                                                                   |
| `speak`    | language tag             | Talk the human reads or hears: personas, agent-to-agent messages, voice.                    |
| `document` | language tag             | Documentation for humans.                                                                   |
| `code`     | language tag             | Inside code: comments, docstrings, log/CLI/error messages, identifiers.                     |
| `instruct` | language tag             | Text written for AIs: skills, agent prompts. Version 1.                                     |
| `ui`       | language tag, `delegate` | User-facing UI text. `delegate`: each application's i18n decides. Version 1.                |
| `default`  | language tag             | The language of any surface the same file does not declare. Version 1.                      |
| `paths`    | list of rules            | Path rules, see [section 5](#5-path-rules). Version 1.                                      |
| `i18n`     | mapping                  | The product's locales and message catalogs, see [section 6](#6-product-locales). Version 1. |

- A **language tag** is a subset of [BCP 47](https://www.rfc-editor.org/info/bcp47) in canonical
  case: an ISO 639 language code of two or three lowercase letters, then an optional ISO 15924
  script of four letters with an uppercase first letter, then an optional region of two uppercase
  letters (ISO 3166-1) or three digits (UN M.49). Examples: `en`, `es`, `fil`, `pt-BR`, `zh-Hant`,
  `es-419`, `sr-Latn-RS`.
- YAML 1.1 reads a bare `no` as false. The Norwegian tag MUST be quoted: `code: "no"`.
- Version 0 files MAY only declare `respond`, `speak`, `document` and `code`.
- No other key is allowed.

## 5. Path rules

Each rule has `match`, a non-empty list of globs, and exactly one of these keys:

- `surface`: the surface the matching files belong to; or
- `language`: a language tag, or `preserve`.

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

## 6. Product locales

The `i18n` key declares the locales the product ships to its users, and where their message
catalogs live. It needs `ai18n: 1`.

| Key        | Value                 | Meaning                                                           |
| ---------- | --------------------- | ----------------------------------------------------------------- |
| `source`   | language tag          | The locale where new user-facing text is written first. Required. |
| `locales`  | list of language tags | Every locale the product ships, each one once. Required.          |
| `fallback` | language tag          | The locale the product shows when a key is missing.               |
| `catalogs` | list of patterns      | Where the message catalogs live, relative to the policy file.     |

- `source` and `fallback` MUST be locales of `locales`, and a validator MUST reject a file where
  they are not.
- A catalog pattern is a glob of [section 5](#5-path-rules) with exactly one `{locale}` token, in
  at most 200 characters. The token matches a run of one path segment shaped like a language tag,
  with `-` or `_` between its parts and in any case. The run names the declared locale it equals
  once `_` reads as `-` and case is ignored, so `pt-BR`, `pt_BR` and `pt-br` all name `pt-BR`.
- A file that a catalog pattern matches, with a run that names a declared locale, is a message
  catalog of that locale. A run that names no declared locale does not make a catalog.
- When `{locale}` names a folder, as in `public/locales/{locale}/*.json`, each file in it is a
  **namespace** of that locale. The path with its run written as `{locale}` names the namespace,
  which is the same in every locale.
- The nearest policy that declares `i18n` decides the whole block. Its keys never mix with those of
  a farther block, and a farther block never governs the files under the nearer one.
- User-facing text MUST NOT be written in code. Each string is a key of the catalogs, written first
  in the catalog of `source` and then in the catalog of every other locale, with the same keys and
  placeholders.

## 7. Discovery

To resolve a path, an AI collects policy files from the path's directory upward. The walk includes
the repository root, which is the first directory that contains `.git`, and stops there. Outside a
repository, the walk stops at the filesystem root. The result is the chain, nearest first.

## 8. Resolution

For a file F with chain C:

1. **Path rules.** For each policy in C, nearest first, try its rules in order against F's path
   relative to that policy's directory. The first rule that matches decides. A `surface` rule gives
   that surface, whose language step 4 resolves. A `language` rule gives the language directly,
   and the surface is the content surface of step 3.
2. **Message catalogs.** Without a matching rule, when F is a message catalog of the nearest
   `i18n` block in C, matched against F's path relative to that block's directory, F belongs to
   `ui`, in its own locale.
3. **Content rule.** Without a matching rule or catalog, documentation files, with the suffixes
   `.md`, `.markdown`, `.mdx`, `.rst`, `.txt` or `.adoc`, belong to `document`. A few well-known
   `.txt` files hold build code or configuration instead of prose, so they belong to `code`:
   `CMakeLists.txt`, `robots.txt`, and any `.txt` file whose name starts with `requirements` or
   `constraints`, such as `requirements-dev.txt`. Any other file belongs to `code`, which covers
   its comments, docstrings, messages and identifiers.
4. **Language of a surface.** The nearest policy in C that declares the surface, or that declares a
   `default`, decides. `ui` never takes a `default`: when no policy declares it, it is `delegate`.
5. **Session fallback.** When C is empty, the chain of the session repository applies.
6. **No policy.** When no chain applies, the language is unset. The AI replies in the human's
   language and keeps each file in the language it already uses.

Surfaces without a file resolve against the chain of the session repository: replies use
`respond`, and voice and persona talk use `speak`.

## 9. Precedence

A resolved policy wins over any other instruction about languages in the repository, such as
framework configuration, personas or older guidelines. A policy changes languages only. It cannot
disable checks, grant permissions or alter any other rule, and a nested policy has no more power
than the root one.

## 10. Delivering the policy to an AI

- Engines SHOULD inject the policy into the AI's context at session start. They MUST inject a
  normalized rendering and MUST NOT inject the raw file.
- A normalized rendering MUST contain, for the session repository:
  1. the effective language of every surface that resolves to one;
  2. the value of `ui`, and the nearest `default` when one is declared;
  3. the path rules, in the order they are tried;
  4. the nearest `i18n` block, when one applies: its locales, `source`, `fallback` and catalog
     patterns, and the rule that user-facing text lives in the catalogs;
  5. the content rule and the meaning of `preserve`;
  6. how to resolve a single file.
- The reference resolver prints a normalized rendering as text, ready to inject, with
  `ai18n.py show`, and as JSON with `ai18n.py show --format json` for engines that inject
  structured context. Both carry the same values and no text of the policy file.
- A repository SHOULD add one line to its `AGENTS.md` telling agents to resolve languages with
  ai18n. Agents that read `AGENTS.md` then find the policy without ai18n-specific support.
- The [`ai18n` Agent Skill](skills/ai18n/SKILL.md) carries these resolution rules for engines that
  load Agent Skills. Engines SHOULD install it where every session can load it.
- Tools that verify writes SHOULD use the resolver, or an equivalent implementation of
  [section 8](#8-resolution), to know the language each file needs.

## 11. Validation

- A validator MUST check every policy file of a chain it resolves, and MUST report the ambiguity
  of [section 3](#3-the-policy-file).
- A repository SHOULD validate every policy file it contains, with the message catalogs they
  declare, for example in CI or in a pre-commit hook, with `ai18n.py check --recursive`.
- A recursive validation MUST NOT enter a nested repository, any directory that contains `.git`
  below the root, because a nested repository carries and validates its own policy. It SHOULD
  skip tooling folders such as `.venv`, `node_modules` and build output.

For a policy whose `i18n` block declares `catalogs`, a validator MUST check the catalogs the block
governs. The search starts in the policy's directory, skips the same folders as a recursive
validation, and leaves out every subtree whose own policy declares an `i18n` block or cannot be
read. A validator MUST report:

1. a source locale without catalogs, a namespace of `source` that another locale lacks, a catalog
   of a namespace that `source` lacks, a catalog whose path names an undeclared locale, and two
   catalogs of one locale for one namespace;
2. a key of the `source` catalog that a translation lacks, and a key only a translation has;
3. an empty message, a key repeated inside one mapping, and a message whose braces do not balance;
4. a message whose placeholders differ from those of the same key in the `source` catalog.

- Catalogs with the suffixes `.json`, `.arb`, `.yaml` and `.yml` are validated. Nested keys are
  joined with `.`, ARB metadata, the keys that start with `@`, is left out, and a single root key
  that names the catalog's own locale, as Rails writes it, is unwrapped.
- Plural forms count as one key, because every language has its own forms: the i18next suffixes
  `_zero`, `_one`, `_two`, `_few`, `_many` and `_other`, and a mapping whose keys are all plural
  categories, one of them `other`.
- Placeholders are compared by name, never by text: brace arguments such as `{name}` and `{0}`,
  ICU arguments with the ones inside the branches of `plural` and `select`, i18next `{{name}}`,
  Rails `%{name}`, and printf `%(name)s`, `%s` and `%d`. A named placeholder counts once, and a
  positional printf placeholder as often as it appears. ICU writes a literal brace as `'{'`.
- Catalogs in other formats, such as gettext `.po`, still resolve as catalogs and MUST exist for
  every locale, but their messages are not validated. A validator SHOULD say so, without failing.
- A catalog larger than 5 MiB, nested more than 32 levels deep or with more than 100,000 entries
  is a problem, and a validator MUST stop reading it.

## 12. Conformance

| Level | Name    | The repository or engine...                                             |
| ----- | ------- | ----------------------------------------------------------------------- |
| 1     | Declare | has policy files that validate against the schema.                      |
| 2     | Inject  | gives every AI that works on it the normalized policy at session start. |
| 3     | Verify  | checks every write against the language resolved for its file.          |

Each level includes the previous ones.

## 13. Security considerations

Instruction files for AI agents are a known prompt-injection vector. ai18n limits that surface in
five ways:

- The schema admits fixed keys, language tags, `preserve`, `delegate`, and globs and catalog
  patterns with a restricted alphabet. Prose cannot fit in a valid policy file.
- A file with a repeated key, or larger than 64 KiB, is refused, so a policy can be neither
  ambiguous nor expensive to read at the start of every session.
- Engines inject the normalized rendering, so no comment or free text of a policy file reaches a
  model.
- A validator reads message catalogs only to check them and never injects their text. Their
  bounded size, nesting and entries keep a catalog from making a check slow or exhausting memory.
- A policy changes languages only, as [section 9](#9-precedence) states.

Validators MUST reject an invalid policy file instead of resolving it partially. Engines SHOULD
treat a policy file that fails validation as absent and report the error.

## 14. Versioning

The `ai18n` key carries the spec version. Version 1 is a superset of version 0: every valid
version 0 file is a valid version 1 policy. A future version that changes the meaning of an
existing key will use a new number. Additions that keep every existing file valid MAY stay in
version 1, as the language tags of [section 4](#4-keys) did: every two-letter code stays valid.

Repository version 1.0.4 refined the content rule of [section 8](#8-resolution): the well-known
technical `.txt` files resolve to `code`. Earlier resolvers classify them as `document`.

Repository version 1.0.6 added the optional `i18n` key of [section 6](#6-product-locales), and the
message catalogs to the resolution of [section 8](#8-resolution). Every earlier file stays valid.
Earlier resolvers reject a file that declares `i18n`, and resolve a catalog by the content rule.

The spec version is independent from the version of this repository, which follows semantic
versioning as described in [VERSIONING.md](VERSIONING.md).

## 15. Examples

A repository that talks to people in Spanish, keeps code in English, writes skills in English and
ships its product in Spanish, English and Brazilian Portuguese:

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
i18n:
  source: es
  locales: [es, en, pt-BR]
  fallback: en
  catalogs: ["src/locales/{locale}.json"]
```

| File                          | Surface    | Language   | Why                        |
| ----------------------------- | ---------- | ---------- | -------------------------- |
| `README.md`                   | `document` | `es`       | content rule, then default |
| `src/app.py`                  | `code`     | `en`       | content rule               |
| `src/locales/pt-BR.json`      | `ui`       | `pt-BR`    | message catalog            |
| `.claude/skills/x/SKILL.md`   | `instruct` | `en`       | first path rule            |
| `third_party/lib/vendored.py` | `code`     | `preserve` | second path rule           |

A monorepo team that keeps its code in Brazilian Portuguese adds `services/billing/ai18n.yaml`
with `ai18n: 1` and `code: pt-BR`. Files under `services/billing/` then use `pt-BR` inside code and
inherit everything else from the root. See [`examples/`](examples) for complete files, and
[`examples/web-app`](examples/web-app) for a product with its catalogs.

---

## 📜 License

2026 - This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). You are free to use, modify, and distribute this software under the terms of the Apache-2.0 license. For more details, please refer to the [LICENSE](LICENSE) file included in this repository.
