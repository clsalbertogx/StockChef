import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import DashboardPage from "./pages/DashboardPage";
import InsumosPage from "./pages/InsumosPage";
import LoginPage from "./pages/LoginPage";
import PedidoDetalhePage from "./pages/PedidoDetalhePage";
import PedidosPage from "./pages/PedidosPage";
import ProdutosPage from "./pages/ProdutosPage";

function Protected({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <Protected>
                <DashboardPage />
              </Protected>
            }
          />
          <Route
            path="/insumos"
            element={
              <Protected>
                <InsumosPage />
              </Protected>
            }
          />
          <Route
            path="/produtos"
            element={
              <Protected>
                <ProdutosPage />
              </Protected>
            }
          />
          <Route
            path="/pedidos"
            element={
              <Protected>
                <PedidosPage />
              </Protected>
            }
          />
          <Route
            path="/pedidos/:id"
            element={
              <Protected>
                <PedidoDetalhePage />
              </Protected>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
