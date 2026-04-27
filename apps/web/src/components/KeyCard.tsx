import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, IssuedKey, KeyInfo } from "../api/client";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("ko-KR");
}

export default function KeyCard() {
  const qc = useQueryClient();
  const { data: key, isLoading } = useQuery<KeyInfo | null>({
    queryKey: ["key"],
    queryFn: async () => (await api.get("/api/keys")).data,
  });

  const [issued, setIssued] = useState<IssuedKey | null>(null);
  const [confirmRotate, setConfirmRotate] = useState(false);

  const issue = useMutation({
    mutationFn: async () => (await api.post<IssuedKey>("/api/keys")).data,
    onSuccess: (d) => {
      setIssued(d);
      qc.invalidateQueries({ queryKey: ["key"] });
    },
  });
  const rotate = useMutation({
    mutationFn: async () => (await api.post<IssuedKey>("/api/keys/rotate")).data,
    onSuccess: (d) => {
      setIssued(d);
      setConfirmRotate(false);
      qc.invalidateQueries({ queryKey: ["key"] });
    },
  });
  const extend = useMutation({
    mutationFn: async () => (await api.post("/api/keys/extend")).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["key"] }),
  });
  const remove = useMutation({
    mutationFn: async () => api.delete("/api/keys"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["key"] }),
  });

  if (isLoading) return <div className="card">불러오는 중...</div>;

  return (
    <div className="card">
      <h2>API Key</h2>
      {!key ? (
        <div className="spaced">
          <span className="muted">아직 발급된 키가 없습니다.</span>
          <button onClick={() => issue.mutate()} disabled={issue.isPending}>
            발급
          </button>
        </div>
      ) : (
        <>
          <div className="spaced" style={{ marginBottom: 12 }}>
            <span className="mono">{key.prefix}••••••••</span>
            <span className="muted">만료: {formatDate(key.expires_at)}</span>
          </div>
          <div className="row">
            <button className="secondary" onClick={() => extend.mutate()} disabled={extend.isPending}>
              연장
            </button>
            <button className="secondary" onClick={() => setConfirmRotate(true)}>
              재발급
            </button>
            <button
              className="danger"
              onClick={() => {
                if (confirm("정말 삭제하시겠습니까? 키 사용 중인 클라이언트는 즉시 401을 받습니다.")) {
                  remove.mutate();
                }
              }}
            >
              삭제
            </button>
          </div>
        </>
      )}

      {issued && <IssuedModal value={issued} onClose={() => setIssued(null)} />}

      {confirmRotate && (
        <div className="modal-bg" onClick={() => setConfirmRotate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>키를 재발급할까요?</h2>
            <p className="warn">기존 키는 즉시 무효화됩니다.</p>
            <div className="row" style={{ marginTop: 16, justifyContent: "flex-end" }}>
              <button className="secondary" onClick={() => setConfirmRotate(false)}>
                취소
              </button>
              <button onClick={() => rotate.mutate()} disabled={rotate.isPending}>
                재발급
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function IssuedModal({ value, onClose }: { value: IssuedKey; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>새 API Key</h2>
        <p className="warn">이 키는 지금 한 번만 표시됩니다. 안전한 곳에 저장하세요.</p>
        <pre
          className="mono"
          style={{ wordBreak: "break-all", whiteSpace: "pre-wrap", padding: 12 }}
        >
          {value.api_key}
        </pre>
        <div className="row" style={{ justifyContent: "flex-end", marginTop: 16 }}>
          <button
            className="secondary"
            onClick={() => {
              navigator.clipboard.writeText(value.api_key).then(() => setCopied(true));
            }}
          >
            {copied ? "복사됨" : "복사"}
          </button>
          <button onClick={onClose}>닫기</button>
        </div>
      </div>
    </div>
  );
}
