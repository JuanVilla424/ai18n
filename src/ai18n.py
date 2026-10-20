#!/usr/bin/env python3
"""ai18n.py — reference resolver of the ai18n standard: the language of every surface, for any AI.

ai18n (SPEC.md) is i18n for AI agents. One data-only file, ai18n.yaml, declares the language an AI
uses to reply, speak, document, write code and write instructions for other AIs, and the locales
the product ships to its users, with the message catalogs that hold their text. A languages.yaml
with the four classic keys is version 0 of the same standard and stays valid.

Discovery works like EditorConfig: from a file, every policy file up to the repository root is
collected, nearest first. For each surface the nearest file that declares it, or declares a
`default`, decides; path rules are tried from the nearest file to the farthest, then the message
catalogs of the nearest `i18n` block. Engines inject the normalized policy that `show` prints,
never the raw file, so no comment of a policy file ever reaches a model; the schema
(schema/ai18n.schema.json) only admits data, and a file with a repeated key or more than
MAX_POLICY_BYTES is rejected before anything resolves from it.

Usage:
  ai18n.py resolve <path> [--session DIR] [--json]    surface and language of a file
  ai18n.py resolve --surface <name> [--session DIR]   language of a surface (respond, speak, ui...)
  ai18n.py check [--root DIR] [--recursive]            validate the policies and their catalogs
  ai18n.py show [--root DIR] [--format text|json]      normalized policy, ready to inject
  ai18n.py init [--root DIR] [--locales TAGS] ...      write the first ai18n.yaml of a project
  ai18n.py --version
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple, cast

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

__version__ = "1.0.7"
SPEC_VERSION = 1
SPEC_URL = "https://github.com/JuanVilla424/ai18n/blob/main/SPEC.md"
SCHEMA_FILE = Path(__file__).resolve().parents[1] / "schema" / "ai18n.schema.json"
# In each directory the first existing name is the policy: languages.yaml is version 0 or an alias.
POLICY_NAMES = ("ai18n.yaml", "languages.yaml")
# A policy is a few lines of data: a bigger file is refused before it is parsed, so a hostile
# repository cannot slow down every session that reads it.
MAX_POLICY_BYTES = 64 * 1024
SURFACES = {
    "respond": "every reply to the human",
    "speak": "talk the human reads or hears: personas, agent-to-agent messages, voice",
    "document": "documentation for humans",
    "code": "inside code: comments, docstrings, log/CLI/error messages, identifiers",
    "instruct": "text written for AIs: skills, agent prompts",
}
UI_COVERS = "user-facing UI text; delegate = each app's own i18n decides"
DEFAULT_COVERS = "any surface the nearest policy does not declare"
DELEGATE = "delegate"
DOC_SUFFIXES = (".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc")
# Well-known .txt files that hold build code or configuration, not prose: they are code.
TECHNICAL_TXT_NAMES = ("CMakeLists.txt", "robots.txt")
TECHNICAL_TXT_PREFIXES = ("requirements", "constraints")
# Folders a recursive check never enters: tooling, caches and build output, never policies.
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".tox", "build", "dist"}
NO_POLICY = (
    "# ai18n: no policy here\n\n"
    "No ai18n.yaml or languages.yaml applies: reply in the human's language and keep each "
    "file in the language it already uses.\n"
)
# The line that points agents that read AGENTS.md at the policy; init prints it or adds it.
AGENTS_LINE = (
    "Languages: before writing anything, resolve its language with ai18n. The policy is "
    "`ai18n.yaml`, and `python3 {resolver} resolve <path>` prints the surface and language of a "
    "file."
)
NEVER_OVERWRITE = "a policy already exists; init never overwrites one, so edit it instead"

LOCALE_TOKEN = "{locale}"
# What the {locale} token of a catalog pattern matches: a run shaped like a language tag, with
# `-` or `_` between its parts and in any case, so pt-BR, pt_BR and pt-br all reach the same check.
LOCALE_RUN = r"[A-Za-z]{2,3}(?:[-_][A-Za-z]{4})?(?:[-_](?:[A-Za-z]{2}|[0-9]{3}))?"
# The catalog formats whose messages a check validates; any other format is only resolved.
VALIDATED_FORMATS = {".json": "JSON", ".arb": "JSON", ".yaml": "YAML", ".yml": "YAML"}
# A catalog is product text, so it may be far bigger than a policy, but it stays bounded: a
# hostile repository cannot make a check slow or exhaust its memory, not even with YAML aliases.
MAX_CATALOG_BYTES = 5 * 1024 * 1024
MAX_CATALOG_DEPTH = 32
MAX_CATALOG_ENTRIES = 100_000
# Plural forms count as one key, because every language has its own forms: the i18next suffixes
# (item_one, item_other) and a mapping whose keys are all plural categories, as Rails writes them.
PLURAL_CATEGORIES = frozenset({"zero", "one", "two", "few", "many", "other"})
PLURAL_SUFFIX = re.compile(r"_(?:ordinal_)?(?:zero|one|two|few|many|other)\Z")
# printf placeholders: %(name)s by name, %s and %d by position. A literal percent is written %%.
PRINTF = re.compile(r"%(?:\((?P<name>\w+)\))?[-+#0]*\d*(?:\.\d+)?[sdifuxXeEgGr]")
BRACE_TOKEN = re.compile(r"[{},]")
# ICU MessageFormat writes a literal brace as '{' or '}'.
ICU_QUOTED_BRACE = re.compile(r"'[{}]'")
ARGUMENT_NAME = re.compile(r"(?:[^\W\d][\w.]*|\d+)")

Policy = dict[str, Any]
Chain = list[tuple[Path, Policy]]
# The messages of one catalog: each key, with the plural forms it groups and their values.
Messages = dict[str, dict[str, object]]


class PolicyError(Exception):
    """A policy file that is not valid ai18n: unreadable, not YAML, or rejected by the schema."""


class CatalogError(Exception):
    """A message catalog that cannot be checked: unreadable, malformed, or beyond the limits."""


class CatalogMatch(NamedTuple):
    """A path that a catalog pattern matches."""

    locale: str | None  # the declared locale, or None when the path names an undeclared one
    run: str  # what the {locale} token matched, as the path writes it
    namespace: str  # the path with that run written as {locale}: the same file in every locale


# NamedTuple, not dataclasses: hooks load this file with importlib without registering it in
# sys.modules, and a dataclass needs its module there to read its annotations.
class InitOptions(NamedTuple):
    """The values of a first policy: the language people read, the languages of code and of
    text for AIs, and the locales the product ships."""

    language: str = "en"
    code: str = "en"
    instruct: str = "en"
    locales: tuple[str, ...] = ()
    source: str | None = None
    fallback: str | None = None
    catalogs: tuple[str, ...] = ()


class _BraceGroup(NamedTuple):
    """An open brace group of a message: an argument such as {name}, or a sub-message such as a
    branch of an ICU plural or select."""

    argument: bool
    start: int
    name_end: int | None = None  # where an argument's name stops: at a comma or a nested group


@functools.cache
def _validator() -> Draft202012Validator:
    """A validator for the published JSON Schema, loaded once per process."""
    try:
        schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PolicyError(
            f"cannot load the ai18n schema {SCHEMA_FILE} ({exc}); restore it from the ai18n "
            "repository"
        ) from exc
    return Draft202012Validator(schema)


def _read_policy_text(path: Path) -> str:
    """The text of a policy file, refused when it is too big to be a policy."""
    size = path.stat().st_size
    if size > MAX_POLICY_BYTES:
        raise PolicyError(
            f"{path}: {size} bytes, more than the {MAX_POLICY_BYTES} a policy file may have"
        )
    return path.read_text(encoding="utf-8")


def _reject_duplicate_keys(
    node: yaml.Node | None, path: Path, seen: set[int] | None = None
) -> None:
    """Refuse a mapping that repeats a key: YAML would silently keep the last value.

    `seen` holds the nodes already visited, because YAML aliases can make the node graph cyclic."""
    seen = set() if seen is None else seen
    if node is None or id(node) in seen:
        return
    seen.add(id(node))
    if isinstance(node, yaml.MappingNode):
        keys: set[str] = set()
        for key_node, value_node in node.value:
            if isinstance(key_node, yaml.ScalarNode):
                if key_node.value in keys:
                    line = key_node.start_mark.line + 1
                    raise PolicyError(f"{path}: line {line}: duplicate key {key_node.value!r}")
                keys.add(key_node.value)
            _reject_duplicate_keys(value_node, path, seen)
    elif isinstance(node, yaml.SequenceNode):
        for item in node.value:
            _reject_duplicate_keys(item, path, seen)


def _check_i18n(policy: Policy, path: Path) -> None:
    """Refuse an i18n block whose source or fallback is not one of its locales."""
    block = policy.get("i18n")
    if block is None:
        return
    for key in ("source", "fallback"):
        if key in block and block[key] not in block["locales"]:
            raise PolicyError(
                f"{path}: i18n/{key}: {block[key]!r} is not one of the locales "
                f"{', '.join(block['locales'])}; add it to i18n.locales or choose one of them"
            )


def _parse_policy(text: str, path: Path) -> Policy:
    """A policy from its text: YAML without repeated keys, valid against the schema, and with an
    i18n block whose source and fallback are among its locales."""
    try:
        _reject_duplicate_keys(yaml.compose(text, Loader=yaml.SafeLoader), path)
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolicyError(f"{path}: not readable as UTF-8 YAML ({exc})") from exc
    data = {} if data is None else data
    error = best_match(_validator().iter_errors(data))
    if error is not None:
        where = "/".join(str(part) for part in error.absolute_path) or "top level"
        raise PolicyError(f"{path}: {where}: {error.message}")
    policy = cast(Policy, data)
    _check_i18n(policy, path)
    return policy


def load_file(path: Path) -> Policy:
    """One policy file, parsed and validated against the schema."""
    try:
        text = _read_policy_text(path)
    except (OSError, UnicodeDecodeError) as exc:
        raise PolicyError(f"{path}: not readable as UTF-8 YAML ({exc})") from exc
    return _parse_policy(text, path)


def _directories(start: Path) -> Iterator[Path]:
    """`start` and its parents up to the repository root: the first directory holding .git."""
    directory = Path(os.path.abspath(start))
    while True:
        yield directory
        try:
            at_root = (directory / ".git").exists() or directory.parent == directory
        except OSError as exc:
            raise PolicyError(_unreadable(exc)) from exc
        if at_root:
            return
        directory = directory.parent


def _unreadable(error: OSError) -> str:
    """The problem line for a directory a recursive check cannot read."""
    return f"{error.filename}: cannot read it ({error.strerror}); fix its permissions or move it"


def _walk(root: Path, problems: list[str]) -> Iterator[tuple[Path, list[str], list[str]]]:
    """os.walk from `root` in sorted order, without tooling folders or nested repositories.

    As with os.walk, the caller may prune the directory names it gets. A directory that cannot be
    read is added to `problems` instead of being skipped in silence."""

    def report(error: OSError) -> None:
        problems.append(_unreadable(error))

    for current, dirnames, filenames in os.walk(os.path.abspath(root), onerror=report):
        here = Path(current)
        kept: list[str] = []
        for name in sorted(dirnames):
            if name in SKIP_DIRS:
                continue
            try:
                nested_repository = (here / name / ".git").exists()
            except OSError as exc:
                report(exc)
                continue
            if not nested_repository:
                kept.append(name)
        dirnames[:] = kept
        yield here, dirnames, sorted(filenames)


def _directories_below(root: Path, problems: list[str]) -> Iterator[Path]:
    """`root` and every directory under it, except tooling folders and nested repositories.

    A directory that cannot be read is added to `problems` instead of being skipped in silence."""
    for here, _, _ in _walk(root, problems):
        yield here


def _policy_files(directory: Path) -> list[Path]:
    """The policy files present in one directory, in precedence order."""
    try:
        return [directory / name for name in POLICY_NAMES if (directory / name).is_file()]
    except OSError as exc:
        raise PolicyError(_unreadable(exc)) from exc


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
            value: str = data[surface]
            return value
        if surface != "ui" and "default" in data:
            fallback: str = data["default"]
            return fallback
    if surface == "ui" and chain:
        return DELEGATE
    return None


def product_locales(chain: Chain) -> tuple[Path, dict[str, Any]] | None:
    """The i18n block of the nearest policy that declares one, with that policy's directory.

    The nearest block decides as a whole: its keys never mix with those of a farther block."""
    for directory, data in chain:
        if "i18n" in data:
            block: dict[str, Any] = data["i18n"]
            return directory, block
    return None


def _glob_regex(pattern: str) -> re.Pattern[str]:
    """A path glob as a regex: `**/` spans whole directories, `*` and `?` stay inside one, and the
    {locale} token of a catalog pattern captures a run shaped like a language tag as `locale`."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern.startswith(LOCALE_TOKEN, i):
            out.append(f"(?P<locale>{LOCALE_RUN})")
            i += len(LOCALE_TOKEN)
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


def _locale_key(text: str) -> str:
    """A locale as a path may write it, made comparable: pt-BR, pt_BR and pt-br are equal."""
    return text.replace("_", "-").lower()


def _catalog_match(
    relative: str, patterns: list[re.Pattern[str]], locales: list[str]
) -> CatalogMatch | None:
    """How the catalog patterns match a relative path: the first match that names a declared
    locale, else the first one that names an undeclared locale, else None."""
    undeclared: CatalogMatch | None = None
    for pattern in patterns:
        found = pattern.match(relative)
        if found is None:
            continue
        run = found.group("locale")
        namespace = (
            relative[: found.start("locale")] + LOCALE_TOKEN + relative[found.end("locale") :]
        )
        locale = next((tag for tag in locales if _locale_key(tag) == _locale_key(run)), None)
        if locale is not None:
            return CatalogMatch(locale, run, namespace)
        undeclared = undeclared or CatalogMatch(None, run, namespace)
    return undeclared


def catalog_locale(target: Path, chain: Chain) -> str | None:
    """The locale of a message catalog of the nearest i18n block, or None for any other file."""
    product = product_locales(chain)
    if product is None:
        return None
    directory, block = product
    try:
        relative = target.relative_to(directory).as_posix()
    except ValueError:
        return None
    patterns = [_glob_regex(pattern) for pattern in block.get("catalogs", [])]
    match = _catalog_match(relative, patterns, block["locales"])
    return None if match is None else match.locale


def content_surface(path: Path) -> str:
    """With no path rule the content decides: documentation, or code for any other file.

    A few well-known .txt files hold build code or configuration, not prose: they are code."""
    suffix = path.suffix.lower()
    if suffix == ".txt" and (
        path.name in TECHNICAL_TXT_NAMES or path.name.lower().startswith(TECHNICAL_TXT_PREFIXES)
    ):
        return "code"
    return "document" if suffix in DOC_SUFFIXES else "code"


def resolve(path: str | Path, session: str | Path | None = None) -> tuple[str, str | None]:
    """(surface, language) of a file: path rules first, then the message catalogs, then the
    content rule.

    A message catalog is `ui` text in its own locale. A file whose repository has no policy
    follows the policy of the session's repository."""
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
    locale = catalog_locale(target, chain)
    if locale is not None:
        return "ui", locale
    surface = content_surface(target)
    return surface, language_of(surface, chain)


def surface_language(surface: str, session: str | Path) -> str | None:
    """The language of a surface that has no file, such as a reply or the voice."""
    return language_of(surface, find_chain(Path(session)))


def _resolver_path(root: str | Path) -> str:
    """This resolver's path relative to `root`, the way a command run from there names it."""
    return os.path.relpath(Path(__file__).resolve(), Path(os.path.abspath(root)))


def normalized(chain: Chain, resolver: str = "src/ai18n.py") -> dict[str, Any]:
    """The normalized policy as data: effective values only, never a comment of a policy file."""
    if not chain:
        return {"ai18n": SPEC_VERSION, "policy": False}
    surfaces = {name: language_of(name, chain) for name in SURFACES}
    technical_txt = [*TECHNICAL_TXT_NAMES, *(f"{prefix}*.txt" for prefix in TECHNICAL_TXT_PREFIXES)]
    product = product_locales(chain)
    return {
        "ai18n": SPEC_VERSION,
        "policy": True,
        "spec": SPEC_URL,
        "surfaces": {name: value for name, value in surfaces.items() if value is not None},
        "ui": language_of("ui", chain),
        "default": next((data["default"] for _, data in chain if "default" in data), None),
        "paths": [dict(rule) for _, data in chain for rule in data.get("paths", [])],
        "i18n": None if product is None else _product_view(product[1]),
        "content_rule": {
            "document": list(DOC_SUFFIXES),
            "code_txt": technical_txt,
            "code": "any other file",
        },
        "resolve": f"python3 {resolver} resolve <path>",
    }


def _product_view(block: dict[str, Any]) -> dict[str, Any]:
    """An i18n block with every key present, as the normalized policy carries it."""
    return {
        "source": block["source"],
        "locales": list(block["locales"]),
        "fallback": block.get("fallback"),
        "catalogs": list(block.get("catalogs", [])),
    }


def _product_lines(product: dict[str, Any]) -> list[str]:
    """The text rendering of the product locales: what the product ships, and where its text
    lives."""
    fallback = f"; a missing key falls back to {product['fallback']}" if product["fallback"] else ""
    lines = [
        "",
        f"Product locales (i18n): the product ships {', '.join(product['locales'])}. New "
        f"user-facing text is written first in {product['source']}, then in every other "
        f"locale{fallback}.",
        "User-facing text never lives in code: each string is a key of the message catalogs, "
        "with the same keys and placeholders in every locale.",
    ]
    if product["catalogs"]:
        globs = ", ".join(f"`{glob}`" for glob in product["catalogs"])
        lines.append(
            f"Message catalogs, tried after the path rules: {globs}. Each one is `ui` text in "
            "its own locale."
        )
    return lines


def render_policy(chain: Chain, resolver: str = "src/ai18n.py") -> str:
    """The normalized policy as text to inject: values from the files, wording from here.

    No comment or free text of a policy file ever reaches the output, and every glob is quoted
    as code so Markdown never reads its `*` as emphasis."""
    data = normalized(chain, resolver)
    if not data["policy"]:
        return NO_POLICY
    rows = [(name, value, SURFACES[name]) for name, value in data["surfaces"].items()]
    rows.append(("ui", data["ui"], UI_COVERS))
    if data["default"] is not None:
        rows.append(("default", data["default"], DEFAULT_COVERS))
    width = max(len(f"{name}: {value}") for name, value, _ in rows)
    lines = [
        "# ai18n: the languages of this repository",
        "",
        "The nearest ai18n.yaml decides and wins over any other file (framework config, personas,",
        f"old guidelines); languages.yaml is its version 0 or an alias. Spec: {SPEC_URL}",
        "",
        "```yaml",
        *[f"{name}: {value}".ljust(width) + f"  # {covers}" for name, value, covers in rows],
        "```",
    ]
    if data["paths"]:
        lines += ["", "Path rules, tried in order (the first match wins over the content rule):"]
        for rule in data["paths"]:
            target = rule.get("surface") or rule["language"]
            globs = ", ".join(f"`{glob}`" for glob in rule["match"])
            lines.append(f"- {globs} -> {target}")
    if data["i18n"] is not None:
        lines += _product_lines(data["i18n"])
    technical = ", ".join(data["content_rule"]["code_txt"])
    lines += [
        "",
        "Content rule: documentation files (.md, .rst, .txt...) are `document`; technical .txt "
        f"files ({technical}) and any other file are `code`. `preserve` keeps the language a "
        "text already has: never translate it.",
        "Resolve one file: " + data["resolve"],
    ]
    return "\n".join(lines) + "\n"


def show(root: str | Path, fmt: str = "text") -> str:
    """The normalized policy that applies to `root`, as text or JSON, naming this resolver."""
    resolver = _resolver_path(root)
    chain = find_chain(Path(root))
    if fmt == "json":
        return json.dumps(normalized(chain, resolver), indent=2) + "\n"
    return render_policy(chain, resolver)


def _catalog_start(directory: Path, pattern: str) -> Path | None:
    """The deepest directory a catalog pattern names before its first wildcard or {locale}, or
    None when the pattern leads outside the policy's directory, where it can match nothing."""
    fixed: list[str] = []
    for segment in pattern.split("/")[:-1]:
        if "*" in segment or "?" in segment or LOCALE_TOKEN in segment:
            break
        fixed.append(segment)
    start = Path(os.path.normpath(directory.joinpath(*fixed)))
    return start if start == directory or directory in start.parents else None


def _declares_i18n(directory: Path) -> bool:
    """Whether the policy of a directory declares its own i18n block. A policy that cannot be
    read counts as one, so no file is checked against a block that may not govern it."""
    try:
        files = _policy_files(directory)
        return bool(files) and "i18n" in load_file(files[0])
    except PolicyError:
        return True


def _governed_files(directory: Path, start: Path, problems: list[str]) -> Iterator[Path]:
    """The files under `start` whose nearest i18n block is the one of `directory`: a subtree whose
    policy declares its own i18n block belongs to that block, as it does when a file resolves."""
    if not os.path.isdir(start):
        return
    here = start
    while here != directory:
        if _declares_i18n(here):
            return
        here = here.parent
    for current, dirnames, filenames in _walk(start, problems):
        dirnames[:] = [name for name in dirnames if not _declares_i18n(current / name)]
        for name in filenames:
            yield current / name


def _find_catalogs(
    directory: Path, block: dict[str, Any], problems: list[str]
) -> dict[str, dict[str, Path]]:
    """The catalogs an i18n block governs, by namespace and locale. A file whose path names a
    locale the block does not declare, or a second catalog of one locale, is a problem."""
    patterns = [_glob_regex(pattern) for pattern in block["catalogs"]]
    starts = {_catalog_start(directory, pattern) for pattern in block["catalogs"]}
    found: dict[str, dict[str, Path]] = {}
    seen: set[Path] = set()
    for start in sorted(candidate for candidate in starts if candidate is not None):
        for path in _governed_files(directory, start, problems):
            if path in seen:  # two patterns may start their walks in nested folders
                continue
            seen.add(path)
            relative = path.relative_to(directory).as_posix()
            match = _catalog_match(relative, patterns, block["locales"])
            if match is None:
                continue
            if match.locale is None:
                problems.append(
                    f"{path}: a catalog of {match.run}, a locale i18n.locales does not declare; "
                    "declare it, or move the file out of i18n.catalogs"
                )
                continue
            by_locale = found.setdefault(match.namespace, {})
            if match.locale in by_locale:
                problems.append(
                    f"{path}: a second catalog of {match.locale}, after {by_locale[match.locale]}; "
                    "keep one"
                )
            else:
                by_locale[match.locale] = path
    return found


def _unique_pairs(path: Path, pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """A JSON object, refused when it repeats a key: json would silently keep the last value."""
    mapping: dict[str, Any] = {}
    for key, value in pairs:
        if key in mapping:
            raise CatalogError(f"{path}: duplicate key {key!r}")
        mapping[key] = value
    return mapping


def _parse_catalog(text: str, kind: str, path: Path) -> object:
    """The data of a JSON or YAML catalog, refusing a key repeated inside one mapping."""
    if kind == "YAML":
        _reject_duplicate_keys(yaml.compose(text, Loader=yaml.SafeLoader), path)
        return yaml.safe_load(text)
    return json.loads(text, object_pairs_hook=functools.partial(_unique_pairs, path))


def _catalog_root(data: object, path: Path, locale: str) -> dict[str, Any]:
    """The mapping that holds a catalog's messages: ARB metadata (keys starting with @) left out,
    and a single root key that names the catalog's own locale, as Rails writes it, unwrapped."""
    data = {} if data is None else data
    if not isinstance(data, dict):
        raise CatalogError(f"{path}: a catalog must be a mapping of keys to messages")
    if path.suffix.lower() == ".arb":
        data = {key: value for key, value in data.items() if not str(key).startswith("@")}
    if len(data) == 1:
        ((key, value),) = data.items()
        if isinstance(value, dict) and _locale_key(str(key)) == _locale_key(locale):
            data = value
    return cast(dict[str, Any], data)


def _is_plural_mapping(value: dict[Any, Any]) -> bool:
    """Whether a mapping holds the plural forms of one message: plural categories only."""
    return "other" in value and all(str(key) in PLURAL_CATEGORIES for key in value)


def _add_message(messages: Messages, keys: tuple[str, str], value: object, path: Path) -> None:
    """Add one message, or one plural form of it, refusing a key the catalog already has."""
    base, key = keys
    forms = messages.setdefault(base, {})
    if key in forms:
        raise CatalogError(f"{path}: duplicate key {key!r}, written both nested and with dots")
    forms[key] = value


def _messages(data: dict[str, Any], path: Path) -> Messages:
    """The messages of a catalog by key: nested keys joined with `.`, and the plural forms of one
    message grouped under one key, within the limits of depth and entries."""
    messages: Messages = {}
    pending: list[tuple[str, object, int]] = [("", data, 0)]
    entries = 0
    while pending:
        key, value, depth = pending.pop()
        entries += 1
        if entries > MAX_CATALOG_ENTRIES:
            raise CatalogError(
                f"{path}: more than {MAX_CATALOG_ENTRIES} entries; split it into namespaces"
            )
        if key and isinstance(value, dict) and _is_plural_mapping(value):
            for form, text in value.items():
                _add_message(messages, (key, f"{key}.{form}"), text, path)
        elif isinstance(value, dict | list):
            if depth == MAX_CATALOG_DEPTH:
                raise CatalogError(f"{path}: nested more than {MAX_CATALOG_DEPTH} levels deep")
            children = value.items() if isinstance(value, dict) else enumerate(value)
            pending.extend(
                (f"{key}.{name}" if key else str(name), child, depth + 1)
                for name, child in children
            )
        else:
            _add_message(messages, (PLURAL_SUFFIX.sub("", key) or key, key), value, path)
    return messages


def _load_catalog(path: Path, locale: str) -> Messages:
    """The messages of one JSON, ARB or YAML catalog, refused when it is too big, cannot be
    parsed, repeats a key or is not a mapping."""
    kind = VALIDATED_FORMATS[path.suffix.lower()]
    try:
        size = path.stat().st_size
        text = None if size > MAX_CATALOG_BYTES else path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise CatalogError(f"{path}: not readable as UTF-8 ({exc})") from exc
    if text is None:
        raise CatalogError(
            f"{path}: {size} bytes, more than the {MAX_CATALOG_BYTES} a catalog may have; split "
            "it into namespaces"
        )
    try:
        data = _parse_catalog(text, kind, path)
    except (ValueError, yaml.YAMLError) as exc:
        raise CatalogError(f"{path}: not valid {kind} ({exc})") from exc
    except RecursionError as exc:
        raise CatalogError(f"{path}: nested too deeply to be read") from exc
    except PolicyError as exc:  # a repeated YAML key, named with its line
        raise CatalogError(str(exc)) from exc
    return _messages(_catalog_root(data, path, locale), path)


def _brace_arguments(text: str) -> set[str] | None:
    """The argument names of a message's brace groups, or None when its braces do not balance.

    It reads ICU MessageFormat ({name}, {0}, {n, number} and the arguments inside the branches of
    plural and select), i18next ({{name}}, {{- name}}, {{name, format}}) and Rails (%{name}). The
    text of a branch, such as {item} in `one {item}`, is a sub-message, never an argument."""
    names: set[str] = set()
    groups: list[_BraceGroup] = []
    for token in BRACE_TOKEN.finditer(text):
        char, index = token.group(), token.start()
        top = groups[-1] if groups else None
        if char == "{":
            if top is None or not top.argument:
                groups.append(_BraceGroup(True, index + 1))
            elif top.name_end is None and not text[top.start : index].strip():
                # the outer braces of {{name}} only wrap the argument
                groups[-1] = top._replace(argument=False)
                groups.append(_BraceGroup(True, index + 1))
            else:
                if top.name_end is None:
                    groups[-1] = top._replace(name_end=index)
                groups.append(_BraceGroup(False, index + 1))
        elif char == "}":
            if top is None:
                return None
            groups.pop()
            if top.argument:
                end = index if top.name_end is None else top.name_end
                name = text[top.start : end].strip().removeprefix("-").strip()
                if ARGUMENT_NAME.fullmatch(name):
                    names.add(name)
        elif top is not None and top.argument and top.name_end is None:
            groups[-1] = top._replace(name_end=index)
    return None if groups else names


def _placeholders(message: str) -> Counter[str] | None:
    """The placeholders of a message: named ones once, positional printf ones as often as they
    appear. None when the braces of the message do not balance."""
    text = message.replace("%%", "")
    found: Counter[str] = Counter()
    for match in PRINTF.finditer(text):
        found[match.group()] = 1 if match.group("name") else found[match.group()] + 1
    names = _brace_arguments(ICU_QUOTED_BRACE.sub("", text))
    if names is None:
        return None
    for name in names:
        found[f"{{{name}}}"] = 1
    return found


def _signature(forms: dict[str, object]) -> Counter[str] | None:
    """The placeholders of a message across its plural forms; None when a form does not balance
    its braces, which is reported on its own."""
    signature: Counter[str] = Counter()
    for value in forms.values():
        if isinstance(value, str):
            found = _placeholders(value)
            if found is None:
                return None
            signature |= found
    return signature


def _describe(signature: Counter[str]) -> str:
    """Placeholders as a problem line names them."""
    return ", ".join(sorted(signature.elements())) or "none"


def _check_messages(path: Path, messages: Messages, problems: list[str]) -> None:
    """Report the messages of one catalog that are empty, or whose braces do not balance."""
    texts = {
        key: value
        for forms in messages.values()
        for key, value in forms.items()
        if isinstance(value, str)
    }
    for key in sorted(texts):
        if not texts[key].strip():
            problems.append(f"{path}: {key!r} is empty; write its text")
        elif _placeholders(texts[key]) is None:
            problems.append(f"{path}: {key!r} has unbalanced braces; close every {{ with }}")


def _compare_messages(
    path: Path, messages: Messages, source: str, reference: Messages, problems: list[str]
) -> None:
    """Report the keys a translation lacks or adds, and the placeholders it changes."""
    problems.extend(
        f"{path}: missing {key!r}, which the source {source} has; add it, translated"
        for key in sorted(reference.keys() - messages.keys())
    )
    problems.extend(
        f"{path}: {key!r} is not in the source {source}; add it there first, or remove it"
        for key in sorted(messages.keys() - reference.keys())
    )
    for key in sorted(reference.keys() & messages.keys()):
        expected, actual = _signature(reference[key]), _signature(messages[key])
        if expected is not None and actual is not None and expected != actual:
            problems.append(
                f"{path}: {key!r} has the placeholders {_describe(actual)}, but the source "
                f"{source} has {_describe(expected)}"
            )


def _checked_catalog(path: Path, locale: str, problems: list[str]) -> Messages | None:
    """The messages of a catalog after checking each one on its own; None when it cannot be
    read, which is a problem."""
    try:
        messages = _load_catalog(path, locale)
    except CatalogError as exc:
        problems.append(str(exc))
        return None
    _check_messages(path, messages, problems)
    return messages


def _check_namespace(by_locale: dict[str, Path], source: str, problems: list[str]) -> None:
    """Check the catalogs of one namespace, each translation against the source catalog. The
    translations are read one at a time, so a check holds at most two catalogs in memory."""
    reference = _checked_catalog(by_locale[source], source, problems)
    for locale, path in sorted(by_locale.items()):
        if locale == source:
            continue
        messages = _checked_catalog(path, locale, problems)
        if messages is not None and reference is not None:
            _compare_messages(path, messages, source, reference, problems)


def _check_layout(
    policy: Path, namespace: str, by_locale: dict[str, Path], block: dict[str, Any]
) -> list[str]:
    """The catalogs a namespace lacks for a declared locale, or has without a source catalog."""
    source = block["source"]
    if source not in by_locale:
        return [
            f"{path}: the source locale {source} has no {namespace}; remove this catalog, or "
            "create the source one first"
            for path in sorted(by_locale.values())
        ]
    return [
        f"{policy}: i18n: {namespace} has no catalog of {locale}; create it from the source "
        f"{source}"
        for locale in block["locales"]
        if locale not in by_locale
    ]


def _check_catalogs(
    policy: Path, block: dict[str, Any], problems: list[str], notices: list[str]
) -> None:
    """Check the message catalogs of one i18n block: every namespace of the source locale exists
    in every locale, with the same keys and placeholders."""
    found = _find_catalogs(policy.parent, block, problems)
    source = block["source"]
    if not any(source in by_locale for by_locale in found.values()):
        problems.append(
            f"{policy}: i18n: no catalog of the source locale {source} matches "
            f"{', '.join(block['catalogs'])}; create it, or fix i18n.catalogs"
        )
        return
    unvalidated: set[str] = set()
    for namespace, by_locale in sorted(found.items()):
        layout = _check_layout(policy, namespace, by_locale, block)
        problems.extend(layout)
        if source not in by_locale:
            continue
        suffix = by_locale[source].suffix.lower()
        if suffix in VALIDATED_FORMATS:
            _check_namespace(by_locale, source, problems)
        else:
            unvalidated.add(suffix or "extensionless")
    notices.extend(
        f"{policy}: {suffix} catalogs resolve and must exist in every locale, but their messages "
        "are not validated"
        for suffix in sorted(unvalidated)
    )


def check(root: str | Path, recursive: bool = False, notices: list[str] | None = None) -> list[str]:
    """The problems of the policy files that apply to `root`, and of their message catalogs; []
    when they are all valid.

    With `recursive`, every policy file under `root` is checked too; nested repositories are
    skipped, because they carry and check their own policy. Catalogs in a format whose messages
    are not validated are named in `notices`, which never make a check fail."""
    problems: list[str] = []
    notes: list[str] = [] if notices is None else notices
    try:
        directories = list(_directories(Path(root)))
    except PolicyError as exc:
        return [str(exc)]
    if recursive:
        below = _directories_below(Path(root), problems)
        directories += [d for d in below if d not in directories]
    for directory in directories:
        try:
            files = _policy_files(directory)
            ambiguous = len(files) == 2 and not files[0].samefile(files[1])
        except (PolicyError, OSError) as exc:
            problems.append(str(exc))
            continue
        if ambiguous:
            problems.append(
                f"{directory}: ai18n.yaml and languages.yaml differ; keep one, or make "
                "languages.yaml an alias of ai18n.yaml"
            )
        for policy in files:
            try:
                data = load_file(policy)
            except PolicyError as exc:
                problems.append(str(exc))
                continue
            if policy == files[0] and "catalogs" in data.get("i18n", {}):
                _check_catalogs(policy, data["i18n"], problems, notes)
    return problems


def init_text(options: InitOptions) -> str:
    """The text of a first ai18n.yaml: every tag quoted, so "no" stays Norwegian; UI text
    delegated; skills written for AIs; and, with locales, the i18n block."""
    quote = json.dumps
    lines = [
        "---",
        "# ai18n.yaml: the languages of this repository and of its product.",
        f"# Spec: {SPEC_URL}",
        "ai18n: 1",
        f"default: {quote(options.language)}",
        f"code: {quote(options.code)}",
        f"instruct: {quote(options.instruct)}",
        "ui: delegate",
        "paths:",
        '  - match: ["**/SKILL.md", "**/skills/**"]',
        "    surface: instruct",
    ]
    if options.locales:
        lines += [
            "i18n:",
            f"  source: {quote(options.source or options.locales[0])}",
            f"  locales: {quote(list(options.locales))}",
        ]
        if options.fallback:
            lines.append(f"  fallback: {quote(options.fallback)}")
        if options.catalogs:
            lines.append(f"  catalogs: {quote(list(options.catalogs))}")
    return "\n".join(lines) + "\n"


def init(root: str | Path, options: InitOptions) -> Path:
    """Write the first ai18n.yaml of `root`, validated before it is written, and return its path.

    It never overwrites: a directory that already has a policy is an error."""
    directory = Path(os.path.abspath(root))
    existing = _policy_files(directory)
    if existing:
        raise PolicyError(f"{existing[0]}: {NEVER_OVERWRITE}")
    target = directory / POLICY_NAMES[0]
    text = init_text(options)
    _parse_policy(text, target)
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as exc:
        raise PolicyError(f"{target}: cannot write it ({exc.strerror})") from exc
    return target


def add_agents_line(root: str | Path, line: str) -> bool:
    """Append `line` to the AGENTS.md of `root`, creating the file when it is missing. False when
    the file already has the line, which is never added twice."""
    path = Path(os.path.abspath(root)) / "AGENTS.md"
    try:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if line in text:
            return False
        separator = "" if not text else "\n" if text.endswith("\n") else "\n\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{separator}{line}\n")
    except (OSError, UnicodeDecodeError) as exc:
        raise PolicyError(f"{path}: cannot add the ai18n line ({exc})") from exc
    return True


def _existing_dir(value: str) -> str:
    """An argparse type: the directory must exist, so a typo is an error instead of `valid`."""
    if not os.path.isdir(value):
        raise argparse.ArgumentTypeError(f"directory not found: {value}")
    return value


def _locale_list(value: str) -> list[str]:
    """An argparse type: language tags separated by commas, at least one."""
    tags = [tag.strip() for tag in value.split(",") if tag.strip()]
    if not tags:
        raise argparse.ArgumentTypeError("needs at least one language tag, such as es,en,pt-BR")
    return tags


def _add_init_options(init_cmd: argparse.ArgumentParser) -> None:
    """The options of `init`: the languages of the first policy and the product's locales."""
    init_cmd.add_argument(
        "--root", default=".", type=_existing_dir, help="where to write it (default: .)"
    )
    init_cmd.add_argument(
        "--language", default="en", help="language people read: replies, talk, documentation"
    )
    init_cmd.add_argument("--code", default="en", help="language inside code (default: en)")
    init_cmd.add_argument(
        "--instruct", default="en", help="language of skills and agent prompts (default: en)"
    )
    init_cmd.add_argument(
        "--locales", type=_locale_list, help="locales the product ships, such as es,en,pt-BR"
    )
    init_cmd.add_argument(
        "--source", help="locale where new user-facing text is written first (default: the first)"
    )
    init_cmd.add_argument("--fallback", help="locale the product shows when a key is missing")
    init_cmd.add_argument(
        "--catalog",
        action="append",
        help="where the catalogs live, such as src/locales/{locale}.json; repeatable",
    )
    init_cmd.add_argument(
        "--agents-md", action="store_true", help="add the ai18n line to AGENTS.md, once"
    )


def _parser() -> argparse.ArgumentParser:
    """The command line: resolve, check, show and init."""
    parser = argparse.ArgumentParser(
        prog="ai18n.py",
        description=f"Resolve the ai18n languages of a repository for any AI ({SPEC_URL}).",
    )
    parser.add_argument(
        "--version", action="version", version=f"ai18n.py {__version__} (spec {SPEC_VERSION})"
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
        type=_existing_dir,
        help="repository whose policy applies when the file has none (default: current directory)",
    )
    resolve_cmd.add_argument("--json", action="store_true", help="print one JSON object")
    root_help = "directory to start from (default: current directory)"
    check_cmd = commands.add_parser(
        "check", help="validate the policy files of a repository and their message catalogs"
    )
    check_cmd.add_argument("--root", default=".", type=_existing_dir, help=root_help)
    check_cmd.add_argument(
        "--recursive",
        action="store_true",
        help="also check every policy file under the root, skipping nested repositories",
    )
    show_cmd = commands.add_parser("show", help="print the normalized policy, ready to inject")
    show_cmd.add_argument("--root", default=".", type=_existing_dir, help=root_help)
    show_cmd.add_argument(
        "--format", choices=("text", "json"), default="text", help="text (default) or JSON"
    )
    _add_init_options(
        commands.add_parser(
            "init", help="write the first ai18n.yaml of a project; it never overwrites one"
        )
    )
    return parser


def _run_resolve(args: argparse.Namespace) -> int:
    """`resolve`: the surface and language of a file, or the language of a surface."""
    if args.surface:
        surface, language = args.surface, surface_language(args.surface, args.session)
    else:
        surface, language = resolve(args.path, args.session)
    if args.json:
        print(json.dumps({"surface": surface, "language": language}))
    else:
        print(f"{surface} {language or 'unset'}")
    return 0


def _run_check(args: argparse.Namespace) -> int:
    """`check`: notices and problems go to stderr, and the exit code says whether there was a
    problem; a notice alone never fails."""
    notices: list[str] = []
    problems = check(args.root, recursive=args.recursive, notices=notices)
    for notice in notices:
        print(f"ai18n: note: {notice}", file=sys.stderr)
    for problem in problems:
        print(f"ai18n: {problem}", file=sys.stderr)
    if not problems:
        print("ai18n: valid")
    return 1 if problems else 0


def _run_show(args: argparse.Namespace) -> int:
    """`show`: the normalized policy, as text or JSON."""
    print(show(args.root, args.format), end="")
    return 0


def _run_init(args: argparse.Namespace) -> int:
    """`init`: write the first policy, point AGENTS.md at it when asked, and print what is next."""
    options = InitOptions(
        language=args.language,
        code=args.code,
        instruct=args.instruct,
        locales=tuple(args.locales or ()),
        source=args.source,
        fallback=args.fallback,
        catalogs=tuple(args.catalog or ()),
    )
    print(f"ai18n: wrote {init(args.root, options)}")
    resolver = _resolver_path(args.root)
    line = AGENTS_LINE.format(resolver=resolver)
    steps: list[str] = []
    if not args.agents_md:
        steps.append(f"Add this line to AGENTS.md, or run init with --agents-md:\n   {line}")
    elif add_agents_line(args.root, line):
        print("ai18n: added the ai18n line to AGENTS.md")
    else:
        print("ai18n: AGENTS.md already has the ai18n line")
    if options.catalogs:
        files = ", ".join(
            pattern.replace(LOCALE_TOKEN, locale)
            for pattern in options.catalogs
            for locale in options.locales
        )
        steps.append(f"Create one catalog per locale, with the same keys and placeholders: {files}")
    steps += [
        f"Give every session the output of `python3 {resolver} show`, and install the ai18n skill.",
        f"Check the policy and its catalogs in pre-commit and CI: python3 {resolver} check "
        "--recursive",
    ]
    print("Next steps:")
    for number, step in enumerate(steps, 1):
        print(f"{number}. {step}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the command line: 0 on success, 1 when a policy, a catalog or the schema is invalid or
    init did not write its file, 2 on misuse."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "resolve" and (args.path is None) == (args.surface is None):
        parser.error("resolve takes a path or --surface, exactly one")
    if args.command == "init" and args.locales is None:
        if args.source or args.fallback or args.catalog:
            parser.error("init: --source, --fallback and --catalog need --locales")
    runners = {"resolve": _run_resolve, "check": _run_check, "show": _run_show, "init": _run_init}
    try:
        return runners[args.command](args)
    except PolicyError as exc:
        print(f"ai18n: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
