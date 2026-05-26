import { useState } from "react";

export interface Session {
  id: string;
  title: string;
  createdAt: number;
}

interface SessionListProps {
  sessions: Session[];
  activeSessionId: string;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onCreate: () => void;
}

export default function SessionList({ sessions, activeSessionId, onSelect, onDelete, onCreate }: SessionListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  return (
    <div style={{ width: 240, borderRight: "1px solid #eef0f3", background: "#fafbfc", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "16px", borderBottom: "1px solid #eef0f3" }}>
        <button
          onClick={onCreate}
          style={{ width: "100%", padding: "8px", background: "#1a1d21", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontSize: "13px" }}
        >
          + 새 세션
        </button>
      </div>
      <div style={{ flex: 1, overflowY: "auto" }}>
        {sessions.map((session) => (
          <div
            key={session.id}
            onClick={() => onSelect(session.id)}
            style={{
              padding: "10px 16px",
              cursor: "pointer",
              background: session.id === activeSessionId ? "#e8eaed" : "transparent",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderBottom: "1px solid #f0f1f3",
            }}
          >
            <span style={{ fontSize: "13px", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {session.title}
            </span>
            {deletingId === session.id ? (
              <div style={{ display: "flex", gap: 4 }}>
                <button
                  className="danger"
                  onClick={() => { onDelete(session.id); setDeletingId(null); }}
                  style={{ fontSize: "11px", padding: "2px 6px" }}
                >
                  예
                </button>
                <button className="secondary" onClick={() => setDeletingId(null)} style={{ fontSize: "11px", padding: "2px 6px" }}>
                  아니오
                </button>
              </div>
            ) : (
              <button
                className="secondary"
                onClick={() => setDeletingId(session.id)}
                style={{ fontSize: "11px", padding: "2px 6px", opacity: 0.5 }}
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
