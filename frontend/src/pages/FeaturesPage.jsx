import { DIMENSIONS } from "@/lib/constants";
import { PageIntro, Section, Row, Note } from "@/components/content/Section";

// The product page: what's scored, on what basis, and what's checked
// rather than estimated. Dimension copy is read from lib/constants.js's
// DIMENSIONS -- the same data ResultsPage renders -- so this page and the
// results screen can't drift on what a dimension measures.
export default function FeaturesPage() {
  return (
    <div className="mx-auto w-full max-w-[720px] px-6 pb-24">
      <PageIntro
        eyebrow="What ATSync does"
        title="Six dimensions, on the record"
        sub="What each score is actually based on — not a keyword count, and not a black box."
      />

      <Section
        heading="THE SIX SCORING DIMENSIONS"
        note="100 points total. Relevance only runs when you supply a job description — see Two modes below."
      >
        <div className="divide-y divide-hairline">
          {DIMENSIONS.map((d) => (
            <div key={d.key} className="grid grid-cols-[1fr_auto] items-baseline gap-x-6 py-4">
              <div className="min-w-0">
                <h3 className="text-[15px] font-medium text-ink">{d.label}</h3>
                <p className="mt-1 text-[13px] leading-relaxed text-subtle">{d.measures}</p>
              </div>
              <span className="font-pixel text-subtle">/{d.max}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section heading="CONTACT & LINK VERIFICATION" note="Checked, not estimated.">
        <Row label="Phone validity" sub="by region" />
        <Row label="Email deliverability" sub="MX lookup" />
        <Row label="Link reachability" sub="does it actually resolve" />
        <Row label="Unclickable-URL detection" sub="text with no href" />
        <Note>
          An unclickable URL looks like a link in the text but has no href behind it — invisible in your own PDF
          viewer, same as it is to an ATS.
        </Note>
      </Section>

      <Section heading="TWO MODES">
        <Row label="Quality — no job description" value="/85" />
        <Row label="Match — job description supplied" value="/100" />
        <Note>
          The denominator is always stated. A quality-mode score is never silently measured against a full 100 it
          never had a chance to reach.
        </Note>
      </Section>

      <Section heading="WHAT IT WON'T GUESS">
        <p className="text-[13px] leading-relaxed text-subtle">
          A dimension that can&rsquo;t be assessed is marked <span className="text-ink">uncomputable</span>, not
          scored 0 — a resume this system genuinely can&rsquo;t read on that dimension isn&rsquo;t the same as one
          it read and found empty.
        </p>
        <Note>
          Example: a resume with no bulleted content can&rsquo;t have Achievements assessed — there&rsquo;s nothing
          to check for quantified impact. Instead of a 0 (which would say &ldquo;graded, and failed&rdquo;), that
          dimension is marked uncomputable and the rest are reweighted so the score stays comparable — out of the
          points that could actually run, not padded to 100.
        </Note>
      </Section>

      <Section heading="COVER LETTER">
        <Row label="Job description" value="required" />
        <p className="mt-4 text-[13px] leading-relaxed text-subtle">
          Without one, the result would be a generic template — so the product declines rather than producing
          something weak.
        </p>
        <Note>
          Generative, not evaluative: there&rsquo;s no rubric, no scoring, and no measurement behind a cover letter
          the way there is for the analysis above.
        </Note>
      </Section>
    </div>
  );
}
