import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TopicForm } from "./TopicForm";

describe("TopicForm", () => {
  it("cannot submit an empty topic", async () => {
    const onSubmit = vi.fn();
    render(<TopicForm running={false} onSubmit={onSubmit} />);

    expect(screen.getByRole("button")).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Research topic"), "   {Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits a trimmed topic on Enter", async () => {
    const onSubmit = vi.fn();
    render(<TopicForm running={false} onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText("Research topic"), "  mRNA vaccines  {Enter}");
    expect(onSubmit).toHaveBeenCalledWith("mRNA vaccines");
  });

  it("is disabled while a run is in flight", async () => {
    const onSubmit = vi.fn();
    render(<TopicForm running onSubmit={onSubmit} />);

    expect(screen.getByLabelText("Research topic")).toBeDisabled();
    expect(screen.getByRole("button")).toHaveTextContent("Researching…");
  });
});
