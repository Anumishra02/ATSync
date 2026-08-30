import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import UploadPage from "./UploadPage";
import AnalysisProgressPage from "./AnalysisProgressPage";

const noop = () => {};

describe("UploadPage", () => {
  it("Analyse is disabled with no file and enabled once one is chosen", () => {
    const { rerender } = render(
      <UploadPage file={null} setFile={noop} jd="" setJd={noop} error="" loading={false} onAnalyze={noop} />,
    );
    expect(screen.getByRole("button", { name: /analyse/i })).toBeDisabled();

    const fakePdf = new File(["%PDF-1.4"], "resume.pdf", { type: "application/pdf" });
    rerender(
      <UploadPage file={fakePdf} setFile={noop} jd="" setJd={noop} error="" loading={false} onAnalyze={noop} />,
    );
    expect(screen.getByRole("button", { name: /analyse/i })).toBeEnabled();
  });

  it("states that the resume is not stored, and marks the JD optional", () => {
    render(<UploadPage file={null} setFile={noop} jd="" setJd={noop} error="" loading={false} onAnalyze={noop} />);
    expect(screen.getByText(/processed in memory and not stored/i)).toBeInTheDocument();
    expect(screen.getByText("optional")).toBeInTheDocument();
  });

  it("rejects a non-PDF drop with a reason", () => {
    const setFile = vi.fn();
    render(<UploadPage file={null} setFile={setFile} jd="" setJd={noop} error="" loading={false} onAnalyze={noop} />);
    const zone = document.querySelector('input[type="file"]').closest("label");
    fireEvent.drop(zone, { dataTransfer: { files: [new File(["x"], "resume.png", { type: "image/png" })] } });
    expect(setFile).not.toHaveBeenCalled();
    expect(screen.getByText(/isn't a PDF/i)).toBeInTheDocument();
  });
});

describe("AnalysisProgressPage", () => {
  it("marks completed stages done and holds the rest", () => {
    render(<AnalysisProgressPage stage={2} coldStart={false} />);
    expect(screen.getAllByText("done")).toHaveLength(2);
    expect(screen.getByText(/PARSING PDF/)).toBeInTheDocument();
  });

  it("shows the cold-start line only when flagged", () => {
    const { rerender } = render(<AnalysisProgressPage stage={4} coldStart={false} />);
    expect(screen.queryByText(/free tier spinning back up/i)).not.toBeInTheDocument();
    rerender(<AnalysisProgressPage stage={4} coldStart={true} />);
    expect(screen.getByText(/free tier spinning back up/i)).toBeInTheDocument();
  });
});
