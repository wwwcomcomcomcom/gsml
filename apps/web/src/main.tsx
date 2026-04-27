import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OAuthProvider } from "@themoment-team/datagsm-oauth-react";
import App from "./App";
import "./styles.css";

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <OAuthProvider
        clientId={import.meta.env.VITE_OAUTH_CLIENT_ID}
        redirectUri={import.meta.env.VITE_OAUTH_REDIRECT_URI}
        authMode="STANDARD"
      >
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </OAuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
