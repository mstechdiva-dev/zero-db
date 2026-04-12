# Claude Code Instructions

## Deployment Rules

### Vercel
- **Never merge a PR if there are active Vercel build errors.**
- Resolve all build errors first, push the fix, confirm the build passes, then merge.
- Check Vercel deployment logs before suggesting or performing a merge.
- Always run `tsc --noEmit` from `apps/web` (not the repo root) before claiming the build is clean.
- Vercel only builds main (production) and open PRs (previews). Fixes pushed to a non-PR branch are invisible to Vercel.

## Branch and PR Rules

- **Never push fixes to a branch that has already been merged.** After a merge, create a new branch off main for any follow-up fixes.
- When a branch has been merged and build errors remain on main, the fix goes on a new branch → new PR → verify preview build passes → then merge.
- Do not accumulate fixes across multiple commits on a dead branch. Cut a clean branch, apply all fixes in one focused commit, open a PR.

## Decision Rules

- **Ask before restructuring plans.** If the user says something like "X should happen last", ask what they want to do next — do not unilaterally reorder phases or create a new plan.
- **Ask before opening a PR.** Confirm with the user before creating any pull request.
- **Never merge without explicit user instruction.** A clean build is necessary but not sufficient — the user must say to merge.
