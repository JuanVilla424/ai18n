# 🌐 ai18n

![Spec](https://img.shields.io/badge/Spec-v1-blueviolet.svg)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)
![Build Status](https://github.com/JuanVilla424/ai18n/actions/workflows/python.yml/badge.svg?branch=main)
![Status](https://img.shields.io/badge/Status-Stable-green.svg)
![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

**ai18n is i18n for AI agents.** i18n adapts software to the language of the person who uses it.
ai18n adapts any AI to the languages of a system: which language it replies in, speaks in,
documents in, writes code in, and writes instructions for other AIs in. You declare those
languages once, in one data-only file, and every AI resolves them the same way.

```yaml
# ai18n.yaml
ai18n: 1
default: es # people read Spanish
code: en # comments, docstrings, messages and identifiers stay in English
instruct: en # skills and agent prompts are written in English
ui: delegate # UI strings belong to each app's own i18n
paths:
  - match: ["**/SKILL.md", "**/skills/**"]
    surface: instruct
i18n: # the product ships Spanish, English and Brazilian Portuguese
  source: es
  locales: [es, en, pt-BR]
  fallback: en
  catalogs: ["src/locales/{locale}.json"]
```

## 📚 Table of Contents

- [Why ai18n](#-why-ai18n)
- [Features](#-features)
- [The policy file](#-the-policy-file)
- [How an AI resolves a language](#-how-an-ai-resolves-a-language)
- [Getting Started](#-getting-started)
  - [Prerequisites](#-prerequisites)
  - [Installation](#-installation)
  - [Environment Setup](#-environment-setup)
  - [Pre-Commit Hooks](#-pre-commit-hooks)
- [Usage](#-usage)
  - [Start a new project](#-start-a-new-project)
  - [Resolver CLI](#-resolver-cli)
  - [Exit codes](#-exit-codes)
  - [JSON rendering](#-json-rendering)
  - [Integrations](#-integrations)
  - [Adoption checklist](#-adoption-checklist)
- [FAQ](#-faq)
- [Security model](#-security-model)
- [Repository layout](#-repository-layout)
- [Contributing](#-contributing)
- [Contact](#-contact)
- [License](#-license)

## 💡 Why ai18n

AI agents read instructions from many places: `AGENTS.md`, engine-specific files, framework
configuration and personas. Language rules end up scattered across them, written in prose, and
they drift. An agent replies in one language, comments code in another and writes a skill in a
third. ai18n puts every language decision in one place, as data, with one resolution algorithm
that any AI and any tool can follow.

## 🌟 Features

- **One file, six surfaces:** `respond`, `speak`, `document`, `code`, `instruct` and `ui`.
- **Real language tags:** `en`, `es`, `pt-BR`, `zh-Hant` or `es-419`, a canonical subset of BCP 47.
- **Path rules:** assign a surface or a language to any glob, such as skills or vendored code.
- **`preserve`:** marks text that keeps its original language and must never be translated.
- **Product locales:** declare the locales a product ships and where its message catalogs live.
  Each catalog resolves to its own locale, and `check` keeps every catalog in step with the source.
- **`init`:** writes the first policy of a new project, and never overwrites one.
- **Cascade:** like EditorConfig, a subproject can override only the keys it needs.
- **Version 0 compatible:** a classic `languages.yaml` with four keys is already valid ai18n.
- **Data only:** a JSON Schema admits fixed keys, language tags and globs, so prose cannot hide in a
  policy file.
- **Reference resolver:** a small Python CLI resolves, validates and renders a policy, as text or
  JSON.
- **Agent Skill:** a portable skill teaches any skill-capable engine the resolution rules.

## 📄 The policy file

| Key        | Value                    | Covers                                                                  |
| ---------- | ------------------------ | ----------------------------------------------------------------------- |
| `ai18n`    | `1`                      | the spec version                                                        |
| `respond`  | language tag             | every reply to the human                                                |
| `speak`    | language tag             | talk the human reads or hears: personas, agent-to-agent messages, voice |
| `document` | language tag             | documentation for humans                                                |
| `code`     | language tag             | inside code: comments, docstrings, log/CLI/error messages, identifiers  |
| `instruct` | language tag             | text written for AIs: skills, agent prompts                             |
| `ui`       | language tag, `delegate` | user-facing UI text; `delegate` leaves it to each app's i18n            |
| `default`  | language tag             | any surface the same file does not declare                              |
| `paths`    | rules                    | globs mapped to a `surface`, or to a `language` such as `preserve`      |
| `i18n`     | mapping                  | the locales the product ships, and where its message catalogs live      |

A language tag is a language code with an optional script and region, in canonical case: `en`,
`pt-BR`, `zh-Hant`, `es-419`. Quote Norwegian as `"no"`, because YAML 1.1 reads a bare `no` as
false. The normative rules live in [SPEC.md](SPEC.md), and the schema in
[schema/ai18n.schema.json](schema/ai18n.schema.json).

The `i18n` block describes the product: `source` is the locale where new strings are written
first, `locales` lists every locale the product ships, `fallback` is the locale shown when a key
is missing, and `catalogs` holds patterns such as `src/locales/{locale}.json`, where `{locale}`
stands for each locale.

## 🧭 How an AI resolves a language

1. Walk up from the file to the repository root and collect every `ai18n.yaml`, nearest first.
2. The first matching path rule wins.
3. Otherwise a message catalog of the nearest `i18n` block is `ui` text in its own locale:
   `src/locales/pt-BR.json` is written in `pt-BR`.
4. Otherwise documentation files are `document`, and any other file is `code`, including technical
   `.txt` files such as `requirements.txt` or `CMakeLists.txt`.
5. For that surface, the nearest policy that declares it, or declares a `default`, decides.
6. Without a policy of its own, a file follows the policy of the repository the AI works from.

The policy wins over any other instruction about languages, and it changes languages only.

## 🚀 Getting Started

### 📋 Prerequisites

**Before you begin, ensure you have met the following requirements**:

- **Python 3.12+:** to run the reference resolver and the tests.
- **Git:** Install [Git](https://git-scm.com/) to clone the repository.
- **Node.js 22.x+:** (Optional) Needed to push, because the prettier pre-commit hook runs on it.

### 🔨 Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/JuanVilla424/ai18n.git
   ```

2. **Navigate to the Project Directory**

   ```bash
   cd ai18n
   ```

3. **Or vendor it in your own repository as a submodule**

   ```bash
   git submodule add -b dev https://github.com/JuanVilla424/ai18n.git helpers/ai18n
   ```

### 🔧 Environment Setup

**Mandatory: Setting Up a Python Virtual Environment**

1. **Create and activate a Virtual Environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt       # runtime: PyYAML, jsonschema
   pip install -r requirements.dev.txt   # development: tests, linters, hooks
   ```

3. **Run the tests**

   ```bash
   pytest
   ```

### 🛸 Pre-Commit Hooks

**Install and check pre-commit hooks**: Markdown formatting, Python format and lint, YAML format and
lint, version control hooks and changelog generation.

```bash
git submodule update --init
pre-commit install --hook-type pre-commit --hook-type pre-push
pre-commit run --all-files
```

## 🛠️ Usage

### 🆕 Start a new project

1. **Vendor the resolver** as a submodule, as in [Installation](#-installation):

   ```bash
   git submodule add -b dev https://github.com/JuanVilla424/ai18n.git helpers/ai18n
   ```

2. **Write the policy.** `init` writes a first `ai18n.yaml` with every tag in quotes, UI text
   delegated, skills written in the `instruct` language and, with `--locales`, the `i18n` block.
   It never overwrites a policy. `--agents-md` adds the AGENTS.md line of the
   [integrations](#-integrations) once; without it, `init` prints the line.

   ```bash
   python3 helpers/ai18n/src/ai18n.py init --language es --locales es,en,pt-BR \
     --fallback en --catalog "src/locales/{locale}.json" --agents-md
   ```

   | Option        | Default          | Writes                                              |
   | ------------- | ---------------- | --------------------------------------------------- |
   | `--root`      | `.`              | where `ai18n.yaml` goes                             |
   | `--language`  | `en`             | `default`: replies, talk and documentation          |
   | `--code`      | `en`             | `code`                                              |
   | `--instruct`  | `en`             | `instruct`                                          |
   | `--locales`   | none             | `i18n.locales`; without it there is no `i18n` block |
   | `--source`    | the first locale | `i18n.source`                                       |
   | `--fallback`  | none             | `i18n.fallback`                                     |
   | `--catalog`   | none             | `i18n.catalogs`; repeat it for several patterns     |
   | `--agents-md` | off              | the AGENTS.md line, added once                      |

3. **Create the catalogs**, one per locale, with the same keys and placeholders. Write each new
   string in the `source` catalog first. [`examples/web-app`](examples/web-app) has a complete set
   in `es`, `en` and `pt-BR`, with placeholders and an ICU plural.
4. **Inject and teach.** Give every session the output of `show`, and install the skill, as the
   [integrations](#-integrations) show.
5. **Validate.** Run `check --recursive` in pre-commit and CI. It checks the policy and every
   catalog.

### 🧰 Resolver CLI

With the policy shown at the top of this README:

```bash
python3 src/ai18n.py resolve .claude/skills/x/SKILL.md   # instruct en
python3 src/ai18n.py resolve src/locales/pt-BR.json      # ui pt-BR
python3 src/ai18n.py resolve --surface respond --json    # {"surface": "respond", "language": "es"}
python3 src/ai18n.py check                               # validate the policies that apply here
python3 src/ai18n.py check --recursive                   # validate every policy in the repository
python3 src/ai18n.py show                                # normalized policy as text, ready to inject
python3 src/ai18n.py show --format json                  # the same policy as JSON
python3 src/ai18n.py init --locales es,en,pt-BR          # write the first policy of a project
python3 src/ai18n.py --version                           # resolver and spec versions
```

- `resolve` prints the surface and the language of a file, or `unset` when no policy applies. A
  message catalog is `ui` text in its own locale.
- `check` exits with 1 when a policy file is invalid, two policy files in one directory differ, or
  a message catalog is out of step with its source. With `--recursive` it also checks every policy
  under the root, and skips nested repositories.
- `check` reports missing or extra catalogs and keys, empty messages, repeated keys and
  placeholders that differ from the source. It validates JSON, ARB and YAML catalogs, and notes
  without failing the formats it does not validate, such as `.po`.
- `show` renders the values of the policy with fixed wording, so no comment of the file reaches a
  model.
- `init` writes the first `ai18n.yaml` of a project, as [Start a new project](#-start-a-new-project)
  shows.

### 🚦 Exit codes

| Code | Meaning                                                                                                            |
| ---- | ------------------------------------------------------------------------------------------------------------------ |
| `0`  | Success: the file resolved, the policies and catalogs are valid, the policy was rendered or written.               |
| `1`  | A policy file, a message catalog, a directory or the schema is invalid or cannot be read, or `init` did not write. |
| `2`  | Usage error, such as a missing argument or a `--root` that does not exist.                                         |

### 🧾 JSON rendering

`show --format json` gives engines the normalized policy as data. For the policy at the top of
this README it prints:

```json
{
  "ai18n": 1,
  "policy": true,
  "spec": "https://github.com/JuanVilla424/ai18n/blob/main/SPEC.md",
  "surfaces": {
    "respond": "es",
    "speak": "es",
    "document": "es",
    "code": "en",
    "instruct": "en"
  },
  "ui": "delegate",
  "default": "es",
  "paths": [
    { "match": ["**/SKILL.md", "**/skills/**"], "surface": "instruct" }
  ],
  "i18n": {
    "source": "es",
    "locales": ["es", "en", "pt-BR"],
    "fallback": "en",
    "catalogs": ["src/locales/{locale}.json"]
  },
  "content_rule": {
    "document": [".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc"],
    "code_txt": [
      "CMakeLists.txt",
      "robots.txt",
      "requirements*.txt",
      "constraints*.txt"
    ],
    "code": "any other file"
  },
  "resolve": "python3 src/ai18n.py resolve <path>"
}
```

| Field          | Meaning                                                                        |
| -------------- | ------------------------------------------------------------------------------ |
| `ai18n`        | The spec version of the rendering.                                             |
| `policy`       | `false` when no policy applies; then `ai18n` and `policy` are the only fields. |
| `surfaces`     | The effective language of every surface that resolves to one.                  |
| `ui`           | A language tag, or `delegate`.                                                 |
| `default`      | The nearest `default`, or `null`.                                              |
| `paths`        | The path rules, in the order they are tried.                                   |
| `i18n`         | The nearest `i18n` block with all four keys, or `null` when none applies.      |
| `content_rule` | The documentation suffixes, the technical `.txt` files and the rest.           |
| `resolve`      | The command that resolves one file, relative to the root.                      |

Within spec version 1 these fields keep their meaning, and new fields may be added. A consumer
should ignore fields it does not know.

### 🔌 Integrations

These snippets assume ai18n is vendored at `helpers/ai18n`, and that PyYAML and jsonschema are
installed for the Python that runs the resolver.

**Claude Code.** A `SessionStart` hook adds its output to the context of every new session. Add it
to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/helpers/ai18n/src/ai18n.py\" show --root \"$CLAUDE_PROJECT_DIR\""
          }
        ]
      }
    ]
  }
}
```

**OpenCode.** OpenCode loads `AGENTS.md` files as instructions. Have your setup script write the
output of `show` into a section of an `AGENTS.md` that OpenCode loads, and regenerate it whenever
`ai18n.yaml` changes.

**Any agent that reads `AGENTS.md`.** Add one line:

```markdown
Languages: before writing anything, resolve its language with ai18n. The policy is `ai18n.yaml`,
and `python3 helpers/ai18n/src/ai18n.py resolve <path>` prints the surface and language of a file.
```

**Agent Skills.** Copy [`skills/ai18n`](skills/ai18n/SKILL.md) to a folder your engines scan, such
as `~/.claude/skills/ai18n/`. Claude Code and OpenCode both read that folder.

**pre-commit.** Validate every policy file, and the catalogs under `src/locales/`, before each
commit:

```yaml
repos:
  - repo: local
    hooks:
      - id: ai18n-check
        name: ai18n-check
        entry: python3 helpers/ai18n/src/ai18n.py check --recursive
        language: system
        pass_filenames: false
        files: (^|/)(ai18n|languages)\.yaml$|^src/locales/
```

**CI.** Run the same check in your pipeline:

```yaml
- uses: actions/checkout@v4
  with:
    submodules: true
- run: pip install PyYAML jsonschema
- run: python3 helpers/ai18n/src/ai18n.py check --recursive
```

### ✅ Adoption checklist

1. **Declare.** Add `ai18n.yaml` at the root, or let `init` write it. A classic `languages.yaml`
   keeps working, and it can become a symbolic link to `ai18n.yaml`.
2. **Point.** Add the `AGENTS.md` line above.
3. **Inject.** Give every session the output of `show`, never the raw file.
4. **Teach.** Install the `ai18n` skill where your engines load skills.
5. **Verify.** Run `check --recursive` in pre-commit or CI, which also checks the message catalogs,
   and have your write checks compare the language of new text with `resolve <path>`.

These steps map to the conformance levels of [SPEC.md](SPEC.md#12-conformance): declare, inject and
verify.

## ❓ FAQ

**Does ai18n translate anything?** No. It tells an AI which language to write in. Translating the
text of a product stays with that product's i18n, which is why `ui` defaults to `delegate`. The
`i18n` block tells the AI which locales the product ships and where their catalogs live, and
`check` keeps those catalogs in step with the source locale.

**How does it relate to `AGENTS.md`?** `AGENTS.md` holds prose instructions for agents. ai18n is the
data that `AGENTS.md` points to, so one line there is enough.

**Why data instead of prose?** Prose drifts, contradicts itself and can hide prompt injections. Data
has one meaning, validates against a schema and renders the same way for every engine.

**What happens without a policy?** The AI replies in the human's language and keeps each file in
the language it already uses.

**Can one folder use another language?** Yes. Add an `ai18n.yaml` there. It overrides only the
keys it declares and inherits the rest.

**Is the reference resolver required?** No. Any implementation of the resolution rules in
[SPEC.md](SPEC.md#8-resolution) conforms. The resolver is the reference, and its tests show the
expected behavior.

## 🔒 Security model

Instruction files for AI agents are a prompt-injection vector, so ai18n keeps its own file inert.
The schema only admits data, engines inject the normalized rendering instead of the raw file, and a
policy can change languages only. A file with a repeated key, or larger than 64 KiB, is refused,
and an invalid policy is rejected as a whole, never resolved in part. Message catalogs are only
read to be checked, never injected, and a catalog larger than 5 MiB is a problem.
See [SECURITY.md](SECURITY.md) to report a vulnerability.

## 🗂️ Repository layout

```text
SPEC.md                    the normative specification
schema/ai18n.schema.json   JSON Schema (draft 2020-12) of a policy file
src/ai18n.py               reference resolver and CLI
skills/ai18n/SKILL.md      portable Agent Skill with the resolution rules
examples/                  version 0, version 1, monorepo and web app examples
tests/                     tests of the resolver, the schema and the examples
ai18n.yaml                 this repository's own policy
```

## 🤝 Contributing

**Contributions are welcome! To contribute to this repository, please follow these steps**:

1. **Fork the Repository**

2. **Create a Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Commit Your Changes**

   ```bash
   git commit -m "feat(core): your feature commit message - lower case"
   ```

4. **Push to the Branch**

   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request into** `dev` **branch**

Please ensure your contributions adhere to the [Code of Conduct](CODE_OF_CONDUCT.md) and the
[Contribution Guidelines](CONTRIBUTING.md). Changes to the rules must keep `SPEC.md`, the schema,
the resolver and the skill consistent.

## 📫 Contact

For any inquiries or support, please open an issue or contact [r6ty5r296it6tl4eg5m.constant214@passinbox.com](mailto:r6ty5r296it6tl4eg5m.constant214@passinbox.com).

---

## 📜 License

2026 - This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). You are free to use, modify, and distribute this software under the terms of the Apache-2.0 license. For more details, please refer to the [LICENSE](LICENSE) file included in this repository.
