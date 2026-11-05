# REFERENCE ATLAS

**Built on research.** A visual, source-bound map of the papers, public projects and official articles
referenced by [Agentic Vault](https://github.com/Technoetic/agentic-vault) and
[Semantic Crosscheck](https://github.com/Technoetic/semantic-crosscheck).

**Live:** https://technoetic.github.io/reference-atlas/

## Explore

- A data-driven constellation, with one node per recorded source and actual plugin links.
- A separately generated conceptual artwork for every source card and detail,
  with source-specific motifs and one-to-one source/image verification.
- Search, plugin/type facets, chronological/title ordering, and pinned citation details.
- Local duplicate-reference checks for arXiv, DOI, GitHub repositories and names.
- Downloadable [JSON](data/catalog.json) and [CSV](data/catalog.csv) registries.
- A responsive, reduced-motion-aware interface; no framework, CDN or runtime dependency.

The catalog is a snapshot of published citations. A reference is not a claim of
copied code, a runtime dependency or reproduced benchmark results. Unidentified
research names and background references remain visible as separate categories.
The year shown for an arXiv identifier is a registration-year hint, not necessarily
the final journal publication year. Official articles and public formats are labeled separately;
an article never inflates paper or project counts.

## Check before recommending a source again

```sh
python scripts/check_references.py --url https://arxiv.org/pdf/2502.12110v7.pdf
python scripts/check_references.py --url https://github.com/langchain-ai/openwiki/tree/main --json
python scripts/check_references.py --input candidates.txt --json --fail-on-known
python scripts/check_references.py --published --url https://github.com/langchain-ai/openwiki --json
```

`--fail-on-known` returns exit 3 if an existing strong identifier is found. A name
match is only a possible match. `not_found` means absent from this snapshot; it
does not establish novelty. By default the checker performs no network requests.
With `--published`, it fetches only the current public registry; candidate URLs
are never requested or transmitted. See [the research policy](RESEARCH_POLICY.md).

## Develop and verify

Requires Python 3.10+ and Node.js 24+. There is no dependency installation step.

```sh
python -m unittest discover -s tests -p 'test_*.py'
node --test
python scripts/build_catalog.py
node scripts/build.mjs
python -m http.server 8080 --directory dist
```

`data/registry.source.json` is the curated input; `catalog.json` and `catalog.csv`
are reproducible outputs. Every cited use pins a public plugin commit, file and
line. New records or identity aliases need evidence review before publication.
Query-based views work directly on GitHub Pages, including refresh and history.

The build hashes the source asset graph, embeds its identity in the entry HTML,
and emits `version.json` and an SHA-256 deployment manifest. A changed build is
applied on the next clean navigation; a candidate-list draft is protected until
explicitly cleared. One prior asset graph is retained to support cached entry HTML.
The Pages host controls HTTP cache headers, so the client uses fresh version
requests and build-specific assets/document navigations rather than relying on
custom server headers or a service worker.

## Update the registry

1. Pin the new public plugin revisions and inspect their actual reference statements.
2. Normalize identifiers, compare against existing keys/aliases, and review unresolved names.
3. Update `data/registry.source.json`, preserving previous cited uses and explaining role changes.
4. Rebuild, test and independently review the source/evidence differences.
5. Push the reviewed change; GitHub Actions verifies and publishes GitHub Pages.

For the NVIDIA-inspired v0.41.0 update, the offline helper
`scripts/update_ontology_references.py --plugin-root <plugin-checkout> --commit <public-sha> --tag v0.41.0`
prepares a dry-run from exact release-tag Git blobs. Independently verify the public
tag/commit first, then add `--apply` and run the normal catalog build and tests.
It preserves prior citation excerpts, resolves shifted physical lines by exact
unique matches, and records the article separately from the Auto Ontology project.
These are earlier research references reused for a new application, not claims
of newly discovered research, NVIDIA code adoption or reproduced performance.

The registry is not a live literature index. New versions and new uses may warrant
review after explicitly stating their difference from the prior reference.

## License

Card artwork was generated with the built-in image generation tool. The
[prompt set](docs/card-artwork-unique-prompts.json) records each source's specific
concept, exact prompt and evidence; [media/cards](media/cards/) contains the
optimized dedicated WebP files. These are editorial concept
illustrations, not figures reproduced from the cited papers.
The active manifest preserves generation-time `generationEvidenceUrls` separately
from `currentEvidenceUrls`; the legacy `evidenceUrls` field follows the latter.
Updating a citation snapshot changes neither original image prompts nor image bytes.
Full-resolution generation originals stay outside the public asset graph.

The first artwork iteration is preserved in [the archive](docs/artwork-v1-media/).

MIT for this site's original code. Source titles and citation metadata identify
their respective authors/projects; follow each upstream's license for its code or text.
