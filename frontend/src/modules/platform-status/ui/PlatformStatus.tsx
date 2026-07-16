import { usePlatformStatus } from "../model/usePlatformStatus";

const labels = {
  loading: "Проверяем сервисы…",
  ready: "Все базовые сервисы доступны",
  error: "Часть сервисов пока недоступна",
} as const;

export function PlatformStatus() {
  const state = usePlatformStatus();
  return (
    <div className="status-card" role="status" aria-live="polite">
      <span className={`status-dot ${state}`} aria-hidden="true" />
      <span className="status-label">{labels[state]}</span>
    </div>
  );
}
