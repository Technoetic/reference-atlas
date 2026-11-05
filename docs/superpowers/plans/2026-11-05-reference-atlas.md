# Reference Atlas Implementation Plan

> For agentic workers: execute through independent implementers and a separate final reviewer.

**Goal:** Publish a visually compelling, evidence-bound research catalog and make
future duplicate-reference checks reusable.

**Architecture:** One audited JSON registry feeds a static ES-module site and an
offline Python checker. Public citation snapshots pin both plugin commits.

**Tech Stack:** HTML/CSS/ES modules, Canvas, Node standard library, Python standard
library, GitHub Actions/Pages, Aside CLI browser verification.

**Spec:** `docs/SPEC.md`.

## Global constraints

- GitHub Pages only; do not register, save or publish a Site.
- Public plugin sources only; no vault/company data or secrets in the public repo.
- Keep strict, background and unresolved reference categories visible.
- Unknown registry match does not establish novelty; permit explicit new-version deltas.
- Preserve working input during version checks; next clean navigation reloads the target.
- Public launch is authorized; source plugin changes/releases are out of scope.

## Review focus

1. A paper PDF/version or GitHub subpath must match its known canonical source.
2. Similar names and unknown identifiers must not be falsely labeled known/new.
3. Counts and shared-source connections must come from actual cited uses.
4. Deep links/history/390px/reduced motion and load errors must work on Pages.
5. A changed build must preserve check-input drafts until a safe navigation.

## Tasks

- [ ] Extract semantic-crosscheck sources; reconcile with the audited agentic-vault inventory.
- [ ] Write failing identity/merge/checker tests, implement one registry pipeline and CLI.
- [ ] Build the extreme visual hero, catalog/detail/filter views and duplicate-check UI.
- [ ] Build hashed assets/version identity and GitHub Actions Pages deployment.
- [ ] Run tests, independent data/code review, and actual Aside local acceptance checks.
- [ ] Publish the concrete reviewed site; cross-check published artifacts/behavior.
- [ ] Connect persistent research guidance to the registry, save evidence, commit owned work.
