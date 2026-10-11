# Contributing

## Branches

There is one shared branch and one branch per person:

| Branch | Owner | Works in |
|---|---|---|
| `main` | everyone, via PR only | — |
| `fatmanur` | Fatmanur | `src/personas/` (Track A) |
| `yigithan` | Yiğithan | `src/simulation/` (Track B) |
| `hasan` | Hasan | `src/validation/`, `docs/findings.md` (Track C) |
| `ezgi` | Ezgi | `src/ui/` (Track D) |

Rules:
- **Work only on your own branch.** Never commit to or push to someone
  else's branch.
- **Never push to `main`.** It is protected: changes land only through a pull
  request with at least one teammate's approval.
- Stay inside your track's folder. If you need to change a shared file
  (`src/common/`, `docs/methodology-rules.md`, a schema in another track's
  README), do it in a separate small PR and tell the affected tracks.

## Daily workflow

```bash
# once
git clone https://github.com/zxvozayy/Perspectome.git
cd Perspectome
git checkout <your-name>

# every time you start working: bring in what others merged
git pull origin main

# work, then
git add <files>
git commit -m "feat: ..."
git push origin <your-name>
```

Then open a pull request **from your branch into `main`** on GitHub.

## When to open a PR

- **Every finished issue** gets its own PR — don't wait for the sprint to end.
  Small PRs are reviewed fast; big ones conflict.
- Link the issue in the PR description (`Closes #6`) so it closes on merge.
- After your PR is merged, keep working on the same branch; run
  `git pull origin main` first.
- Pull `main` into your branch at least once a week even if you're mid-task,
  so schema changes from other tracks reach you early.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat: ...`,
`fix: ...`, `docs: ...`, `test: ...`, `chore: ...`

## Reviews

- At least one teammate approves before merge. Anyone can review anyone.
- Reviewers check: invariants in
  [`docs/methodology-rules.md`](docs/methodology-rules.md) intact, contract
  unchanged (or announced), tests pass, finding recorded if something was
  measured.
- Explain *why*, not just *what*, in the PR description.

## Issues

Use the issue templates (bug / feature / research task). Every issue sits on
the Iterative Development board (with its sprint) and the Kanban board;
bugs go on the Bug Tracker.
