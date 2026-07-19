interface PanelTabsProps {
  label: string;
  tabs: readonly string[];
  activeTab: string;
  onChange: (tab: string) => void;
}

export function PanelTabs({
  label,
  tabs,
  activeTab,
  onChange,
}: PanelTabsProps) {
  return (
    <div className="hx-panel-tabs" role="group" aria-label={label}>
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          aria-pressed={tab === activeTab}
          onClick={() => {
            onChange(tab);
          }}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

export function PanelPlaceholder({ tab }: { tab: string }) {
  return (
    <div className="hx-panel-placeholder" role="status">
      <strong>{tab}</strong>
      <span>Раздел готов к подключению опубликованных данных.</span>
    </div>
  );
}
