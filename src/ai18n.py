#!/usr/bin/env python3
"""ai18n.py — reference resolver of the ai18n standard: the language of every surface, for any AI.

ai18n (SPEC.md) is i18n for AI agents. One data-only file, ai18n.yaml, declares the language an AI
uses to reply, speak, document, write code and write instructions for other AIs. A languages.yaml
with the four classic keys is version 0 of the same standard and stays valid.

Discovery works like EditorConfig: from a file, every policy file up to the repository root is
collected, nearest first. For each surface the nearest file that declares it, or declares a
`default`, decides; path rules are tried from the nearest file to the farthest. Engines inject the
normalized policy that `show` prints, never the raw file, so no comment of a policy file ever
reaches a model; the schema (schema/ai18n.schema.json) only admits data.

Usage:
  ai18n.py resolve <path> [--session DIR] [--json]    surface and language of a file
  ai18n.py resolve --surface <name> [--session DIR]   language of a surface (respond, speak, ui...)
  ai18n.py check [--root DIR]                          validate the policy files that apply to DIR
  ai18n.py show [--root DIR]                           normalized policy, ready to inject
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

SPEC_VERSION = 1
SPEC_URL = "https://github.com/JuanVilla424/ai18n/blob/main/SPEC.md"
SCHEMA_FILE = Path(__file__).resolve().parents[1] / "schema" / "ai18n.schema.json"
# In each directory the first existing name is the policy: languages.yaml is version 0 or an alias.
POLICY_NAMES = ("ai18n.yaml", "languages.yaml")
SURFACES = {
    "respond": "every reply to the human",
    "speak": "talk the human reads or hears: personas, agent-to-agent messages, voice",
    "document": "documentation for humans",
    "code": "inside code: comments, docstrings, log/CLI/error messages, identifiers",
    "instruct": "text written for AIs: skills, agent prompts",
}
UI_COVERS = "user-facing UI text; delegate = each app's own i18n decides"
DELEGATE = "delegate"
DOC_SUFFIXES = {".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc"}

Chain = list[tuple[Path, dict]]


class PolicyError(Exception):
    """A policy file that is not valid ai18n: unreadable, not YAML, or rejected by the schema."""


def _validator() -> Draft202012Validator:
    """A validator for the published JSON Schema."""
    return Draft202012Validator(json.loads(SCHEMA_FILE.read_text(encoding="utf-8")))


def load_file(path: Path) -> dict:
    """One policy file, parsed and validated against the schema."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PolicyError(f"{path}: not readable as YAML ({exc})") from exc
    data = {} if data is None else data
    error = best_match(_validator().iter_errors(data))
    if error is not None:
        where = "/".join(str(part) for part in error.absolute_path) or "top level"
        raise PolicyError(f"{path}: {where}: {error.message}")
    return data


def _directories(start: Path) -> Iterator[Path]:
    """`start` and its parents up to the repository root: the first directory holding .git."""
    directory = Path(os.path.abspath(start))
    while True:
        yield directory
        if (directory / ".git").exists() or directory.parent == directory:
            return
        directory = directory.parent


def _policy_files(directory: Path) -> list[Path]:
    """The policy files present in one directory, in precedence order."""
    return [directory / name for name in POLICY_NAMES if (directory / name).is_file()]


def find_chain(start: Path) -> Chain:
    """The (directory, policy) pairs that apply to `start`, nearest first."""
    chain: Chain = []
    for directory in _directories(start):
        files = _policy_files(directory)
        if files:
            chain.append((directory, load_file(files[0])))
    return chain


def language_of(surface: str, chain: Chain) -> str | None:
    """The language of a surface: the nearest file that declares it, or declares a `default`.

    `ui` never takes a default: undeclared, it is delegated to each app's own i18n. None means
    that no policy applies."""
    for _, data in chain:
        if surface in data:
            return data[surface]
        if surface != "ui" and "default" in data:
            return data["default"]
    if surface == "ui" and chain:
        return DELEGATE
    return None


def _glob_regex(pattern: str) -> re.Pattern[str]:
    """A path glob as a regex: `**/` spans whole directories, `*` and `?` stay inside one."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def content_surface(path: Path) -> str:
    """With no path rule the content decides: documentation, or code for any other file."""
    return "document" if path.suffix.lower() in DOC_SUFFIXES else "code"


def resolve(path: str | Path, session: str | Path | None = None) -> tuple[str, str | None]:
    """(surface, language) of a file: path rules first, then the content rule.

    A file whose repository has no policy follows the policy of the session's repository."""
    target = Path(os.path.abspath(path))
    chain = find_chain(target.parent)
    if not chain and session is not None:
        chain = find_chain(Path(session))
    for directory, data in chain:
        try:
            relative = target.relative_to(directory).as_posix()
        except ValueError:
            continue
        for rule in data.get("paths", []):
            if any(_glob_regex(glob).match(relative) for glob in rule["match"]):
                if "language" in rule:
                    return content_surface(target), rule["language"]
                return rule["surface"], language_of(rule["surface"], chain)
    surface = content_surface(target)
    return surface, language_of(surface, chain)


def surface_language(surface: str, session: str | Path) -> str | None:
    """The language of a surface that has no file, such as a reply or the voice."""
    return language_of(surface, find_chain(Path(session)))


def render_policy(chain: Chain, resolver: str = "src/ai18n.py") -> str:
    """The normalized policy to inject: the values come from the files, the wording from here.

    No comment or free text of a policy file ever reaches the output."""
    if not chain:
        return (
            "# ai18n: no policy here\n\n"
            "No ai18n.yaml or languages.yaml applies: reply in the human's language and keep each "
            "file in the language it already uses.\n"
        )
    rows = [(name, language_of(name, chain), covers) for name, covers in SURFACES.items()]
    rows.append(("ui", language_of("ui", chain), UI_COVERS))
    nearest_default = next((data["default"] for _, data in chain if "default" in data), None)
    rows.append(("default", nearest_default, "any surface the nearest policy does not declare"))
    declared = [(name, value, covers) for name, value, covers in rows if value is not None]
    width = max(len(f"{name}: {value}") for name, value, _ in declared)
    lines = [
        "# ai18n: the languages of this repository",
        "",
        "The nearest ai18n.yaml decides and wins over any other file (framework config, personas,",
        f"old guidelines); languages.yaml is its version 0 or an alias. Spec: {SPEC_URL}",
        "",
        "```yaml",
        *[f"{name}: {value}".ljust(width) + f"  # {covers}" for name, value, covers in declared],
        "```",
    ]
    rules = [rule for _, data in chain for rule in data.get("paths", [])]
    if rules:
        lines += ["", "Path rules, tried in order (the first match wins over the content rule):"]
        for rule in rules:
            target = rule.get("surface") or rule["language"]
            lines.append("- " + ", ".join(rule["match"]) + " -> " + target)
    lines += [
        "",
        "Content rule: documentation files (.md, .rst, .txt...) are `document`; any other file "
        "is `code`. `preserve` keeps the language a text already has: never translate it.",
        f"Resolve one file: python3 {resolver} resolve <path>",
    ]
    return "\n".join(lines) + "\n"


def show(root: str | Path) -> str:
    """The normalized policy that applies to `root`, naming this resolver relative to it."""
    resolver = os.path.relpath(Path(__file__).resolve(), Path(os.path.abspath(root)))
    return render_policy(find_chain(Path(root)), resolver)


def check(root: str | Path) -> list[str]:
    """The problems of the policy files that apply to `root`; [] when they are all valid."""
    problems: list[str] = []
    for directory in _directories(Path(root)):
        files = _policy_files(directory)
        if len(files) == 2 and not files[0].samefile(files[1]):
            problems.append(
                f"{directory}: ai18n.yaml and languages.yaml differ; keep one, or make "
                "languages.yaml an alias of ai18n.yaml"
            )
        for policy in files:
            try:
                load_file(policy)
            except PolicyError as exc:
                problems.append(str(exc))
    return problems


def _parser() -> argparse.ArgumentParser:
    """The command line: resolve, check and show."""
    parser = argparse.ArgumentParser(
        prog="ai18n.py",
        description=f"Resolve the ai18n languages of a repository for any AI ({SPEC_URL}).",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    resolve_cmd = commands.add_parser(
        "resolve", help="surface and language of a file, or the language of a surface"
    )
    resolve_cmd.add_argument("path", nargs="?", help="the file about to be written")
    resolve_cmd.add_argument(
        "--surface", choices=[*SURFACES, "ui"], help="a surface without a file: respond, speak..."
    )
    resolve_cmd.add_argument(
        "--session",
        default=".",
        help="repository whose policy applies when the file has none (default: current directory)",
    )
    resolve_cmd.add_argument("--json", action="store_true", help="print one JSON object")
    for name, help_text in (
        ("check", "validate the policy files that apply to a directory"),
        ("show", "print the normalized policy, ready to inject"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument(
            "--root", default=".", help="directory to start from (default: current directory)"
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command line; 0 on success, 1 when a policy file is invalid."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve":
            if (args.path is None) == (args.surface is None):
                parser.error("resolve takes a path or --surface, exactly one")
            if args.surface:
                surface, language = args.surface, surface_language(args.surface, args.session)
            else:
                surface, language = resolve(args.path, args.session)
            if args.json:
                print(json.dumps({"surface": surface, "language": language}))
            else:
                print(f"{surface} {language or 'unset'}")
            return 0
        if args.command == "check":
            problems = check(args.root)
            for problem in problems:
                print(f"ai18n: {problem}", file=sys.stderr)
            if not problems:
                print("ai18n: valid")
            return 1 if problems else 0
        print(show(args.root), end="")
        return 0
    except PolicyError as exc:
        print(f"ai18n: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
