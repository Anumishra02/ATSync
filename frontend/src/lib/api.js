import axios from "axios";

// VITE_API_URL (set at build time, e.g. in Vercel's project settings)
// lets the backend host change without a code change + rebuild -- this
// repo has already moved hosts once (Railway -> Render). Falls back to the
// current known-good URL so a build without the env var set still works.
export const API_BASE =
  import.meta.env.VITE_API_URL || "https://atsync-5l6k.onrender.com/api/resume";

export const api = axios.create({ baseURL: API_BASE });

/**
 * POST /v2/analyze -- optional-JD analysis with the three-status model.
 * Send the PDF itself (not pre-extracted text) so the backend can use all
 * parser channels and the contact/link verification module. Omit the JD
 * entirely when blank: quality mode runs, Relevance comes back
 * not_applicable rather than being scored 0.
 */
export async function analyzeResume(file, jobDescription) {
  const form = new FormData();
  form.append("file", file);
  if (jobDescription && jobDescription.trim()) {
    form.append("job_description", jobDescription);
  }
  const { data } = await api.post("/v2/analyze", form);
  return data;
}

/** POST /upload -- extract text from a PDF (used by the cover-letter flow). */
export async function uploadResume(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/upload", form);
  return data;
}

/** POST /cover-letter -- needs resume text + a job description. */
export async function generateCoverLetter({ resumeText, jobDescription, tone }) {
  const { data } = await api.post("/cover-letter", {
    resume_text: resumeText,
    job_description: jobDescription,
    tone,
  });
  return data;
}
