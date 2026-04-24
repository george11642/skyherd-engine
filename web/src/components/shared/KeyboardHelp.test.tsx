import { describe, it, expect } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import { KeyboardHelp } from "./KeyboardHelp";

describe("KeyboardHelp", () => {
  it("renders the floating open button by default", () => {
    const { queryByTestId } = render(<KeyboardHelp />);
    expect(queryByTestId("keyboard-help-open")).toBeTruthy();
    expect(queryByTestId("keyboard-help-dialog")).toBeFalsy();
  });

  it("opens dialog on '?' keypress", () => {
    const { queryByTestId } = render(<KeyboardHelp />);
    act(() => {
      fireEvent.keyDown(window, { key: "?" });
    });
    expect(queryByTestId("keyboard-help-dialog")).toBeTruthy();
  });

  it("does NOT open '?' when focus is in a text input", () => {
    const { queryByTestId } = render(
      <div>
        <input data-testid="inp" type="text" />
        <KeyboardHelp />
      </div>,
    );
    const input = queryByTestId("inp")!;
    input.focus();
    act(() => {
      fireEvent.keyDown(input, { key: "?" });
    });
    expect(queryByTestId("keyboard-help-dialog")).toBeFalsy();
  });

  it("closes on Esc", () => {
    const { queryByTestId } = render(<KeyboardHelp />);
    act(() => {
      fireEvent.keyDown(window, { key: "?" });
    });
    expect(queryByTestId("keyboard-help-dialog")).toBeTruthy();
    act(() => {
      fireEvent.keyDown(window, { key: "Escape" });
    });
    expect(queryByTestId("keyboard-help-dialog")).toBeFalsy();
  });

  it("closes when close button is clicked", () => {
    const { queryByTestId } = render(<KeyboardHelp />);
    act(() => {
      fireEvent.keyDown(window, { key: "?" });
    });
    const close = queryByTestId("keyboard-help-close")!;
    fireEvent.click(close);
    expect(queryByTestId("keyboard-help-dialog")).toBeFalsy();
  });

  it("closes when backdrop is clicked", () => {
    const { queryByTestId } = render(<KeyboardHelp />);
    act(() => {
      fireEvent.keyDown(window, { key: "?" });
    });
    const dialog = queryByTestId("keyboard-help-dialog")!;
    fireEvent.click(dialog);
    expect(queryByTestId("keyboard-help-dialog")).toBeFalsy();
  });

  it("does NOT close when inner dialog body is clicked", () => {
    const { queryByTestId } = render(<KeyboardHelp />);
    act(() => {
      fireEvent.keyDown(window, { key: "?" });
    });
    const closeBtn = queryByTestId("keyboard-help-close")!;
    // clicking a child (not the backdrop) should NOT close
    const parent = closeBtn.parentElement!.parentElement!; // dialog body
    fireEvent.click(parent);
    expect(queryByTestId("keyboard-help-dialog")).toBeTruthy();
  });

  it("open button toggles the dialog", () => {
    const { queryByTestId } = render(<KeyboardHelp />);
    const openBtn = queryByTestId("keyboard-help-open")!;
    fireEvent.click(openBtn);
    expect(queryByTestId("keyboard-help-dialog")).toBeTruthy();
  });

  it("lists at least one shortcut per known category", () => {
    const { queryByTestId } = render(<KeyboardHelp />);
    act(() => {
      fireEvent.keyDown(window, { key: "?" });
    });
    const dialog = queryByTestId("keyboard-help-dialog")!;
    expect(dialog.textContent).toContain("Help");
    expect(dialog.textContent).toContain("Navigation");
  });
});
