import { buildContactFindings, countIssues } from "@/lib/results";
import { cn } from "@/lib/utils";

const MARK = {
  ok: { glyph: "✓", cls: "text-ok" },
  bad: { glyph: "✗", cls: "text-warn" },
  warn: { glyph: "!", cls: "text-warn" },
  note: { glyph: "·", cls: "text-absent" },
};

// Styled as verified findings, not estimates. A phone number is or isn't
// dialable; a domain does or doesn't accept mail; a URL does or doesn't
// resolve. Separate heading, separate section, deliberately not folded
// into the scored dimensions above.
export default function ContactLinks({ contact, parse }) {
  const findings = buildContactFindings(contact, parse);
  const issues = countIssues(findings);

  return (
    <section className="border-t border-hairline pt-10">
      <div className="flex items-baseline justify-between">
        <h2 className="font-pixel text-sm tracking-[0.14em] text-ink">CONTACT &amp; LINKS</h2>
        <span className={cn("font-pixel text-[13px]", issues ? "text-warn" : "text-ok")}>
          {issues === 0 ? "no issues" : `${issues} issue${issues === 1 ? "" : "s"}`}
        </span>
      </div>

      <ul className="mt-5 flex flex-col">
        {findings.length === 0 && (
          <li className="py-2 text-[13px] text-subtle">No contact fields or links detected in the resume.</li>
        )}
        {findings.map((f, i) => {
          const m = MARK[f.status] || MARK.note;
          return (
            <li
              key={i}
              className="grid grid-cols-[1rem_4.5rem_1fr] items-baseline gap-3 border-b border-hairline py-2.5 text-[13px] last:border-b-0"
            >
              <span className={cn("font-pixel text-center", m.cls)}>{m.glyph}</span>
              <span className="font-pixel text-[11px] uppercase tracking-wider text-subtle">{f.label}</span>
              <span className={f.status === "note" ? "text-absent" : "text-ink/90"}>{f.text}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
