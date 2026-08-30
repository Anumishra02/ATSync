import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ResultsPage from "./ResultsPage";
import { SAMPLE_ANALYSIS } from "@/lib/sampleAnalysis";

describe("ResultsPage", () => {
  it("quality mode: states the renormalised denominator and never zeroes an absent dimension", () => {
    render(<ResultsPage analysis={SAMPLE_ANALYSIS.uncomputable} onReset={() => {}} onAddJd={() => {}} />);
    // renormalised caption
    expect(screen.getByText(/of 65 points scored · renormalised/i)).toBeInTheDocument();
    // achievements is uncomputable -> shown as such, no "0"
    const achievements = screen.getByText("Achievements").closest(".grid");
    expect(achievements.textContent).toMatch(/uncomputable/i);
    // relevance is not_applicable -> prompt, not a score
    expect(screen.getByText(/not applicable/i)).toBeInTheDocument();
  });

  it("match mode: shows all six dimensions scored and no add-a-JD prompt", () => {
    render(<ResultsPage analysis={SAMPLE_ANALYSIS.match} onReset={() => {}} onAddJd={() => {}} />);
    expect(screen.getByText("RESUME + ROLE MATCH")).toBeInTheDocument();
    expect(screen.queryByText(/add a job description to also score/i)).not.toBeInTheDocument();
  });

  it("renders contact findings as verified rows", () => {
    render(<ResultsPage analysis={SAMPLE_ANALYSIS.quality} onReset={() => {}} onAddJd={() => {}} />);
    expect(screen.getByText(/CONTACT & LINKS/)).toBeInTheDocument();
    expect(screen.getByText(/valid, dialable/i)).toBeInTheDocument();
  });
});
