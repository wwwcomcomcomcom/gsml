import { useQuery } from "@tanstack/react-query";
import { api, UsageHistoryItem, UsageToday } from "../api/client";

export default function UsageCard() {
  const today = useQuery<UsageToday>({
    queryKey: ["usage-today"],
    queryFn: async () => (await api.get("/api/usage/today")).data,
  });
  const history = useQuery<UsageHistoryItem[]>({
    queryKey: ["usage-history"],
    queryFn: async () => (await api.get("/api/usage/history?days=7")).data,
  });

  if (today.isLoading) return <div className="card">불러오는 중...</div>;
  const t = today.data!;
  const pct = t.limit > 0 ? Math.min(100, (t.used / t.limit) * 100) : 0;
  const max = Math.max(1, ...(history.data?.map((h) => h.total_tokens) || [1]));

  return (
    <div className="card">
      <h2>사용량</h2>
      <div className="spaced" style={{ marginBottom: 6 }}>
        <span>오늘</span>
        <span className="mono">
          {t.used.toLocaleString()} / {t.limit.toLocaleString()} tokens
        </span>
      </div>
      <div className="bar">
        <div style={{ width: `${pct}%` }} />
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        다음 리셋: {new Date(t.reset_at).toLocaleString("ko-KR")}
      </p>

      <h2 style={{ marginTop: 20, fontSize: 14 }}>최근 7일</h2>
      <div className="spark">
        {(history.data || []).map((h) => (
          <div
            key={h.date}
            title={`${h.date}: ${h.total_tokens.toLocaleString()} tokens`}
            style={{ height: `${(h.total_tokens / max) * 100}%` }}
          />
        ))}
      </div>
    </div>
  );
}
