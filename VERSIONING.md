# 📦 Versioning Strategy

This repository carries two independent versions:

- **The spec version** is the value of the `ai18n` key in a policy file, currently `1`. It changes
  only when the meaning of an existing key changes. Additions that keep every existing policy valid
  stay in the same spec version, as [SPEC.md](SPEC.md#13-versioning) describes.
- **The repository version** covers the specification text, the schema, the reference resolver and
  the skill together. It follows [Semantic Versioning](https://semver.org/) with the format
  `MAJOR.MINOR.PATCH`, and `ai18n.py --version` prints it next to the spec version.

## 🧩 Version Components

- **MAJOR:** Increments when you make incompatible changes, such as a new spec version.
- **MINOR:** Increments when you add functionality in a backward-compatible manner.
- **PATCH:** Increments when you make backward-compatible fixes and improvements.

## 🌿 Branch Workflow

Our repository uses the following branches to manage the development and release process:

1. **dev:** Active development happens here. New features and bug fixes are merged into this branch.
2. **test:** Once features in `dev` are stable, they are promoted to `test` for further testing.
3. **prod:** After thorough testing, changes from `test` are promoted to `prod`.
4. **main:** The `main` branch holds the latest released version. Releases are tagged from this branch.

## 📝 Commit Message Guidelines

To automate versioning and changelog generation, every commit message follows a specific convention. Each commit message includes one of the following [commit types](#-commit-types), the `core` scope and a lower case description. Add one of the [versioning keywords](#-versioning-keywords) when the commit must start a release.

### 🗂️ Commit Message Structure

```bash
<type>(core): <description> [versioning keyword]
```

Example:

```bash
feat(core): accept language tags with a script and a region [minor candidate]
```

### 🔤 Commit Types

- **feat**: A new feature for the user.
- **fix**: A bug fix for the user.
- **docs**: Documentation only changes.
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc.).
- **refactor**: A code change that neither fixes a bug nor adds a feature.
- **perf**: A code change that improves performance.
- **test**: Adding missing tests or correcting existing tests.
- **chore**: Changes to the build process or auxiliary tools and libraries.

### 🔑 Versioning Keywords

**Optionally** include one of the following keywords at the end of the commit message to indicate the type of version bump:

- **[major candidate]** Indicates that this commit should trigger a MAJOR version bump.
- **[minor candidate]** Indicates that this commit should trigger a MINOR version bump.
- **[patch candidate]** Indicates that this commit should trigger a PATCH version bump.

Examples:

- `feat(core): add a json rendering of the policy [minor candidate]`
- `fix(core): reject globs that escape the policy directory [patch candidate]`
- `refactor(core): rename the instruct surface for spec version 2 [major candidate]`

## 🚀 Release Process

1. Development Phase:
   - Developers work on features and bug fixes in the `dev` branch.
   - Commit messages follow the guidelines above to indicate the type of changes.

2. Testing Phase:
   A commit with a versioning keyword bumps the version in `pyproject.toml` and `src/ai18n.py` on push.
   The Version Controller workflow then opens the pull request from `dev` to `test`.

3. Production Phase:
   Merging that pull request opens the next one, from `test` to `prod`.
   Final validation occurs here.

4. Release:
   - The pull request from `prod` to `main` is approved and merged by a maintainer.
   - A release is tagged, and the `CHANGELOG.md` is updated automatically based on commit messages.

## ⭐ Best Practices

- **Atomic Commits**: Ensure each commit represents a single logical change.
- **Descriptive Messages**: Write clear and concise commit messages that accurately describe the changes.
- **Consistent Format**: Adhere strictly to the commit message structure to enable automation tools to function correctly.
- **Avoid Force Pushes**: Respect branch protection rules to maintain repository integrity.

---

## 📜 License

2026 - This project is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0). You are free to use, modify, and distribute this software under the terms of the Apache-2.0 license. For more details, please refer to the [LICENSE](LICENSE) file included in this repository.
