import { useState } from "react";

import type { AdminCatalogPort } from "../api/adminCatalogPort";
import {
  AdminCatalogError,
  type AdminCatalogPermissions,
} from "../domain/catalog";

function download(
  file: Awaited<ReturnType<AdminCatalogPort["exportCatalog"]>>,
) {
  const url = URL.createObjectURL(file.blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = file.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ExportPanel({
  port,
  permissions,
}: {
  port: AdminCatalogPort;
  permissions: AdminCatalogPermissions;
}) {
  const [format, setFormat] = useState<"json" | "csv">("json");
  const [status, setStatus] = useState<"published" | "all">("published");
  const [message, setMessage] = useState<string | null>(null);
  async function runExport() {
    setMessage(null);
    try {
      const file = await port.exportCatalog(
        format,
        status,
        permissions,
        new AbortController().signal,
      );
      download(file);
      setMessage(`Файл ${file.filename} подготовлен.`);
    } catch (error) {
      const message =
        error instanceof AdminCatalogError &&
        ["export_too_large", "unauthorized", "forbidden"].includes(error.code)
          ? error.message
          : "Не удалось подготовить экспорт.";
      setMessage(message);
    }
  }
  return (
    <section className="catalog-export" aria-labelledby="export-title">
      <h2 id="export-title">Экспорт каталога</h2>
      <label>
        Формат
        <select
          value={format}
          onChange={(event) => {
            setFormat(event.target.value as "json" | "csv");
          }}
        >
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
        </select>
      </label>
      <label>
        Данные
        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value as "published" | "all");
          }}
        >
          <option value="published">Только опубликованные</option>
          <option value="all">Все статусы</option>
        </select>
      </label>
      <button
        type="button"
        disabled={!permissions.export}
        onClick={() => {
          void runExport();
        }}
      >
        Скачать
      </button>
      {!permissions.export ? (
        <p>Для экспорта требуется permission catalog:export.</p>
      ) : null}
      {message ? (
        <p role="status" aria-live="polite">
          {message}
        </p>
      ) : null}
    </section>
  );
}
