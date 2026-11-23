#!/usr/bin/env python3
"""Inventory a repository and emit a README whose claims are all traceable to files."""
import argparse
import json
import os
import re
import sys

SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "venv", ".venv", "env", "dist", "build",
             "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", "target", "vendor",
             ".idea", ".vscode", "coverage", ".next", ".nuxt", "site-packages"}

LANG = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".rb": "Ruby", ".php": "PHP",
    ".cs": "C#", ".c": "C", ".h": "C", ".cpp": "C++", ".swift": "Swift", ".m": "Objective-C",
    ".sh": "Shell", ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".md": "Markdown", ".yml": "YAML", ".yaml": "YAML", ".json": "JSON", ".toml": "TOML",
    ".lua": "Lua", ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir", ".vue": "Vue", ".svelte": "Svelte",
}
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php",
            ".cs", ".c", ".cpp", ".swift", ".sh", ".sql", ".vue", ".svelte", ".dart", ".lua"}
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec)/|(_test|\.test|\.spec|test_)\.\w+$")
ENTRY_NAMES = {"main.py", "app.py", "cli.py", "server.py", "manage.py", "wsgi.py", "asgi.py",
               "index.js", "index.ts", "server.js", "server.ts", "main.go", "main.rs", "Main.java",
               "main.rb", "app.rb", "cli.rb", "Program.cs"}


def walk(root):
    files = []
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and (not d.startswith(".") or d == ".github")]
        for n in names:
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, root).replace("\\", "/")
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            files.append({"rel": rel, "size": size, "ext": os.path.splitext(n)[1].lower()})
    return files


def read(path, limit=200000):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def load_json(path):
    try:
        return json.loads(read(path))
    except Exception:
        return None


def pyproject(path):
    txt = read(path)
    out = {"name": None, "scripts": {}, "deps": []}
    try:
        import tomllib
        data = tomllib.loads(txt)
        proj = data.get("project", {}) or {}
        out["name"] = proj.get("name")
        out["scripts"] = (proj.get("scripts") or {})
        out["deps"] = list(proj.get("dependencies") or [])
        poetry = (data.get("tool", {}) or {}).get("poetry", {}) or {}
        if not out["name"]:
            out["name"] = poetry.get("name")
        if poetry:
            out["scripts"] = out["scripts"] or (poetry.get("scripts") or {})
            out["deps"] = out["deps"] or list((poetry.get("dependencies") or {}).keys())
    except Exception:
        m = re.search(r'name\s*=\s*"([^"]+)"', txt)
        out["name"] = m.group(1) if m else None
        for m in re.finditer(r'^([\w\-]+)\s*=\s*"[^"]+"$', txt, re.M):
            out["scripts"].setdefault(m.group(1), m.group(1))
    return out


ENV_PATTERNS = [
    re.compile(r"os\.environ\[\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']\s*\]"),
    re.compile(r"os\.environ\.get\(\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']"),
    re.compile(r"os\.getenv\(\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']"),
    re.compile(r"process\.env\.([A-Z][A-Z0-9_]{2,})"),
    re.compile(r"process\.env\[\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']\s*\]"),
    re.compile(r"env\(\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']"),
    re.compile(r"getenv\(\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']"),
]

ENTRY_MAIN = re.compile(r"if\s+__name__\s*==\s*[\"']__main__[\"']")


def scan(root, files):
    facts = {"root": root, "languages": {}, "code_files": 0, "total_lines": 0,
             "entrypoints": [], "commands": {}, "env": {}, "tests": {"dirs": [], "frameworks": []},
             "manifests": [], "make_targets": [], "docker": {}, "top_dirs": {}, "readme_exists": False,
             "has_ci": False, "license": None, "tests_count": 0}

    for f in files:
        rel = f["rel"]
        lang = LANG.get(f["ext"])
        if lang:
            facts["languages"][lang] = facts["languages"].get(lang, 0) + 1
        if f["ext"] in CODE_EXT:
            facts["code_files"] += 1
            facts["total_lines"] += read(os.path.join(root, rel)).count("\n") + 1
        if rel.count("/") == 0:
            facts["top_dirs"].setdefault(rel, 0)
        else:
            top = rel.split("/")[0]
            facts["top_dirs"][top] = facts["top_dirs"].get(top, 0) + 1
        base = os.path.basename(rel)
        if base in ENTRY_NAMES:
            facts["entrypoints"].append(rel)
        if TEST_RE.search(rel) and f["ext"] in CODE_EXT:
            facts["tests_count"] += 1
            d = os.path.dirname(rel) or "."
            if d not in facts["tests"]["dirs"]:
                facts["tests"]["dirs"].append(d)
        if base.lower().startswith("readme"):
            facts["readme_exists"] = True
        if base in ("LICENSE", "LICENSE.md", "LICENCE"):
            facts["license"] = base
        if rel.startswith(".github/workflows/") or base in (".gitlab-ci.yml", "Jenkinsfile", "azure-pipelines.yml"):
            facts["has_ci"] = True

    # manifests
    for name in ("package.json", "pyproject.toml", "setup.py", "requirements.txt", "Makefile",
                 "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Cargo.toml", "go.mod",
                 "Gemfile"):
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        facts["manifests"].append(name)
        if name == "package.json":
            data = load_json(p) or {}
            facts["commands"]["package.json"] = {
                "name": data.get("name"), "scripts": data.get("scripts") or {},
                "bin": data.get("bin") or {}, "engines": data.get("engines") or {},
                "deps": sorted((data.get("dependencies") or {}).keys())[:12],
            }
        if name == "pyproject.toml":
            facts["commands"]["pyproject.toml"] = pyproject(p)
        if name == "Makefile":
            txt = read(p)
            facts["make_targets"] = sorted(set(re.findall(r"^([A-Za-z0-9_.\-/]+)\s*:(?!=)", txt, re.M)))[:20]
        if name == "Dockerfile":
            txt = read(p)
            facts["docker"]["expose"] = re.findall(r"^EXPOSE\s+(\S+)", txt, re.M)
            facts["docker"]["cmd"] = re.findall(r"^(?:CMD|ENTRYPOINT)\s+(.+)$", txt, re.M)[:3]
            facts["docker"]["base"] = re.findall(r"^FROM\s+(\S+)", txt, re.M)[:3]
        if name.startswith("docker-compose"):
            txt = read(p)
            svcs = re.findall(r"^  ([a-zA-Z0-9_.\-]+):\s*$", txt, re.M)
            facts["docker"]["services"] = svcs[:12]

    # env vars from code + .env files
    for f in files:
        if f["ext"] not in (".py", ".js", ".ts", ".go", ".rb", ".php", ".java", ".sh", ".yml", ".yaml"):
            continue
        if f["size"] > 400000:
            continue
        txt = read(os.path.join(root, f["rel"]))
        for pat in ENV_PATTERNS:
            for m in pat.finditer(txt):
                key = m.group(1)
                facts["env"].setdefault(key, []).append(f["rel"])
    for envname in (".env.example", ".env.sample", ".env.template", "env.example"):
        p = os.path.join(root, envname)
        if os.path.isfile(p):
            for line in read(p).splitlines():
                m = re.match(r"^\s*([A-Z][A-Z0-9_]{2,})\s*=", line)
                if m:
                    facts["env"].setdefault(m.group(1), ["%s (declared)" % envname])

    # test frameworks
    dep_text = []
    for m in facts["manifests"]:
        if m.startswith("requirements"):
            dep_text.append(read(os.path.join(root, m)))
    pj = facts["commands"].get("package.json") or {}
    dep_text.append(" ".join(pj.get("deps") or []))
    dep_text.append(" ".join((facts["commands"].get("pyproject.toml") or {}).get("deps") or []))
    joined = " ".join(dep_text).lower()
    names = {os.path.basename(f["rel"]) for f in files}
    if any(n in names for n in ("pytest.ini", "conftest.py", "tox.ini")) or "pytest" in joined:
        facts["tests"]["frameworks"].append("pytest")
    if "vitest.config.ts" in names or "vitest.config.js" in names or "vitest" in joined:
        facts["tests"]["frameworks"].append("vitest")
    if any(n in names for n in ("jest.config.js", "jest.config.ts", "jest.config.json")) or "jest" in joined:
        facts["tests"]["frameworks"].append("jest")
    if facts["tests"]["frameworks"]:
        facts["tests"]["frameworks"] = sorted(set(facts["tests"]["frameworks"]))
    if not facts["tests"]["frameworks"] and facts["tests"]["dirs"]:
        facts["tests"]["frameworks"].append("unclear")

    # python __main__ entrypoints
    for f in files:
        if f["ext"] == ".py" and f["size"] < 200000 and ENTRY_MAIN.search(read(os.path.join(root, f["rel"]))):
            if f["rel"] not in facts["entrypoints"]:
                facts["entrypoints"].append(f["rel"])
    facts["entrypoints"] = facts["entrypoints"][:8]
    return facts


def md_tree(facts, limit=12):
    rows = []
    for name, count in sorted(facts["top_dirs"].items(), key=lambda kv: -kv[1])[:limit]:
        rows.append((name, count))
    return rows


def render(facts):
    name = None
    pj = facts["commands"].get("package.json") or {}
    pp = facts["commands"].get("pyproject.toml") or {}
    name = pj.get("name") or pp.get("name") or os.path.basename(os.path.abspath(facts["root"]))
    langs = sorted(facts["languages"].items(), key=lambda kv: -kv[1])
    lang_line = ", ".join("%s (%d files)" % (k, v) for k, v in langs[:4] if k in
                          ("Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "Ruby", "PHP", "C#")) or "not detected"

    L = []
    L.append("# %s\n" % name)
    L.append("> One sentence: what this is and who it is for. **[[FILL]]** — the inventory cannot read intent.\n")
    if facts["has_ci"]:
        L.append("_CI config present. Badge: add the workflow URL after the first green run._\n")

    L.append("\n## What is here\n")
    L.append("| | |")
    L.append("|---|---|")
    L.append("| Code files | %d |" % facts["code_files"])
    L.append("| Lines of code | %s |" % format(facts["total_lines"], ","))
    L.append("| Languages | %s |" % lang_line)
    L.append("| Test files | %d |" % facts["tests_count"])
    if facts["license"]:
        L.append("| License file | `%s` |" % facts["license"])
    L.append("| Manifests | %s |" % (", ".join("`%s`" % m for m in facts["manifests"]) or "none found"))

    L.append("\n## Requirements\n")
    req = []
    for k, v in (pj.get("engines") or {}).items():
        req.append("- %s `%s`" % (k, v))
    if not req:
        req.append("- Language runtime: **[[FILL]]** (no `engines` field, no `.python-version`)")
    L.append("\n".join(req))
    L.append("")

    L.append("\n## Install\n")
    steps = []
    if "package.json" in facts["manifests"]:
        pm = "pnpm" if os.path.isfile(os.path.join(facts["root"], "pnpm-lock.yaml")) else \
             "yarn" if os.path.isfile(os.path.join(facts["root"], "yarn.lock")) else "npm"
        steps.append("```bash\n%s install\n```" % pm)
    if "requirements.txt" in facts["manifests"]:
        steps.append("```bash\npython -m pip install -r requirements.txt\n```")
    if "pyproject.toml" in facts["manifests"]:
        steps.append("```bash\npython -m pip install -e .\n```")
    if "Cargo.toml" in facts["manifests"]:
        steps.append("```bash\ncargo build\n```")
    if "go.mod" in facts["manifests"]:
        steps.append("```bash\ngo mod download\n```")
    L.append("\n\n".join(steps) if steps else "**[[FILL]]** — no install manifest found. State the install step explicitly.")

    L.append("\n## Run\n")
    run = []
    for k, v in (pj.get("scripts") or {}).items():
        if k in ("dev", "start", "serve", "build"):
            run.append("- `%s` → `%s`" % (k, v))
    for k, v in (pp.get("scripts") or {}).items():
        run.append("- `%s`: `%s` (console script)" % (k, k))
    for e in facts["entrypoints"]:
        if e.endswith(".py") and "test" not in e:
            run.append("- `python %s` (has `__main__` block)" % e)
    if facts["docker"].get("cmd"):
        run.append("- container: `%s`" % facts["docker"]["cmd"][0].strip()[:90])
    if facts["make_targets"]:
        run.append("- make targets present: %s" % ", ".join("`%s`" % t for t in facts["make_targets"][:10]))
    L.append("\n".join(run) if run else "**[[FILL]]** — no start command found in a manifest; the entrypoint is not obvious from the tree.")

    L.append("\n## Test\n")
    tl = []
    for fw in facts["tests"]["frameworks"]:
        if fw == "pytest":
            tl.append("```bash\npython -m pytest\n```")
        elif fw in ("jest",):
            tl.append("```bash\nnpm test\n```")
        elif fw == "vitest":
            tl.append("```bash\nnpx vitest run\n```")
        elif fw == "mocha":
            tl.append("```bash\nnpm test\n```")
    if tl:
        L.append("\n\n".join(tl))
        L.append("\n**[[FILL]]** — state the minimum bar: what must pass before merge.")
    else:
        L.append("**[[FILL]]** — no test framework detected and %d test-shaped file(s) exist; say how tests run." % facts["tests_count"])

    L.append("\n## Configuration\n")
    if facts["env"]:
        L.append("| Variable | Read in | Required |")
        L.append("|---|---|---|")
        for k, srcs in sorted(facts["env"].items()):
            readers = sorted(set(s.rsplit("/", 1)[-1] for s in srcs))
            L.append("| `%s` | %s | **[[FILL]]** |" % (k, ", ".join(readers[:3])))
        L.append("\nDefaults and formats are not inferable from the read site; fill the third column.")
    else:
        L.append("No environment variable is read in the scanned code.")

    L.append("\n## Layout\n")
    L.append("| Path | Files | Role |")
    L.append("|---|---|---|")
    role = {"src": "source", "lib": "library", "tests": "tests", "test": "tests", "docs": "docs",
            "scripts": "tooling", "app": "application", "api": "service", "web": "frontend",
            "backend": "service", "db": "schema and migrations", "migrations": "schema",
            "config": "configuration", "assets": "static assets", "cmd": "entrypoints"}
    file_role = {"Dockerfile": "container image", "Makefile": "task shortcuts", "LICENSE": "licence",
                 "package.json": "dependency manifest", "pyproject.toml": "dependency manifest",
                 "requirements.txt": "dependency manifest", "go.mod": "dependency manifest",
                 "Cargo.toml": "dependency manifest", "Gemfile": "dependency manifest",
                 "docker-compose.yml": "local stack", ".env.example": "environment template"}
    for name_, count in md_tree(facts):
        if os.path.isdir(os.path.join(facts["root"], name_)):
            L.append("| `%s/` | %d | %s |" % (name_, count, role.get(name_, "**[[FILL]]**")))
        else:
            L.append("| `%s` | 1 | %s |" % (name_, file_role.get(name_, "**[[FILL]]**")))

    L.append("\n## For an AI agent reading this\n")
    L.append("- Entrypoints found: %s." % (", ".join("`%s`" % e for e in facts["entrypoints"]) or "none"))
    L.append("- Commands verified in manifests: install, run and test above are copy-pasteable as written.")
    L.append("- Anywhere **[[FILL]]** appears, the claim was not in the repo. Do not guess it; ask the maintainer.")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Inventory a repo and draft a verifiable README")
    ap.add_argument("--repo", default=".", help="repository root")
    ap.add_argument("--out", default="out", help="output directory")
    ap.add_argument("--json", action="store_true", help="also write facts.json (always written)")
    a = ap.parse_args()
    if not os.path.isdir(a.repo):
        sys.exit("not a directory: %s" % a.repo)
    files = walk(a.repo)
    if not files:
        sys.exit("empty directory: %s" % a.repo)
    facts = scan(a.repo, files)
    os.makedirs(a.out, exist_ok=True)
    md = render(facts)
    with open(os.path.join(a.out, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(a.out, "repo_facts.json"), "w", encoding="utf-8") as fh:
        json.dump(facts, fh, indent=2)
    gaps = md.count("[[FILL]]")
    print("files=%d code=%d lines=%d entrypoints=%d env=%d tests=%d gaps=%d" % (
        len(files), facts["code_files"], facts["total_lines"], len(facts["entrypoints"]),
        len(facts["env"]), facts["tests_count"], gaps))
    print("wrote %s" % os.path.join(a.out, "README.md"))


if __name__ == "__main__":
    sys.exit(main())
