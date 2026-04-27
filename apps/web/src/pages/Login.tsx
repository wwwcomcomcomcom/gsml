import { OAuthLoginButton } from "@themoment-team/datagsm-oauth-react";

export default function Login() {
  return (
    <div className="container" style={{ paddingTop: 120, textAlign: "center" }}>
      <h1>GSML</h1>
      <p className="muted" style={{ marginBottom: 32 }}>
        DataGSM 계정으로 로그인하여 LLM API Key를 발급받으세요.
      </p>
      <OAuthLoginButton />
    </div>
  );
}
