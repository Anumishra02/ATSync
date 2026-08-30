// /v2/analyze's six rubric dimensions -- see
// backend/services/analysis/scorers.py. Dimensions carry a status
// (scored / uncomputable / not_applicable), not just a score, and
// max_points varies per dimension rather than every check being /100.
export const DIMENSIONS = [
  {
    key: "structure",
    label: "Structure",
    icon: "📋",
    desc: "Are the sections a resume needs (Experience, Education, Skills…) present and properly headed?",
  },
  {
    key: "writing",
    label: "Writing",
    icon: "✍️",
    desc: "Clarity, active voice, and freedom from filler language.",
  },
  {
    key: "achievements",
    label: "Achievements",
    icon: "🏆",
    desc: "How many bullet points show quantified or clearly stated impact.",
  },
  {
    key: "skills",
    label: "Skills",
    icon: "🎯",
    desc: "Recognized skills found in the resume -- matched against the job description when one is supplied.",
  },
  {
    key: "experience",
    label: "Experience",
    icon: "💼",
    desc: "Completeness of each work-experience entry (org, title, dates, location) and chronological order.",
  },
  {
    key: "relevance",
    label: "Relevance",
    icon: "🧭",
    desc: "How strongly the resume aligns with what the job description actually emphasizes. Needs a job description to run.",
  },
];

export const STATUS_META = {
  scored: {},
  uncomputable: {
    label: "N/A",
    note: "Couldn't be scored -- the resume didn't give this dimension enough to work with.",
  },
  not_applicable: {
    label: "—",
    note: "Not applicable in quality mode -- add a job description to score this.",
  },
};

export const LOAD_STEPS = [
  "Parsing your resume",
  "Analyzing your experience",
  "Extracting your skills",
  "Generating recommendations",
];

export const COVER_LETTER_TONES = [
  "professional",
  "friendly",
  "confident",
  "creative",
  "concise",
];
