"use client";
import { useEffect, useRef, useState } from "react";
export function ConfirmDialog({
  title,
  description,
  onConfirm,
  onClose,
}: {
  title: string;
  description: string;
  onConfirm: () => void | Promise<void>;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const target = dialog.current;
    const previous = document.activeElement as HTMLElement | null;
    target?.showModal();
    return () => {
      target?.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className="confirmation-dialog"
      aria-labelledby="confirmation-title"
      aria-describedby="confirmation-description"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <h2 id="confirmation-title">{title}</h2>
      <p id="confirmation-description">{description}</p>
      <div className="maintenance-actions">
        <button
          className="secondary-button"
          disabled={busy}
          onClick={onClose}
          autoFocus
        >
          Cancel
        </button>
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onConfirm();
            } finally {
              setBusy(false);
              onClose();
            }
          }}
        >
          {busy ? "Updating…" : "Confirm"}
        </button>
      </div>
    </dialog>
  );
}
