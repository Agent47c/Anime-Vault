# Development workflow

1. Create a branch from `main`, such as `fix/path-recovery`.
2. Keep changes focused. Preserve existing features; agree on new features before implementing them.
3. Use temporary fixtures for filesystem/database tests, never a personal library.
4. Run `python scripts/check.py` before pushing. Enable the pre-push hook with
   `git config core.hooksPath .githooks` once per clone.
5. For UI changes, also inspect the running Windows app at the supported sizes,
   themes and display scales. Offscreen tests do not prove pixel-perfect rendering.
6. Push the branch and open a pull request. Review the diff and the Windows CI result.
7. Merge only after checks pass, then update version/changelog when preparing a release.

## Change records required for every improvement

Include a changelog entry and a reviewable implementation record for each phase.
Document the problem and resulting behavior, every changed file's responsibility,
database migrations/backups, visible UI changes, preserved features, test commands
and actual results, and remaining limits/manual checks. Keep the pull request title
and description aligned with the final code, including the final test count.
Do not present proposed or untested behavior as completed implementation.

## Required repository configuration

In GitHub Settings, protect `main` with a branch rule/ruleset requiring pull requests
and the `Windows / Python 3.13` status check. The workflow does not itself enable
branch protection. Avoid force-pushing `main` and do not move released tags.

## Privacy and safety

Maintainer-authorized direct pushes still require the same validation and staged
privacy review. Do not bypass a server-side branch rule or force-push shared
history. An owner-requested source snapshot does not certify a finished release.

Do not commit `.env`, databases, watch lists, cache files, logs, exports or media.
Use invented names and temporary paths in new tests. Inspect `git diff --cached`
before committing. Do not enable administrator mode as an installation requirement.

The shared validation command checks Python syntax and the existing regression suite.
It does not build an EXE, contact live metadata services as a requirement, verify a
clean Windows installation, or replace manual review of destructive file workflows.
