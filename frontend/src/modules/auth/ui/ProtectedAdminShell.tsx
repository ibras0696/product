import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { StatePanel } from "@/shared/ui";

import { AuthApiError } from "../api/errors";
import { adminAccessForRoles } from "../model/adminAccess";
import { useAdminLogout, useAdminSession } from "../model/adminSession";
import "./admin.css";

const roleLabels = {
  moderator: "Модератор",
  editor: "Редактор",
  admin: "Администратор",
} as const;

function adminNavigation(roles: Parameters<typeof adminAccessForRoles>[0]) {
  const access = adminAccessForRoles(roles);
  return [
    { path: "/admin", label: "Обзор", visible: true },
    {
      path: "/admin/submissions",
      label: "Заявки",
      visible: access.moderation !== "none",
    },
    {
      path: "/admin/catalog/entities",
      label: "Сущности",
      visible: access.catalog.read,
    },
    { path: "/admin/audit", label: "Аудит", visible: access.catalog.auditRead },
  ].filter((item) => item.visible);
}

export function ProtectedAdminShell() {
  const session = useAdminSession();
  const logout = useAdminLogout();
  const location = useLocation();

  if (session.isPending) {
    return (
      <main className="app-state-page">
        <StatePanel
          live
          title="Проверяем сессию"
          description="Это займёт один момент."
        />
      </main>
    );
  }
  if (session.isError) {
    return (
      <AdminSessionError
        error={session.error}
        logoutPending={logout.isPending}
        onLogout={() => {
          logout.mutate();
        }}
        onRetry={() => void session.refetch()}
      />
    );
  }
  if (!session.data) {
    const returnTo = encodeURIComponent(
      `${location.pathname}${location.search}`,
    );
    return <Navigate to={`/admin/login?returnTo=${returnTo}`} replace />;
  }
  const navigation = adminNavigation(session.data.roles);

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <a className="admin-brand" href="/">
          Паутина истории
        </a>
        <nav aria-label="Разделы администратора">
          {navigation.map(({ path, label }) => (
            <NavLink key={path} to={path} end={path === "/admin"}>
              {label}
            </NavLink>
          ))}
        </nav>
        {logout.isError ? (
          <span className="admin-session-error" role="alert">
            Не удалось выйти. Попробуйте ещё раз.
          </span>
        ) : null}
        <button
          type="button"
          disabled={logout.isPending}
          onClick={() => {
            logout.mutate();
          }}
        >
          {logout.isPending ? "Выходим…" : "Выйти"}
        </button>
      </aside>
      <main className="admin-workspace">
        <header>
          <span>
            {session.data.roles.map((role) => roleLabels[role]).join(", ")}
          </span>
          <strong>{session.data.displayName}</strong>
        </header>
        <Outlet />
      </main>
    </div>
  );
}

interface AdminSessionErrorProps {
  error: Error;
  logoutPending: boolean;
  onLogout: () => void;
  onRetry: () => void;
}

function AdminSessionError({
  error,
  logoutPending,
  onLogout,
  onRetry,
}: AdminSessionErrorProps) {
  const forbidden = error instanceof AuthApiError && error.code === "forbidden";
  return (
    <main className="app-state-page">
      <StatePanel
        tone="danger"
        title={forbidden ? "Нет доступа" : "Не удалось проверить доступ"}
        description={
          forbidden
            ? "У текущего аккаунта нет административной роли."
            : "Повторите запрос. Если ошибка сохраняется, войдите заново."
        }
        action={
          <button
            type="button"
            disabled={forbidden && logoutPending}
            onClick={forbidden ? onLogout : onRetry}
          >
            {forbidden ? "Выйти" : "Повторить"}
          </button>
        }
      />
    </main>
  );
}
