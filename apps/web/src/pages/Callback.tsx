import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { authStore } from "../lib/auth";

export default function Callback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const code = params.get("code");
    if (!code) {
      setError("인증 코드가 없습니다. 다시 로그인하세요.");
      return;
    }

    api
      .post("/api/auth/callback", { code })
      .then((r) => {
        authStore.set(r.data.access_token);
        navigate("/dashboard", { replace: true });
      })
      .catch((e) => {
        setError(e?.response?.data?.detail || "로그인 실패");
      });
  }, [params, navigate]);

  return (
    <div className="container" style={{ paddingTop: 120, textAlign: "center" }}>
      {error ? (
        <>
          <p className="warn">{error}</p>
          <button onClick={() => navigate("/", { replace: true })}>처음으로</button>
        </>
      ) : (
        <p className="muted">로그인 처리 중...</p>
      )}
    </div>
  );
}
