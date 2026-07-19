import type { AdminCatalogPort } from "../api/adminCatalogPort";
import {
  AdminCatalogError,
  type AdminCatalogPermissions,
} from "../domain/catalog";
import { useAudit } from "../model/catalogQueries";

export function AuditView({
  port,
  permissions,
}: {
  port: AdminCatalogPort;
  permissions: AdminCatalogPermissions;
}) {
  const query = useAudit(port, permissions);
  if (!permissions.auditRead)
    return <p>Для просмотра аудита требуется permission audit:read.</p>;
  if (query.isPending) return <p role="status">Загружаем аудит…</p>;
  if (
    query.error instanceof AdminCatalogError &&
    query.error.code === "unauthorized"
  )
    return <p role="alert">Сессия завершилась. Войдите снова.</p>;
  if (
    query.error instanceof AdminCatalogError &&
    query.error.code === "forbidden"
  )
    return <p role="alert">Недостаточно прав для просмотра аудита.</p>;
  if (query.isError) return <p role="alert">Аудит временно недоступен.</p>;
  return (
    <section className="catalog-audit" aria-labelledby="audit-title">
      <div className="catalog-heading">
        <h2 id="audit-title">Последние изменения</h2>
        <span>{query.data.meta.total}</span>
      </div>
      {query.data.items.length === 0 ? (
        <p>Изменений пока нет.</p>
      ) : (
        <ol>
          {query.data.items.map((item) => (
            <li key={item.id}>
              <strong>{item.action}</strong>
              <span>
                {item.resourceType}: {item.resourceId}, версия{" "}
                {item.resourceVersion}
              </span>
              <time dateTime={item.createdAt}>
                {new Date(item.createdAt).toLocaleString("ru-RU")}
              </time>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
