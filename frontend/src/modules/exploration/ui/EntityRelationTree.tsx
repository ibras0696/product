import { MinusIcon, PlusIcon } from "@phosphor-icons/react";
import { useState } from "react";

import type { GraphViewModel } from "../api/viewModels";
import { buildRelationTree, type RelationBranch } from "../model/relationTree";
import { RelationEvidence } from "./RelationEvidence";

interface EntityRelationTreeProps {
  graph?: GraphViewModel;
  pending: boolean;
  onOpen: (id: string) => void;
}

function SecondLevelRelations({
  children,
  onOpen,
}: {
  children: RelationBranch[];
  onOpen: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  if (children.length === 0) return null;
  return (
    <div className="hx-mini-star">
      {children.map((child) => (
        <div key={child.edgeId}>
          <button
            type="button"
            onClick={() => {
              onOpen(child.entityId);
            }}
          >
            <span>{child.title}</span>
            <small>{child.relationTitle}</small>
          </button>
          <button
            className="hx-relation-expand"
            type="button"
            aria-expanded={expanded === child.edgeId}
            aria-label={`${expanded === child.edgeId ? "Скрыть" : "Показать"} источник связи второго уровня: ${child.title}`}
            onClick={() => {
              setExpanded((current) =>
                current === child.edgeId ? null : child.edgeId,
              );
            }}
          >
            {expanded === child.edgeId ? (
              <MinusIcon size={16} />
            ) : (
              <PlusIcon size={16} />
            )}
          </button>
          {expanded === child.edgeId ? (
            <RelationEvidence relationId={child.edgeId} />
          ) : null}
        </div>
      ))}
    </div>
  );
}

export function EntityRelationTree({
  graph,
  pending,
  onOpen,
}: EntityRelationTreeProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  if (pending) return <p role="status">Строим паутину связей…</p>;
  if (!graph || graph.edges.length === 0) {
    return <p>У объекта пока нет опубликованных связей.</p>;
  }
  const branches = buildRelationTree(graph);
  return (
    <section className="hx-modal-relations" aria-labelledby="modal-relations">
      <RelationHeading />
      <div className="hx-relation-star">
        <strong className="hx-relation-root">{graph.center.title.ru}</strong>
        <ul>
          {branches.map((branch) => {
            const open = expanded === branch.edgeId;
            return (
              <li key={branch.edgeId}>
                <div className="hx-relation-action">
                  <button
                    className="hx-relation-node"
                    type="button"
                    onClick={() => {
                      onOpen(branch.entityId);
                    }}
                  >
                    <span>
                      <strong>{branch.title}</strong>
                      <small>{branch.relationTitle}</small>
                    </span>
                  </button>
                  <button
                    className="hx-relation-expand"
                    type="button"
                    aria-expanded={open}
                    aria-label={`${open ? "Скрыть" : "Показать"} подтверждение связи`}
                    onClick={() => {
                      setExpanded(open ? null : branch.edgeId);
                    }}
                  >
                    {open ? <MinusIcon size={16} /> : <PlusIcon size={16} />}
                  </button>
                </div>
                {open ? (
                  <>
                    <RelationEvidence relationId={branch.edgeId} />
                    <SecondLevelRelations
                      children={branch.children}
                      onOpen={onOpen}
                    />
                  </>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

function RelationHeading() {
  return (
    <header>
      <div>
        <span>Древо подтверждённых связей</span>
        <h3 id="modal-relations">Паутина объекта</h3>
      </div>
    </header>
  );
}
