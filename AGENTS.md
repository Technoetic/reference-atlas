# Reference Atlas

Build and publish the public research/reference catalog for Technoetic/agentic-vault
and Technoetic/semantic-crosscheck. Public GitHub Pages only. No Sites hosting.

- Use only published repository citations. No company data, secrets, credentials or
  local source paths in generated public data. All citations point to pinned GitHub commits.
- Browser work uses Aside CLI only, preceded by
  `powershell -NoProfile -ExecutionPolicy Bypass -File D:/NS/00-meta/scripts/aside-up.ps1`.
  No Playwright package, browser or script.
- Preserve distinctions: paper, project, official article, format, unresolved name; direct reference
  versus background. A reference is not a claim of copied code or reproduced results.
- Every catalog entry must have a stable canonical identity and at least one public
  repository citation. Normalize paper versions and repository paths; keep aliases.
- Unknown lookup means not found in this snapshot, never proof of novelty.
- Each catalog source must have its own separately generated artwork. Do not
  reuse topic images across cards or treat renamed copies as unique. Verify
  source-ID assignments, image URLs, actual file hashes, and visual concepts.
  A future source without commissioned artwork uses a text fallback rather than
  borrowing another source's image.
- Keep JS responsibilities separated, CSS tokens/base/components, async load/error
  states, query-based URLs/history, and safe detection of changed builds in open tabs.
- User explicitly authorized creating the site and publishing it to GitHub Pages.
  Do not publish or modify either source plugin as part of this work.

Commands: `node --test`, `python -m unittest discover -s tests -p 'test_*.py'`,
`python scripts/build_catalog.py`, `node scripts/build.mjs`.
