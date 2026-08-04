# test_corpus/

This directory holds real résumé PDFs used for local, manual parsing
validation — files that contain real people's names, phone numbers, and
email addresses. It is listed in `.gitignore` and its contents are **never
committed**. This file (and its absence-of-siblings) is committed so the
gap looks deliberate to anyone reading the repo, not like a missing
dependency.

Automated tests never depend on this directory being populated — they run
against the synthetic fixtures in `backend/tests/fixtures/pdfs/` (committed,
fake identities, five layouts of the same content) plus a
`@pytest.mark.skipif(not Path("test_corpus").exists(), ...)` guard on any
test that opportunistically also checks the real corpus when present. A
fresh `git clone && pytest` passes with zero setup.

## Populating it locally

Drop real résumé PDFs directly in this directory (no subfolder structure
required). Useful sources:

- Your own résumé, and any teammates'/friends' who've given permission.
- Public template samples (e.g. the well-known "Jake's Resume" LaTeX
  template, or generic placeholder-name templates from resume-builder
  sites) — safe by construction since they use fake contact info.
- A scanned/photographed resume, to exercise the zero-text-layer path.

What's already been found running the parser against files gathered here
(kept as a record, not because the files themselves are checked in):

- A batch of 12 "resume N" files are scanned images with **zero
  extractable text layer** — `len(page.chars) == 0`, one full-page image.
  Any real pipeline needs to detect this case explicitly (OCR fallback or
  a clear "couldn't read this" response) rather than silently scoring an
  empty string.
- A generic template PDF has icon-font glyphs (phone/LinkedIn/GitHub
  icons) with no Unicode mapping, extracting as `(cid:209)`-style garbage
  or the Unicode replacement character.
