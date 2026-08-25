# backend/data/

- `skills_seed.json` — 92-term hand-curated bootstrap taxonomy. Committed;
  tests and CI depend on it and must never need a network call.
- `skills_en.csv` — ESCO v1.1.1 classification, English (~13.9k skills).
  **Not committed** (9.5MB external dataset, gitignored). Required only by
  `scripts/compare_taxonomies.py` and by `Taxonomy.from_esco_csv` at
  runtime if the app is configured to use it instead of the seed set.

## Fetching skills_en.csv

```bash
curl -L -o /tmp/esco.zip \
  "https://ec.europa.eu/esco/download/ESCO%20dataset%20-%20v1.1.1%20-%20classification%20-%20en%20-%20csv.zip"
unzip -o /tmp/esco.zip skills_en.csv -d backend/data/
```

The file is large enough that a single `curl` call can time out mid-download
depending on your connection; `curl -C -` resumes a partial download from
where it left off rather than restarting.

Source: [European Skills, Competences, Qualifications and Occupations
(ESCO)](https://esco.ec.europa.eu/en/use-esco/download), European
Commission, Directorate-General for Employment, Social Affairs and
Inclusion. Public, free-to-use dataset (CC BY 4.0).

## Why filter_generic_aliases matters

`Taxonomy.from_esco_csv` defaults to `filter_generic_aliases=True`. Don't
pass `False` in application code without reading that method's docstring
first — the unfiltered load measurably regresses skill-matching accuracy on
the eval corpus (see `evaluation/backlog.md`'s ESCO section). `False`
exists for `scripts/compare_taxonomies.py`'s before/after measurement, not
as a normal loading mode.
