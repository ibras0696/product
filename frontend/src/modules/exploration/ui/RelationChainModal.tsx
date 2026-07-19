import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type RefObject,
} from "react";

import {
  countTreeRelations,
  getRelationTree,
  type RelationTreeNode,
} from "../model/relationshipGraph";
import { GraphNodeIcon } from "./GraphNodeIcon";
import "./explorer-chain.css";

interface RelationChainModalProps {
  rootId: string;
  title: string;
  onClose: () => void;
  triggerRef: RefObject<HTMLButtonElement | null>;
}

const focusableSelector = [
  "button:not([disabled])",
  "[href]",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

function trapTabFocus(
  event: KeyboardEvent<HTMLElement>,
  dialog: HTMLElement | null,
) {
  const focusable = Array.from(
    dialog?.querySelectorAll<HTMLElement>(focusableSelector) ?? [],
  );
  const first = focusable[0];
  const last = focusable.at(-1);
  if (!last) return;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function ChainBranch({ node }: { node: RelationTreeNode }) {
  const [expanded, setExpanded] = useState(false);
  const hasChildren = node.children.length > 0;
  return (
    <li className={`hx-chain-item hx-kind-${node.kind}`}>
      <div className="hx-chain-row">
        <span className="hx-chain-icon" aria-hidden="true">
          <GraphNodeIcon kind={node.kind} />
        </span>
        <span className="hx-chain-label">
          <strong>{node.label}</strong>
          <small>{node.caption}</small>
        </span>
        {hasChildren ? (
          <button
            type="button"
            className="hx-chain-toggle"
            aria-expanded={expanded}
            onClick={() => {
              setExpanded((current) => !current);
            }}
          >
            {expanded ? "Свернуть" : `Связи (${String(node.children.length)})`}
          </button>
        ) : null}
      </div>
      {hasChildren && expanded ? (
        <ul className="hx-chain-children">
          {node.children.map((child) => (
            <ChainBranch key={child.id} node={child} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function RelationChainModal({
  rootId,
  title,
  onClose,
  triggerRef,
}: RelationChainModalProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const [tree] = useState(() => getRelationTree(rootId));

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const trigger = triggerRef.current;
    return () => {
      document.body.style.overflow = previousOverflow;
      trigger?.focus();
    };
  }, [triggerRef]);

  function handleKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    trapTabFocus(event, dialogRef.current);
  }

  const relationCount = countTreeRelations(tree);
  return (
    <div
      className="hx-chain-overlay"
      onPointerDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={dialogRef}
        className="hx-chain-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="chain-title"
        onKeyDown={handleKeyDown}
      >
        <header className="hx-chain-header">
          <div>
            <span>Цепочка связей</span>
            <h2 id="chain-title">{title}</h2>
            <p>{`Всего связанных объектов: ${String(relationCount)}`}</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose}>
            Закрыть
          </button>
        </header>
        {tree && tree.children.length > 0 ? (
          <ul className="hx-chain-root" aria-label={`Цепочка связей: ${title}`}>
            {tree.children.map((child) => (
              <ChainBranch key={child.id} node={child} />
            ))}
          </ul>
        ) : (
          <p className="hx-chain-empty" role="status">
            Для этого объекта пока нет подтверждённых связей.
          </p>
        )}
      </section>
    </div>
  );
}
