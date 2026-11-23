---
name: repo-readme-builder
description: Inventories a repository and drafts a README whose every claim is traceable to a file — languages, entrypoints, install and run commands from manifests, environment variables with the file that reads them, test framework and layout — leaving explicit [[FILL]] markers wherever the repo does not say, instead of inventing prose. Use when a repo has no README, a README is stale or aspirational, a project needs onboarding docs, or an agent needs a verified map before touching code. Not for marketing copy, API reference generation, or documenting a repo that has no files to read.
---

# Repo README Builder

Most READMEs are written from memory and drift within a week. This one is written from the tree: every command in it was read out of a manifest, every variable was read out of a source file, and anything the repo does not state is marked **[[FILL]]** rather than guessed. The result is a document a new contributor can trust line by line, and a to-do list of the exact sentences only the maintainer can supply.

## Contract

1. **Verified or marked.** A claim appears in the README only if it came from a file; otherwise it appears as `[[FILL]]`. No adjectives, no "simple", no "lightweight".
2. **Commands are copied, not composed.** `install`, `run`, `test` come from `package.json`, `pyproject.toml`, `requirements.txt`, `Makefile`, `Dockerfile` or a detected `__main__` block. Nothing is inferred from a directory name.
3. **Environment variables carry their reader.** The table lists the variable and the file(s) that read it, because that is the one fact a newcomer needs to find the default.
4. **Gaps are the deliverable, not a failure.** A README with 8 honest `[[FILL]]` markers beats one with 0 markers and 3 wrong commands. Report the gap count.
5. **No install instructions for a language the inventory did not find.** A Python repo gets pip; a repo with no manifest gets a marker, not a guess.
6. **The draft is a draft.** It goes out after the maintainer fills the markers; the skill never presents it as finished documentation.

## Workflow

### Step 0 — Point it at a tree

```bash
python scripts/readme_facts.py --repo . --out out/
python scripts/readme_facts.py --repo ../service --out out/service-readme
```

It walks the tree once, skipping `.git`, `node_modules`, virtualenvs, build output and caches, and writes `out/README.md` plus `out/repo_facts.json` (the same facts, machine-readable, for a second pass).

### Step 1 — Read what it actually verified

| Section | Source of every line |
|---|---|
| What is here | file counts, line counts, language histogram, licence file, manifests |
| Requirements | `engines`, `.python-version`, else `[[FILL]]` |
| Install | `package.json` → npm/pnpm/yarn (by lockfile), `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod` |
| Run | `scripts.dev/start/serve/build`, console scripts, `__main__` files, `Dockerfile` CMD, `Makefile` targets |
| Test | pytest / jest / vitest / mocha evidence from manifests, config names, `conftest.py` |
| Configuration | `os.environ`, `os.getenv`, `process.env`, `env(...)`, plus `.env.example` declarations |
| Layout | top-level paths, file counts, role guessed only for conventional names |

### Step 2 — Fill the markers in this order

1. The one-sentence purpose. Nothing in the tree yields intent.
2. The third column of the configuration table: required or optional, format, default.
3. Every layout row whose role is not conventional.
4. The test bar: what must pass before merge.

Then delete the "For an AI agent reading this" section if a human audience is the only reader.

### Step 3 — Check the four claims that go wrong most

- **Install** — run it verbatim in a clean shell. A README install line that fails is worse than none.
- **Run** — if the manifest script starts a server, say which port; the inventory only prints the command.
- **Env** — a variable read by `os.environ[…]` (no default) breaks startup when unset. Mark those required explicitly.
- **Test** — if the framework is "unclear", say so; do not print `pytest` because a `tests/` directory exists.

### Step 4 — Ship

Deliver `README.md` (the draft with markers), `repo_facts.json` (evidence), and a one-paragraph note naming what the maintainer must fill. If a README already exists, do not overwrite it silently: write `README.draft.md` and diff the two, because the existing file may contain history and tone that the inventory cannot reproduce.

## Output format

- Title = the name from the manifest, falling back to the directory.
- A `[[FILL]]` marker is bold and bracketed exactly as shown, so it is greppable: `grep -n '\[\[FILL\]\]' README.md`.
- Tables, not prose, for anything with more than three items.
- No badge until CI has run once; the inventory can see a workflow file, not a green build.
- The closing note lists the markers in order, with the file that should answer each.

## Boundaries

- Cannot read intent, roadmap, audience, or architecture rationale.
- Cannot verify that a command works; it verifies that the command is what the manifest declares.
- Does not generate API reference, changelog, screenshots, or badges.
- Monorepos: run it per package, not once at the root — a root run reports every sub-package as a directory.
- Not a linter: a missing README is the reason to run it, not a finding.
