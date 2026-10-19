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
  - [Resolver CLI](#-resolver-cli)
  - [Adopting ai18n in your repository](#-adopting-ai18n-in-your-repository)
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
- **Path rules:** assign a surface or a language to any glob, such as skills or vendored code.
- **`preserve`:** marks text that keeps its original language and must never be translated.
- **Cascade:** like EditorConfig, a subproject can override only the keys it needs.
- **Version 0 compatible:** a classic `languages.yaml` with four keys is already valid ai18n.
- **Data only:** a JSON Schema admits fixed keys, ISO 639-1 codes and globs, so prose cannot hide in
  a policy file.
- **Reference resolver:** a dependency-light Python CLI resolves, validates and renders a policy.
- **Agent Skill:** a portable skill teaches any skill-capable engine the resolution rules.

## 📄 The policy file

| Key        | Value                  | Covers                                                                  |
| ---------- | ---------------------- | ----------------------------------------------------------------------- |
| `ai18n`    | `1`                    | the spec version                                                        |
| `respond`  | language               | every reply to the human                                                |
| `speak`    | language               | talk the human reads or hears: personas, agent-to-agent messages, voice |
| `document` | language               | documentation for humans                                                |
| `code`     | language               | inside code: comments, docstrings, log/CLI/error messages, identifiers  |
| `instruct` | language               | text written for AIs: skills, agent prompts                             |
| `ui`       | language or `delegate` | user-facing UI text; `delegate` leaves it to each app's i18n            |
| `default`  | language               | any surface the same file does not declare                              |
| `paths`    | rules                  | globs mapped to a `surface`, or to a `language` such as `preserve`      |

A language is an ISO 639-1 code: two lowercase letters. The normative rules live in
[SPEC.md](SPEC.md), and the schema in [schema/ai18n.schema.json](schema/ai18n.schema.json).

## 🧭 How an AI resolves a language

1. Walk up from the file to the repository root and collect every `ai18n.yaml`, nearest first.
2. The first matching path rule wins.
3. Otherwise documentation files are `document`, and any other file is `code`.
4. For that surface, the nearest policy that declares it, or declares a `default`, decides.
5. Without a policy of its own, a file follows the policy of the repository the AI works from.

The policy wins over any other instruction about languages, and it changes languages only.

## 🚀 Getting Started

### 📋 Prerequisites

**Before you begin, ensure you have met the following requirements**:

- **Python 3.12+:** to run the reference resolver and the tests.
- **Git:** Install [Git](https://git-scm.com/) to clone the repository.
- **Node.js 22.x+:** (Optional) (Required to Push) Used by the prettier pre-commit hook.

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

### 🧰 Resolver CLI

With the policy shown at the top of this README:

```bash
python3 src/ai18n.py resolve .claude/skills/x/SKILL.md     # -> instruct en
python3 src/ai18n.py resolve --surface respond --json      # -> {"surface": "respond", "language": "es"}
python3 src/ai18n.py check                                 # validate the policies that apply here
python3 src/ai18n.py show                                  # normalized policy, ready to inject
```

`resolve` prints the surface and the language of a file, or `unset` when no policy applies.
`check` exits with 1 when a policy file is invalid or two policy files in one directory differ.
`show` renders the values of the policy with fixed wording, so no comment of the file reaches a
model.

### 🧩 Adopting ai18n in your repository

1. **Declare.** Add `ai18n.yaml` at the root. A classic `languages.yaml` keeps working, and it can
   become a symbolic link to `ai18n.yaml`.
2. **Point.** Add one line to your `AGENTS.md`, such as: "Before writing anything, resolve its
   language with ai18n: the policy is `ai18n.yaml`."
3. **Inject.** At session start, give the agent the output of `ai18n.py show`, never the raw file.
   In Claude Code this is a `SessionStart` hook. In OpenCode it is a section of the generated
   `AGENTS.md`.
4. **Teach.** Install [`skills/ai18n`](skills/ai18n/SKILL.md) where your engines load Agent Skills,
   such as `~/.claude/skills/ai18n/`.
5. **Verify.** Have your write checks call `ai18n.py resolve <path>` and compare the language of
   the new text with the resolved one.

These steps map to the conformance levels of [SPEC.md](SPEC.md#10-conformance): declare, inject and
verify.

## 🔒 Security model

Instruction files for AI agents are a prompt-injection vector, so ai18n keeps its own file inert.
The schema only admits data, engines inject the normalized rendering instead of the raw file, and a
policy can change languages only. An invalid policy is rejected as a whole, never resolved in part.
See [SECURITY.md](SECURITY.md) to report a vulnerability.

## 🗂️ Repository layout

```text
SPEC.md                    the normative specification
schema/ai18n.schema.json   JSON Schema (draft 2020-12) of a policy file
src/ai18n.py               reference resolver and CLI
skills/ai18n/SKILL.md      portable Agent Skill with the resolution rules
examples/                  version 0, version 1 and monorepo policies
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
   git commit -m "feat(<scope>): your feature commit message - lower case"
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
