import {
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  adminAccessForRoles,
  AdminLoginPage,
  AdminOverviewPage,
  ProtectedAdminShell,
  useAdminSession,
} from "@/modules/auth";
import { adminCatalogApi, AdminCatalogPage } from "@/modules/admin-catalog";
import { EntityDetailsPage, SourceDetailsPage } from "@/modules/entities";
import { HistoryExplorer } from "@/modules/exploration";
import { ContributionWizardPage, submissionsApi } from "@/modules/submissions";
import {
  ModerationWorkspace,
  moderationApi,
  parseModerationFilters,
  toModerationSearchParams,
  type ModerationFilters,
} from "@/modules/moderation";
import { StatePanel } from "@/shared/ui";

function NotFoundPage() {
  return (
    <main className="app-state-page">
      <StatePanel
        title="Страница не найдена"
        description="Адрес мог измениться. Основная карта истории доступна по ссылке ниже."
        action={<a href="/">Открыть карту</a>}
      />
    </main>
  );
}

function EntityRoute() {
  const { entityId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const hasAtlasOrigin = Boolean(
    location.state &&
    typeof location.state === "object" &&
    "from" in location.state,
  );
  return (
    <EntityDetailsPage
      entityId={entityId ?? ""}
      onBack={() => {
        if (hasAtlasOrigin) void navigate(-1);
        else void navigate("/", { replace: true });
      }}
    />
  );
}

function SourceRoute() {
  const { entityId, sourceId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const hasEntityOrigin = Boolean(
    location.state &&
    typeof location.state === "object" &&
    "fromEntity" in location.state,
  );
  return (
    <SourceDetailsPage
      entityId={entityId ?? ""}
      sourceId={sourceId ?? ""}
      onBack={() => {
        if (hasEntityOrigin) void navigate(-1);
        else void navigate(`/entities/${entityId ?? ""}`, { replace: true });
      }}
    />
  );
}

function ContributionRoute() {
  return (
    <ContributionWizardPage
      port={submissionsApi}
      entities={[]}
      settlements={[]}
    />
  );
}

function AdminCatalogRoute() {
  const session = useAdminSession();
  const permissions = adminAccessForRoles(session.data?.roles ?? []).catalog;
  return <AdminCatalogPage port={adminCatalogApi} permissions={permissions} />;
}

function ModerationRoute() {
  const session = useAdminSession();
  const access = adminAccessForRoles(session.data?.roles ?? []);
  const [params, setParams] = useSearchParams();
  const filters = parseModerationFilters(params);
  const selectedId = params.get("submission");

  function changeFilters(nextFilters: ModerationFilters) {
    const next = toModerationSearchParams(nextFilters);
    if (selectedId) next.set("submission", selectedId);
    setParams(next, { replace: true });
  }

  if (access.moderation === "none") {
    return (
      <StatePanel
        title="Модерация недоступна"
        description="Для очереди заявок требуется роль moderator или admin. Backend всё равно проверяет разрешение на каждом запросе."
      />
    );
  }

  return (
    <ModerationWorkspace
      port={moderationApi}
      filters={filters}
      selectedSubmissionId={selectedId}
      onFiltersChange={changeFilters}
      onSelectSubmission={(id) => {
        setParams((current) => {
          const next = new URLSearchParams(current);
          next.set("submission", id);
          return next;
        });
      }}
    />
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<HistoryExplorer />} />
      <Route
        path="/entities/:entityId/sources/:sourceId"
        element={<SourceRoute />}
      />
      <Route path="/entities/:entityId" element={<EntityRoute />} />
      <Route path="/contribute" element={<ContributionRoute />} />
      <Route path="/admin/login" element={<AdminLoginPage />} />
      <Route path="/admin" element={<ProtectedAdminShell />}>
        <Route index element={<AdminOverviewPage />} />
        <Route path="submissions" element={<ModerationRoute />} />
        <Route path="catalog/entities" element={<AdminCatalogRoute />} />
        <Route path="audit" element={<AdminCatalogRoute />} />
        <Route path="*" element={<AdminOverviewPage />} />
      </Route>
      <Route path="/atlas" element={<Navigate to="/" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
