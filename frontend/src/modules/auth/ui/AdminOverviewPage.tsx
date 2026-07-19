import { Link } from "react-router-dom";

const workspaces = [
  {
    label: "Заявки",
    href: "/admin/submissions",
    description: "Проверка и публикация материалов",
  },
  {
    label: "Каталог",
    href: "/admin/catalog/entities",
    description: "Сущности, связи и источники",
  },
  {
    label: "Аудит",
    href: "/admin/audit",
    description: "История редакционных изменений",
  },
] as const;

export function AdminOverviewPage() {
  return (
    <div className="admin-overview">
      <section className="admin-hero">
        <span className="admin-eyebrow">Редакционный контур</span>
        <h1>Рабочее пространство редакции</h1>
        <p>
          Управляйте материалами, связями и версиями данных из одного места.
        </p>
      </section>
      <nav className="admin-metric-grid" aria-label="Разделы редакции">
        {workspaces.map(({ label, href, description }, index) => (
          <Link className="admin-workspace-card" key={label} to={href}>
            <span className="admin-workspace-index">
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className="admin-workspace-copy">
              <strong>{label}</strong>
              <small>{description}</small>
            </span>
            <span className="admin-workspace-arrow" aria-hidden="true">
              →
            </span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
