// /v2/analyze's six rubric dimensions -- see
// backend/services/analysis/scorers.py. Each dimension result carries a
// status (scored / uncomputable / not_applicable), not just a score, and
// max_points varies per dimension. Points sum to 100 (match mode); 85 of
// them are available without a job description (Relevance sits out).
export const DIMENSIONS = [
  {
    key: "structure",
    label: "Structure",
    max: 15,
    blurb: "The sections a resume needs, present and properly headed.",
    measures:
      "Whether Experience, Education, Skills and the rest are present and recognised as headed sections.",
  },
  {
    key: "writing",
    label: "Writing",
    max: 15,
    blurb: "Active voice, low filler, no distracting repetition.",
    measures:
      "Passive-voice rate, filler-phrase density, and repetition of distinctive words across bullet and prose content.",
  },
  {
    key: "achievements",
    label: "Achievements",
    max: 20,
    blurb: "How many bullets show quantified or clearly stated impact.",
    measures:
      "The share of achievement bullets carrying a number, or explicit impact language where a number isn't the point.",
  },
  {
    key: "skills",
    label: "Skills",
    max: 15,
    blurb: "Recognised skills found — matched to the job description when supplied.",
    measures:
      "Without a JD: how many recognised skills the resume names. With a JD: how many of the role's skills it covers.",
  },
  {
    key: "experience",
    label: "Experience",
    max: 20,
    blurb: "Each role's org, title, location and dates — and chronological order.",
    measures:
      "Per-entry completeness against the rubric's mechanical fields, plus a reverse-chronological order check.",
  },
  {
    key: "relevance",
    label: "Relevance",
    max: 15,
    blurb: "How strongly the resume aligns with what the JD emphasises.",
    measures:
      "Alignment with the job description's own weighted requirements — required ahead of preferred. Needs a JD to run.",
  },
];

export const DIMENSION_BY_KEY = Object.fromEntries(DIMENSIONS.map((d) => [d.key, d]));

// Fallback copy when the backend result carries no reason of its own.
export const STATUS_FALLBACK = {
  uncomputable: "The resume didn't give this dimension enough to work with.",
  not_applicable: "Add a job description to score this.",
};

// Mirrors HowItWorksPage's four steps (Parse / Score / Verify / Report) --
// deliberately the same vocabulary, not a separate marketing version of
// it, since that page's own copy says this is what the user just watched.
// The visual rebuild of this screen (dot-matrix readout wired to real
// backend stages) is still Step 5's job, untouched here -- this is a
// copy-only change to the existing labels.
export const LOAD_STEPS = [
  "Parsing your resume",
  "Scoring against the rubric",
  "Verifying contact & links",
  "Preparing your report",
];

export const COVER_LETTER_TONES = [
  "professional",
  "friendly",
  "confident",
  "creative",
  "concise",
];
