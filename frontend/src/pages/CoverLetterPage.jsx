import { useState } from "react";
import { motion } from "framer-motion";
import { uploadResume, generateCoverLetter } from "@/lib/api";
import { COVER_LETTER_TONES } from "@/lib/constants";
import Dropzone from "@/components/Dropzone";
import Pill from "@/components/Pill";
import { cn } from "@/lib/utils";

const EASE = [0.22, 1, 0.36, 1];

export default function CoverLetterPage() {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState("");
  const [tone, setTone] = useState("professional");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    if (!file) return setError("Choose a PDF resume first");
    if (!jd.trim()) return setError("A cover letter needs a job description to write against");
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const uploaded = await uploadResume(file);
      const text = uploaded.full_text;
      if (!text || text.length < 10) {
        setError("Couldn't extract text from that PDF.");
        setLoading(false);
        return;
      }
      const data = await generateCoverLetter({ resumeText: text, jobDescription: jd, tone });
      if (data && data.cover_letter) setResult(data);
      else setError("Generation failed. Try again.");
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Something went wrong.");
    }
    setLoading(false);
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(result.cover_letter);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-auto grid w-full max-w-[1000px] flex-1 gap-12 px-6 py-14 md:grid-cols-2 md:py-20">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: EASE }}
      >
        <p className="font-pixel text-[11px] uppercase tracking-[0.2em] text-subtle">Cover letter</p>
        <h1 className="sd-mask mt-3 font-pixel text-2xl text-ink">
          <span>Write one against a role</span>
        </h1>
        <p className="mt-2 text-[13px] leading-relaxed text-subtle">
          Your resume plus the job description. Generative, not scored — there&rsquo;s no rubric behind a cover
          letter the way there is behind the analysis.
        </p>

        <div className="mt-8 flex flex-col gap-6">
          <Dropzone file={file} onSelect={(f) => { setFile(f); setResult(null); }} onClear={() => setFile(null)} />

          <div>
            <label htmlFor="cl-jd" className="font-pixel text-[11px] uppercase tracking-wider text-subtle">
              Job description
            </label>
            <textarea
              id="cl-jd"
              rows={6}
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job description. Required — without a role to write against, the result is a generic template."
              className="mt-2 w-full resize-none rounded-lg border border-hairline bg-card px-4 py-3 text-[13px] leading-relaxed text-ink placeholder:text-absent focus:border-subtle focus:outline-none"
            />
          </div>

          <div>
            <p className="font-pixel text-[11px] uppercase tracking-wider text-subtle">Tone</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {COVER_LETTER_TONES.map((t) => (
                <button
                  key={t}
                  onClick={() => setTone(t)}
                  className={cn(
                    "rounded-full border px-3.5 py-1.5 text-[12px] transition-colors duration-200 ease-stage",
                    tone === t
                      ? "border-ink bg-ink text-stage"
                      : "border-hairline text-nav hover:border-subtle hover:text-ink",
                  )}
                >
                  {t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-[13px] text-warn">{error}</p>}

          <Pill size="lg" onClick={handleGenerate} disabled={loading || !file || !jd.trim()}>
            {loading ? "Writing…" : "Generate"}
          </Pill>
          <p className="text-[12px] text-absent">Your resume is processed in memory and not stored.</p>
        </div>
      </motion.div>

      <div className="md:pt-1">
        <p className="font-pixel text-[11px] uppercase tracking-wider text-subtle">Output</p>
        <div className="card-bloom mt-3 min-h-[420px] rounded-lg border border-white/[0.06] bg-card p-6">
          {loading && (
            <div className="flex h-[380px] flex-col items-center justify-center gap-3 text-center">
              <p className="font-pixel text-sm text-ink">WRITING…</p>
              <p className="max-w-[280px] text-[12px] leading-relaxed text-absent">
                Up to a minute — longer on the first request if the server&rsquo;s been idle.
              </p>
            </div>
          )}

          {!loading && !result && (
            <div className="flex h-[380px] flex-col items-center justify-center gap-2 text-center">
              <p className="text-[13px] text-subtle">Your draft will appear here.</p>
              <p className="text-[12px] text-absent">Add a resume and a job description to start.</p>
            </div>
          )}

          {!loading && result && (
            <div className="relative">
              <button
                onClick={handleCopy}
                className="absolute right-0 top-0 rounded-md border border-hairline px-3 py-1 text-[12px] text-nav transition-colors duration-200 ease-stage hover:border-subtle hover:text-ink"
              >
                {copied ? "Copied" : "Copy"}
              </button>

              {result.subject_line && (
                <p className="pr-16 text-[13px] text-ink">
                  <span className="text-absent">Subject: </span>
                  {result.subject_line}
                </p>
              )}

              {result.key_points?.length > 0 && (
                <ul className="mt-4 flex flex-col gap-2 border-t border-hairline pt-4">
                  {result.key_points.map((p, i) => (
                    <li key={i} className="grid grid-cols-[0.75rem_1fr] gap-2 text-[12px] text-subtle">
                      <span className="font-pixel text-flare">·</span>
                      <span>{p}</span>
                    </li>
                  ))}
                </ul>
              )}

              <p className="mt-4 whitespace-pre-wrap border-t border-hairline pt-4 text-[13px] leading-loose text-ink/90">
                {result.cover_letter}
              </p>

              <p className="mt-4 border-t border-hairline pt-3 font-pixel text-[11px] text-absent">
                ~{result.word_count} words · {tone}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
