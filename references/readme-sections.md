# Sections, claims and markers

## What a README must answer, in order

1. What is this, in one sentence, and who is it for.
2. What does it need to run.
3. How do I install it.
4. How do I start it.
5. How do I know it still works.
6. Where do I configure it.
7. Where do I change it.

The script produces 2–7 from the tree. Only 1 is unrecoverable, which is why it is the first `[[FILL]]`.

## Verified claims and their sources

| Claim type | Evidence the script accepts | What it refuses to do |
|---|---|---|
| Language mix | extension histogram over all non-skipped files | claim "primary language" from one guess |
| Entrypoint | filename in the known set, or an `if __name__ == "__main__"` block | assert which entrypoint production uses |
| Install | a manifest that declares dependencies | invent a version or a package manager |
| Run | `scripts` dev/start/serve/build, console scripts, Docker `CMD`, `make` targets | promise a port, a host, or a flag |
| Test | framework evidence in manifests, lockfiles, config filenames, `conftest.py` | run the tests |
| Config | a read site in source code, or a declaration in `.env.example` | state which variables are required |
| Layout role | conventional directory names (`src`, `tests`, `migrations`) | explain a directory with a custom name |

## Markers

`[[FILL]]` is deliberately ugly. It survives copy-paste, it is greppable, and it cannot be mistaken for prose.

Where markers belong:

- The purpose sentence.
- The required/optional column of the environment table.
- Any layout row whose directory name is not conventional.
- The testing bar.
- Any deployment, hosting or data-retention statement — nothing in the tree implies those.

Where they do not belong:

- A section the repo fully answers. Do not add `[[FILL]]` "just in case"; a marker per section teaches the reader to ignore markers.
- Inside a code block. Keep commands exact; if a command is unknown, do not print a block at all.

## The four false claims a generated README tends to make

1. **"Just run `npm install`"** in a repo that uses pnpm — the lockfile is the tiebreaker, and a second lockfile is a `[[FILL]]`.
2. **"Start with `python main.py`"** when `main.py` imports a package that only resolves after an editable install. Print the install step first, or mark the run step.
3. **"Copy `.env.example` to `.env`"** when the code reads a variable that is not in the example file. List the difference explicitly; that is a real onboarding blocker.
4. **A CI badge** on a repo whose workflow has never run. The inventory can see `.github/workflows`, not a green check.

## Monorepos

Run per package. At the root, the honest output is a table of packages plus a `[[FILL]]` for what binds them, not a README for the whole tree:

```bash
for d in packages/*/; do python scripts/readme_facts.py --repo "$d" --out "out/$(basename "$d")"; done
```

## When a README already exists

Write `README.draft.md` and compare. Keep the existing file's:

- purpose, history, tone, links, screenshots, badges
- anything already true that the inventory cannot see

Replace only claims that are provably wrong: a wrong install command, a stale env table, a layout that no longer matches. A rewrite that deletes a maintainer's voice is not an improvement, and the file is not yours.
