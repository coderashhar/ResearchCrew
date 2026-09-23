import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Report } from "./Report";
import type { SourceSummary } from "@/lib/types";

const sources: SourceSummary[] = [
  { id: 1, title: "First paper", domain: "nature.com", url: "https://nature.com/a" },
  { id: 2, title: "Second paper", domain: "who.int", url: "https://who.int/b" },
];

describe("Report", () => {
  it("turns a citation into a chip for its source", () => {
    render(<Report report="A claim [2]." sources={sources} />);
    expect(screen.getByLabelText("Source 2: Second paper")).toHaveTextContent("2");
  });

  it("renders a chip per id in a grouped citation", () => {
    render(<Report report="A claim [1, 2]." sources={sources} />);
    expect(screen.getByLabelText("Source 1: First paper")).toBeInTheDocument();
    expect(screen.getByLabelText("Source 2: Second paper")).toBeInTheDocument();
  });

  it("leaves a citation with no source as plain text", () => {
    render(<Report report="Invented [9]." sources={sources} />);
    expect(screen.queryByLabelText(/Source 9/)).toBeNull();
    expect(screen.getByText(/Invented \[9\]\./)).toBeInTheDocument();
  });

  it("cites inside headings and list items too", () => {
    render(<Report report={"## Finding [1]\n\n- Point [2]"} sources={sources} />);
    expect(screen.getByLabelText("Source 1: First paper")).toBeInTheDocument();
    expect(screen.getByLabelText("Source 2: Second paper")).toBeInTheDocument();
  });

  it("shows the source detail when a chip is opened", async () => {
    render(<Report report="A claim [1]." sources={sources} />);
    await userEvent.click(screen.getByLabelText("Source 1: First paper"));

    expect(await screen.findByText("First paper")).toBeInTheDocument();
    expect(screen.getByText("nature.com")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open source" })).toHaveAttribute(
      "href",
      "https://nature.com/a",
    );
  });

  it("renders markup in source text as text, never as HTML", async () => {
    const hostile: SourceSummary[] = [
      { id: 1, title: "<img src=x onerror=alert(1)>", domain: "a.com", url: "https://a.com" },
    ];
    render(<Report report="Claim [1]." sources={hostile} />);
    await userEvent.click(screen.getByLabelText(/Source 1/));

    expect(await screen.findByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
});
