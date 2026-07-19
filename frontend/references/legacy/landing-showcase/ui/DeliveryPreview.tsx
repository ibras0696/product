import { PlatformStatus } from "@/modules/platform-status";

const stages = [
  { label: "Проблема", value: "сформулирована" },
  { label: "MVP", value: "ограничен" },
  { label: "Проверка", value: "запланирована" },
] as const;

export function DeliveryPreview() {
  return (
    <aside
      className="delivery-preview"
      aria-label="Демонстрационный план запуска"
    >
      <div className="preview-heading">
        <span>Демо-данные</span>
        <strong>Спринт продукта</strong>
      </div>
      <div className="preview-stages">
        {stages.map((stage) => (
          <div className="preview-stage" key={stage.label}>
            <span>{stage.label}</span>
            <strong>{stage.value}</strong>
          </div>
        ))}
      </div>
      <PlatformStatus />
    </aside>
  );
}
