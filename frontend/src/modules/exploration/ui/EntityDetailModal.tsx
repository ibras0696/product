import { ArrowLeftIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useRef, type KeyboardEvent, type RefObject } from "react";

import type {
  CatalogEntityType,
  EntityDetailsViewModel,
  GraphViewModel,
  MediaPageViewModel,
  SourcePageViewModel,
} from "../api/viewModels";
import { NetworkCanvas, NetworkLegend } from "./NetworkCanvas";
import "./explorer-modal.css";

interface Props {
  entity: EntityDetailsViewModel;
  graph?: GraphViewModel;
  sources?: SourcePageViewModel;
  media?: MediaPageViewModel;
  graphPending: boolean;
  onOpenEntity: (id: string) => void;
  onBack: () => void;
  onClose: () => void;
}

const focusableSelector =
  'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])';

const entityTypeLabels: Record<CatalogEntityType, string> = {
  settlement: "Населённый пункт",
  person: "Личность",
  event: "Событие",
  landmark: "Достопримечательность",
  natural_object: "Природный объект",
  cultural_object: "Культурный объект",
  organization: "Организация",
  university_object: "Объект университета",
  artifact: "Артефакт",
};

const sourceTypeLabels: Record<
  SourcePageViewModel["items"][number]["type"],
  string
> = {
  archive_document: "Архивный документ",
  book: "Книга",
  scientific_article: "Научная статья",
  museum_material: "Музейный материал",
  official_publication: "Официальная публикация",
  photo: "Фотография",
  audio: "Аудиозапись",
  video: "Видеозапись",
  oral_testimony: "Устное свидетельство",
  web_resource: "Веб-ресурс",
};

function trapFocus(event: KeyboardEvent<HTMLElement>, dialog: HTMLElement) {
  if (event.key !== "Tab") return;
  const focusable = [
    ...dialog.querySelectorAll<HTMLElement>(focusableSelector),
  ];
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable.at(-1) ?? first;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  }
  if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function Materials({
  graph,
  media,
  onOpen,
}: {
  graph?: GraphViewModel;
  media?: MediaPageViewModel;
  onOpen: (id: string) => void;
}) {
  const nodes = graph?.nodes.slice(0, 4) ?? [];
  return (
    <section className="hx-modal-materials" aria-labelledby="modal-materials">
      <h3 id="modal-materials">Связанные материалы</h3>
      <div>
        {nodes.map((node, index) => (
          <button
            type="button"
            key={node.id}
            onClick={() => {
              onOpen(node.id);
            }}
          >
            {media?.items[index]?.preview_url ? (
              <img
                src={media.items[index].preview_url}
                alt=""
                width="320"
                height="180"
                loading="lazy"
              />
            ) : null}
            <span>{entityTypeLabels[node.type]}</span>
            <strong>{node.title.ru}</strong>
            <small>{node.relations_count} связей</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function ModalHeader({
  backRef,
  onBack,
  onClose,
}: {
  backRef: RefObject<HTMLButtonElement | null>;
  onBack: () => void;
  onClose: () => void;
}) {
  return (
    <header className="hx-modal-header">
      <button ref={backRef} type="button" onClick={onBack}>
        <ArrowLeftIcon size={18} />
        Назад
      </button>
      <button type="button" aria-label="Закрыть карточку" onClick={onClose}>
        <XIcon size={20} />
      </button>
    </header>
  );
}

function ModalSummary({ entity }: { entity: EntityDetailsViewModel }) {
  const shortText = entity.short_description.ru.trim();
  const fullText = entity.full_description.ru.trim();
  const hasDistinctFullText =
    fullText.localeCompare(shortText, "ru", { sensitivity: "base" }) !== 0;
  return (
    <section className="hx-modal-summary">
      <div>
        <span>{entityTypeLabels[entity.type]}</span>
        <h2 id="modal-title">{entity.title.ru}</h2>
        <strong>{entity.short_description.ru}</strong>
        {hasDistinctFullText ? <p>{fullText}</p> : null}
      </div>
      {entity.cover_url ? (
        <img
          src={entity.cover_url}
          alt={`Исторический вид: ${entity.title.ru}`}
          width="720"
          height="405"
        />
      ) : null}
    </section>
  );
}

function Sources({ sources }: { sources?: SourcePageViewModel }) {
  if (!sources?.items.length) return null;
  return (
    <section className="hx-modal-sources">
      <h3>Источники ({sources.meta.total})</h3>
      <ul>
        {sources.items.map((source) => {
          const photoUrl =
            source.type === "photo" &&
            source.archive_reference?.startsWith("http")
              ? source.archive_reference
              : source.url;
          const displayTitle = source.title
            .replace(/^File:/i, "")
            .replace(/\.(?:jpe?g|png|webp|gif|tiff?)$/i, "")
            .replaceAll("_", " ");
          const title = (
            <>
              <small>{sourceTypeLabels[source.type]}</small>
              <strong>{displayTitle}</strong>
            </>
          );
          return (
            <li
              className={source.type === "photo" ? "is-photo" : undefined}
              key={source.id}
            >
              {source.type === "photo" && photoUrl ? (
                <a
                  href={source.url ?? photoUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  <img
                    src={photoUrl}
                    alt={displayTitle}
                    width="480"
                    height="320"
                    loading="lazy"
                  />
                  {title}
                </a>
              ) : source.url ? (
                <a href={source.url} target="_blank" rel="noreferrer">
                  {title}
                </a>
              ) : (
                title
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ModalNetwork({
  graph,
  pending,
  onOpen,
}: {
  graph?: GraphViewModel;
  pending: boolean;
  onOpen: (id: string) => void;
}) {
  if (pending) return <p role="status">Строим паутину связей...</p>;
  if (!graph) return <p role="alert">Связи объекта временно недоступны.</p>;
  const empty = graph.edges.length === 0;
  return (
    <section className="hx-modal-network" aria-labelledby="modal-network">
      <header>
        <span>Глубина связей: 2</span>
        <h3 id="modal-network">Паутина объекта</h3>
      </header>
      {empty ? null : <NetworkLegend graph={graph} />}
      <NetworkCanvas graph={graph} onOpenEntity={onOpen} />
      {empty ? (
        <p className="hx-modal-network-empty">
          Для этого объекта пока нет опубликованных связей. Центральный объект
          остаётся на схеме.
        </p>
      ) : null}
    </section>
  );
}

export function EntityDetailModal(props: Props) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const trigger =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    return () => {
      document.body.style.overflow = previous;
      trigger?.focus();
    };
  }, []);
  const open = (id: string) => {
    if (id !== props.entity.id) props.onOpenEntity(id);
  };
  return (
    <div
      className="hx-modal-overlay"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) props.onClose();
      }}
    >
      <section
        ref={dialogRef}
        className="hx-entity-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        onKeyDown={(event) => {
          if (event.key === "Escape") props.onClose();
          else if (dialogRef.current) trapFocus(event, dialogRef.current);
        }}
      >
        <ModalHeader
          backRef={closeRef}
          onBack={props.onBack}
          onClose={props.onClose}
        />
        <nav className="hx-modal-breadcrumb" aria-label="Путь по объектам">
          <span>{props.entity.title.ru}</span>
        </nav>
        <div className="hx-modal-content">
          <ModalSummary entity={props.entity} />
          <Materials graph={props.graph} media={props.media} onOpen={open} />
          <ModalNetwork
            graph={props.graph}
            pending={props.graphPending}
            onOpen={open}
          />
          <Sources sources={props.sources} />
        </div>
      </section>
    </div>
  );
}
