import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the brand mark", () => {
    render(<App />);
    expect(screen.getAllByText(/ATSync/i).length).toBeGreaterThan(0);
  });
});
