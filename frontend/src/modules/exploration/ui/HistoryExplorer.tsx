import type { ReactNode } from "react";

import {
  useHistoryExplorerScreen,
  type HistoryExplorerScreen,
} from "../routing/useHistoryExplorerScreen";
import { EntityCard } from "./EntityCard";
import { EntityDetailModal } from "./EntityDetailModal";
import { ExplorerHeader } from "./ExplorerHeader";
import { ExplorerSidebar } from "./ExplorerSidebar";
import { ExplorerSupportingContent } from "./ExplorerSupportingContent";
import { ExplorerTimeline } from "./ExplorerTimeline";
import { MapStage } from "./MapStage";
import { NetworkStage } from "./NetworkStage";
import "./explorer.css";
import "./explorer-card.css";
import "./explorer-controls.css";
import "./explorer-drawer.css";
import "./explorer-map.css";
import "./explorer-network.css";
import "./explorer-responsive.css";
import "./explorer-timeline.css";

interface HistoryExplorerProps {
  accountSlot?: ReactNode;
}

function mapStatus(screen: HistoryExplorerScreen) {
  if (screen.mapQuery.isPending) return "loading" as const;
  if (screen.mapQuery.isError) return "error" as const;
  return "ready" as const;
}

function networkStatus(screen: HistoryExplorerScreen) {
  if (!screen.selectedId) return mapStatus(screen);
  if (screen.selectedGraphQuery.isPending) return "loading" as const;
  if (screen.selectedGraphQuery.isError) return "error" as const;
  return "ready" as const;
}

function SelectedEntityCard({ screen }: { screen: HistoryExplorerScreen }) {
  const selected = screen.selectedEntity;
  if (!selected) return null;
  return (
    <>
      <p className="hx-visually-hidden" role="status">
        Открыта карточка: {selected.name}
      </p>
      <EntityCard
        key={selected.id}
        entity={selected}
        details={screen.selectedDetailsQuery.data}
        onOpenDetails={() => {
          screen.url.openModal(selected.id);
        }}
      />
    </>
  );
}

function ExplorerModal({ screen }: { screen: HistoryExplorerScreen }) {
  if (!screen.url.state.modalId) return null;
  if (screen.modalDetailsQuery.isPending) {
    return (
      <div className="hx-modal-overlay">
        <div className="hx-map-empty" role="status">
          Загружаем объект…
        </div>
      </div>
    );
  }
  if (screen.modalDetailsQuery.isError) {
    return (
      <div className="hx-modal-overlay">
        <div className="hx-map-empty" role="alert">
          <strong>Объект недоступен</strong>
          <button type="button" onClick={screen.url.closeModal}>
            Закрыть
          </button>
        </div>
      </div>
    );
  }
  return (
    <EntityDetailModal
      entity={screen.modalDetailsQuery.data}
      graph={screen.modalGraphQuery.data}
      sources={screen.modalSourcesQuery.data}
      media={screen.modalMediaQuery.data}
      graphPending={screen.modalGraphQuery.isPending}
      onOpenEntity={screen.url.openModal}
      onBack={screen.url.modalBack}
      onClose={screen.url.closeModal}
    />
  );
}

function ExplorerPrimaryStage({ screen }: { screen: HistoryExplorerScreen }) {
  if (screen.url.state.view === "network") {
    return (
      <NetworkStage
        graph={screen.selectedGraphQuery.data}
        selectedId={screen.selectedId}
        status={networkStatus(screen)}
        onOpenEntity={screen.url.selectEntity}
        onRetry={() => {
          const query = screen.selectedEntity
            ? screen.selectedGraphQuery
            : screen.mapQuery;
          void query.refetch();
        }}
        onReset={screen.url.resetFilters}
      />
    );
  }
  return (
    <MapStage
      entities={screen.entities}
      relations={screen.mapQuery.data?.relations ?? []}
      selectedId={screen.selectedId ?? ""}
      focusEntityId={screen.focusEntityId}
      view={screen.url.state.view}
      status={mapStatus(screen)}
      truncated={Boolean(screen.mapQuery.data?.truncated)}
      relationsTruncated={Boolean(screen.mapQuery.data?.relationsTruncated)}
      onSelect={screen.url.selectEntity}
      onRetry={() => void screen.mapQuery.refetch()}
      onReset={screen.url.resetFilters}
      onFocusRestored={screen.clearFocusRequest}
    />
  );
}

function ExplorerMapColumn({ screen }: { screen: HistoryExplorerScreen }) {
  return (
    <section className="hx-map-column" aria-label="Атлас Чечни">
      <ExplorerPrimaryStage screen={screen} />
      {screen.url.state.view === "timeline" ? (
        <ExplorerTimeline
          filters={{ ...screen.filters, query: screen.deferredQuery }}
          eventsEnabled={
            screen.url.state.types.length === 0 ||
            screen.url.state.types.includes("event")
          }
          onOpenEvent={screen.url.openModal}
        />
      ) : null}
      {screen.url.state.view !== "network" ? (
        <SelectedEntityCard screen={screen} />
      ) : null}
    </section>
  );
}

function ExplorerWorkspace({
  screen,
  accountSlot,
}: {
  screen: HistoryExplorerScreen;
  accountSlot?: ReactNode;
}) {
  return (
    <div className="hx-workspace" id="atlas-content">
      <ExplorerHeader
        accountSlot={accountSlot}
        query={screen.url.state.query}
        suggestions={screen.searchQuery.data?.items ?? []}
        searchPending={
          screen.searchQuery.isPending && screen.deferredQuery.length >= 2
        }
        onQueryChange={screen.url.setQuery}
        onSuggestionSelect={screen.url.openModal}
      />
      <div className="hx-body">
        <ExplorerSidebar
          activeTypes={screen.activeTypes}
          activeResearchStatuses={screen.activeResearchStatuses}
          activeView={screen.url.state.view}
          districtId={screen.url.state.districtId}
          periodId={screen.url.state.periodId}
          dateRange={{
            from: screen.filters.periodFrom ?? null,
            to: screen.filters.periodTo ?? null,
          }}
          options={screen.optionsQuery.data}
          onTypeToggle={screen.toggleType}
          onResearchStatusToggle={screen.toggleResearchStatus}
          onViewChange={screen.url.setView}
          onDistrictChange={screen.url.setDistrict}
          onDateRangeChange={screen.url.setDateRange}
          onReset={screen.url.resetFilters}
        />
        <ExplorerMapColumn screen={screen} />
      </div>
      {screen.selectedEntity ? (
        <ExplorerSupportingContent
          entity={screen.selectedEntity}
          details={screen.selectedDetailsQuery.data}
          graph={screen.selectedGraphQuery.data}
          graphPending={screen.selectedGraphQuery.isPending}
          graphError={screen.selectedGraphQuery.isError}
          onOpenEntity={screen.url.openModal}
        />
      ) : null}
      <ExplorerModal screen={screen} />
    </div>
  );
}

export function HistoryExplorer({ accountSlot }: HistoryExplorerProps) {
  const screen = useHistoryExplorerScreen();
  return (
    <main className="hx-shell" id="atlas">
      <a className="hx-skip-link" href="#atlas-content">
        К содержанию атласа
      </a>
      {!screen.online ? (
        <div className="hx-offline-banner" role="status">
          Нет сети: ранее загруженные данные могут оставаться доступными только
          для чтения.
        </div>
      ) : null}
      {screen.filterNotice ? (
        <div className="hx-filter-notice" role="status">
          {screen.filterNotice.message}
        </div>
      ) : null}
      <ExplorerWorkspace screen={screen} accountSlot={accountSlot} />
    </main>
  );
}
