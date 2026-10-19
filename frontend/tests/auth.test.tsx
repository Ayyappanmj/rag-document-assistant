import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AuthModal } from "@/components/auth/AuthModal";

describe("AuthModal", () => {
  it("renders sign in modal by default", () => {
    render(
      <AuthModal
        open={true}
        onClose={vi.fn()}
        onLogin={vi.fn()}
        onRegister={vi.fn()}
      />
    );

    expect(screen.getByRole("heading", { name: /Sign In/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
  });

  it("toggles between sign in and sign up", async () => {
    const user = userEvent.setup();
    render(
      <AuthModal
        open={true}
        onClose={vi.fn()}
        onLogin={vi.fn()}
        onRegister={vi.fn()}
      />
    );

    const toggleBtn = screen.getByText(/Need an account\? Sign Up/i);
    await user.click(toggleBtn);

    expect(screen.getByRole("heading", { name: /Create an Account/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign Up" })).toBeInTheDocument();
  });

  it("calls onLogin when submitted in sign in mode", async () => {
    const user = userEvent.setup();
    const handleLogin = vi.fn().mockResolvedValue({ id: "1" });
    const handleClose = vi.fn();

    render(
      <AuthModal
        open={true}
        onClose={handleClose}
        onLogin={handleLogin}
        onRegister={vi.fn()}
      />
    );

    await user.type(screen.getByLabelText(/Email Address/i), "test@example.com");
    await user.type(screen.getByLabelText(/Password/i), "secret123");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(handleLogin).toHaveBeenCalledWith("test@example.com", "secret123");
      expect(handleClose).toHaveBeenCalled();
    });
  });

  it("displays error message when login fails", async () => {
    const user = userEvent.setup();
    const handleLogin = vi.fn().mockRejectedValue(new Error("Invalid email or password"));

    render(
      <AuthModal
        open={true}
        onClose={vi.fn()}
        onLogin={handleLogin}
        onRegister={vi.fn()}
      />
    );

    await user.type(screen.getByLabelText(/Email Address/i), "bad@example.com");
    await user.type(screen.getByLabelText(/Password/i), "wrongpass");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password");
    });
  });
});
