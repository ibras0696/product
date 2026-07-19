const workspaces = [
  ["Заявки", "/admin/submissions", "Открыть очередь модерации"],
  ["Каталог", "/admin/catalog/entities", "Редактировать сущности каталога"],
  ["Аудит", "/admin/audit", "Просмотреть журнал изменений"],
] as const;

export function AdminOverviewPage() {
  return (
    <>
      <section className="admin-hero">
        <span className="admin-eyebrow">Редакционный контур</span>
        <h1>Редакционное рабочее пространство</h1>
        <p>
          Очередь заявок, решения редакции, каталог и аудит собраны вокруг
          версий данных и явных разрешений.
        </p>
      </section>
      <nav className="admin-metric-grid" aria-label="Разделы редакции">
        {workspaces.map(([label, href, description]) => (
          <article key={label}>
            <span>{label}</span>
            <a href={href}>{description}</a>
          </article>
        ))}
      </nav>
    </>
  );
}
