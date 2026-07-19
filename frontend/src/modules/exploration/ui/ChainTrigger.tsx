import { useRef, useState } from "react";

import { RelationChainModal } from "./RelationChainModal";

interface ChainTriggerProps {
  rootId: string;
  title: string;
}

export function ChainTrigger({ rootId, title }: ChainTriggerProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        className="hx-secondary-button hx-chain-trigger"
        onClick={() => {
          setOpen(true);
        }}
      >
        Смотреть всю цепочку
      </button>
      {open ? (
        <RelationChainModal
          rootId={rootId}
          title={title}
          triggerRef={triggerRef}
          onClose={() => {
            setOpen(false);
          }}
        />
      ) : null}
    </>
  );
}
