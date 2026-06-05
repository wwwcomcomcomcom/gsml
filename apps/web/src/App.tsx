import { Navigate, Route, Routes } from "react-router-dom";
import { authStore } from "./lib/auth";
import Login from "./pages/Login";
import Callback from "./pages/Callback";
import Dashboard from "./pages/Dashboard";

function Protected({ children }: { children: JSX.Element }) {
  return authStore.isAuthed() ? children : <Navigate to="/" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={authStore.isAuthed() ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/auth/callback" element={<Callback />} />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <Dashboard />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
