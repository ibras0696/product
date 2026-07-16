import { useState } from "react";

import { useCurrentAccount, useLogout } from "../model/useAuth";
import { AuthDialog } from "./AuthDialog";
import "./auth.css";

export function AuthControls() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const account = useCurrentAccount();
  const logout = useLogout();

  if (account.isPending) {
    return (
      <span className="auth-loading" role="status">
        Сессия…
      </span>
    );
  }

  if (account.isError) {
    return (
      <button
        className="auth-retry"
        type="button"
        onClick={() => {
          void account.refetch();
        }}
      >
        Повторить вход
      </button>
    );
  }

  if (account.data) {
    return (
      <div className="auth-account">
        <span title={account.data.email}>{account.data.email}</span>
        <button
          type="button"
          onClick={() => {
            logout.mutate();
          }}
          disabled={logout.isPending}
        >
          {logout.isPending ? "Выходим…" : "Выйти"}
        </button>
        {logout.isError ? (
          <span className="auth-inline-error" role="alert">
            Не удалось выйти
          </span>
        ) : null}
      </div>
    );
  }

  return (
    <>
      <button
        className="auth-trigger"
        type="button"
        onClick={() => {
          setDialogOpen(true);
        }}
      >
        Войти
      </button>
      {dialogOpen ? (
        <AuthDialog
          onClose={() => {
            setDialogOpen(false);
          }}
        />
      ) : null}
    </>
  );
}
