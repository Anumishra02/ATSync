import { motion } from "framer-motion";
import Dropzone from "@/components/Dropzone";
import Pill from "@/components/Pill";

const EASE = [0.22, 1, 0.36, 1];

// Spec Page 3. No fluid canvas -- a page people read. Centred, single
// column, generous space. Analyse is enabled the moment there's a file;
// a blank JD is valid and means a resume-quality score.
export default function UploadPage({ file, setFile, jd, setJd, error, loading, onAnalyze }) {
  return (
    <div className="mx-auto flex w-full max-w-[560px] flex-1 flex-col justify-center px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: EASE }}
      >
        <h1 className="font-pixel text-2xl text-ink">Check a resume</h1>
        <p className="mt-2 text-[13px] text-subtle">
          One PDF. A job description is optional — add one to also score role relevance.
        </p>

        <div className="mt-8 flex flex-col gap-6">
          <Dropzone file={file} onSelect={setFile} onClear={() => setFile(null)} />

          <div>
            <label htmlFor="jd" className="flex items-baseline justify-between">
              <span className="font-pixel text-[11px] uppercase tracking-wider text-subtle">Job description</span>
              <span className="text-[12px] text-absent">optional</span>
            </label>
            <textarea
              id="jd"
              rows={5}
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste a job description to also score role relevance. Leave blank for a resume-quality score."
              className="mt-2 w-full resize-none rounded-lg border border-hairline bg-card px-4 py-3 text-[13px] leading-relaxed text-ink placeholder:text-absent focus:border-subtle focus:outline-none focus:ring-0"
            />
          </div>

          {error && <p className="text-[13px] text-warn">{error}</p>}

          <div className="flex items-center gap-4">
            <Pill size="lg" onClick={onAnalyze} disabled={!file || loading}>
              {loading ? "Analysing…" : "Analyse"}
            </Pill>
          </div>

          <p className="text-[12px] text-absent">
            Your resume is processed in memory and not stored.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
