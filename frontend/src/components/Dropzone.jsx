import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const isPdf = (file) =>
  file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");

// PDF drop zone. Four states: idle / dragover / selected / rejected.
// Rejection always says why.
export default function Dropzone({ file, onSelect, onClear }) {
  const [dragging, setDragging] = useState(false);
  const [rejected, setRejected] = useState(null);
  const inputRef = useRef(null);

  const take = (f) => {
    if (!f) return;
    if (!isPdf(f)) {
      setRejected(`"${f.name}" isn't a PDF. Export or save your resume as a PDF and try again.`);
      return;
    }
    setRejected(null);
    onSelect(f);
  };

  if (file) {
    return (
      <div className="flex items-center justify-between gap-4 rounded-lg border border-hairline bg-card px-5 py-4">
        <div className="min-w-0">
          <p className="truncate text-[13px] text-ink">{file.name}</p>
          <p className="mt-0.5 font-pixel text-[11px] text-subtle">{formatSize(file.size)} · PDF</p>
        </div>
        <button
          onClick={() => {
            onClear();
            setRejected(null);
            if (inputRef.current) inputRef.current.value = "";
          }}
          className="shrink-0 text-[13px] text-nav transition-colors duration-200 ease-stage hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          Remove
        </button>
      </div>
    );
  }

  return (
    <div>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          take(e.dataTransfer.files?.[0]);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-6 py-14 text-center transition-colors duration-200 ease-stage",
          dragging ? "border-ink bg-card" : "border-hairline hover:border-subtle",
          rejected && "border-warn/60",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          onChange={(e) => take(e.target.files?.[0])}
        />
        <p className="font-pixel text-sm text-ink">{dragging ? "DROP TO UPLOAD" : "Drop your resume, or click to choose"}</p>
        <p className="text-[13px] text-subtle">PDF only</p>
      </label>
      {rejected && <p className="mt-3 text-[13px] text-warn">{rejected}</p>}
    </div>
  );
}
