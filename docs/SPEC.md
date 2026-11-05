# Reference Atlas — source map and duplicate-reference check

## Intent

A visually assertive, Korean-first public catalog of the papers and public
projects referenced by two plugins. Publish to
`https://technoetic.github.io/reference-atlas/`. Future improvement research must
check the registry before describing a source as newly referenced.

## Experience

An ink-dark, full-screen hero with oversized editorial typography and a living
constellation drawn from the real catalog. Two central plugin nodes connect to
their cited sources; shared references have two connections. Lime/lavender accents,
responsive typography, restrained lower sections, reduced-motion support.

The application has query-addressed views `?view=atlas`, `?view=sources`, and
`?view=check`. Search, plugin/type facets, title/year sort, source-detail evidence,
downloadable registry, and local candidate lookup. Counts come from the catalog.
Never invent statistics, citations, adoption levels or publication years.

## Data contract

`data/catalog.json`: `{schemaVersion:1, updatedAt, snapshots, sources:[]}`.
Each source: `{id,kind,title,url,year,tags,keys,aliases,uses,note?}`.
Kinds: `paper`, `project`, `format`, `research-name`. A use has
`{plugin,role,evidence:[{file,line,url,excerpt}]}`; plugin is `agentic-vault` or
`semantic-crosscheck`, role is `reference`, `background`, or `unresolved`.
Evidence URLs pin the source plugin commit. `year` may be null. An arXiv-derived
year is a registration-year hint, not a journal publication claim.

Canonical keys: `arxiv:YYMM.NNNNN`, `doi:lowercase`,
`github:owner/repo`, `name:normalized name`, `url:normalized URL`.
Cross-plugin duplicates merge into one source with multiple uses. Name-only
research remains visibly unresolved and does not inflate identified-paper counts.

`src/core/identity.mjs` exports `canonicalKey(input)` returning
`{key,kind,canonicalUrl}` or null. `src/core/catalog.mjs` exports
`findMatches(catalog,input)` returning `{status,key,matches}` where status is
`known`, `possible`, `not_found`, or `invalid`, and
`filterSources(catalog,{plugin,kind,query,sort,tag})` returning an array.
Plugin and kind filter `all` means no restriction; plugin `shared` means both.

## Scope and safeguards

Catalog snapshots are published sources, not a live citation index. Do not treat
code dependencies/CI tooling as research inspirations. Preserve background and
unresolved items separately. Preserve source aliases and decision explanations.
Lookup runs locally and never sends pasted candidates to an API. An existing paper
may be reviewed again for a new version or question if its delta is stated.

The site, JSON/CSV downloads and Python duplicate-check CLI share one registry.
NS workspace instructions and handoff will link this public registry for future
research; source plugin code and release versions remain unchanged.

## Delivery and verification

Buildless source, Node standard-library content-hashed asset builder, Python
standard-library registry tools. No framework/CDN/runtime dependencies.
GitHub Actions builds/tests and deploys Pages. Browser verification uses Aside.
Meaningful tests cover identity normalization, false duplicate collisions,
cross-plugin merge/evidence, query/filter behavior, failed loading, and update
transitions preserving a draft. Verify actual published HTML, asset graph, JSON,
deep links, missing asset 404, and duplicate examples.
