# 🤖 AGENTS.md

Instructions for AI agents working in this repository.

## 🌐 Languages

Before writing anything here, resolve its language with ai18n: the policy is `ai18n.yaml`, the rules
are in `SPEC.md`, and `python3 src/ai18n.py resolve <path>` prints the surface and the language of a
file. This repository uses English everywhere.

## ✅ Before you deliver

- Run `pytest` and `pre-commit run --all-files`; both must pass.
- Keep `src/ai18n.py`, `schema/ai18n.schema.json`, `SPEC.md` and `skills/ai18n/SKILL.md` consistent:
  a change in one of them usually needs the same change in the others.
