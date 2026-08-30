import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { TooltipProvider } from "@/components/ui/tooltip";
import LandingPage from "./LandingPage";

const renderLanding = (props) =>
  render(
    <TooltipProvider>
      <LandingPage onCheckResume={() => {}} onHowItWorks={() => {}} onExplainMetrics={() => {}} {...props} />
    </TooltipProvider>,
  );

describe("LandingPage", () => {
  it("shows the pixel headline and both CTAs, wired", async () => {
    const onCheckResume = vi.fn();
    const onHowItWorks = vi.fn();
    renderLanding({ onCheckResume, onHowItWorks });
    expect(screen.getByRole("heading", { name: /ATSync/i })).toBeInTheDocument();
    expect(screen.getByText(/see what the machine sees/i)).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("button", { name: /check resume/i })[0]);
    await userEvent.click(screen.getByRole("button", { name: /how it works/i }));
    expect(onCheckResume).toHaveBeenCalled();
    expect(onHowItWorks).toHaveBeenCalledOnce();
  });

  it("stat strip uses real measured numbers, not the spec's unverified correlation", () => {
    renderLanding();
    expect(screen.getByText("Human-graded resumes")).toBeInTheDocument();
    expect(screen.getByText("Fully scored, every dimension")).toBeInTheDocument();
    // the 0.628 figure from the spec isn't in the repo — must not appear;
    // nor should the negative-reading MAE the user asked to drop
    expect(screen.queryByText(/0\.628/)).not.toBeInTheDocument();
    expect(screen.queryByText(/gap from human/i)).not.toBeInTheDocument();
  });
});
