# Contributing

## Branches

- `main` — always stable. No direct pushes; changes land via pull request.
- `dev` — active development; feature branches merge here first.
- `feature/<short-name>` — one branch per task.

## Workflow

1. Branch off `dev`: `git checkout -b feature/your-task dev`
2. Commit using [Conventional Commits](https://www.conventionalcommits.org/):
   `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`
3. Open a pull request into `dev`. Fill in the PR template.
4. At least one teammate review before merge.
5. `dev` merges into `main` at milestones (sprint end / before a presentation).

## Issues

Use the issue templates (bug / feature / research task). Every issue should end up
on one of the three project boards (Iterative Development, Kanban, Bug Tracker).

## Code review

- Keep PRs small and focused on one task.
- Explain *why*, not just *what*, in the PR description.
