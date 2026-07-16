import { useState } from "react";

import type { AuthFormValues } from "../model/authSchema";
import { useLogin, useRegister } from "../model/useAuth";
import { AuthForm } from "./AuthForm";

interface AuthDialogProps {
  onClose: () => void;
}

export function AuthDialog({ onClose }: AuthDialogProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const login = useLogin();
  const register = useRegister();
  const active = mode === "login" ? login : register;

  function submit(values: AuthFormValues) {
    active.mutate(values, { onSuccess: onClose });
  }

  function changeMode(nextMode: "login" | "register") {
    login.reset();
    register.reset();
    setMode(nextMode);
  }

  return (
    <div
      className="auth-scrim"
      role="presentation"
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className="auth-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-dialog-title"
      >
        <button
          className="auth-close"
          type="button"
          aria-label="Закрыть"
          autoFocus
          onClick={onClose}
        >
          ×
        </button>
        <div
          className="auth-tabs"
          role="tablist"
          aria-label="Режим авторизации"
        >
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            onClick={() => {
              changeMode("login");
            }}
          >
            Вход
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            onClick={() => {
              changeMode("register");
            }}
          >
            Регистрация
          </button>
        </div>
        <AuthForm
          mode={mode}
          isPending={active.isPending}
          error={active.error}
          onSubmit={submit}
        />
      </section>
    </div>
  );
}
