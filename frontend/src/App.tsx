import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import ComandaPage from "./pages/ComandaPage";
import ComprasDetalhePage from "./pages/ComprasDetalhePage";
import ComprasPage from "./pages/ComprasPage";
import DashboardPage from "./pages/DashboardPage";
import EstoquePage from "./pages/EstoquePage";
import FilaKdsPage from "./pages/FilaKdsPage";
import FornecedoresPage from "./pages/FornecedoresPage";
import InsumosPage from "./pages/InsumosPage";
import InventarioPage from "./pages/InventarioPage";
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
            path="/estoque"
            element={
              <Protected>
                <EstoquePage />
              </Protected>
            }
          />
          <Route
            path="/fornecedores"
            element={
              <Protected>
                <FornecedoresPage />
              </Protected>
            }
          />
          <Route
            path="/inventario"
            element={
              <Protected>
                <InventarioPage />
              </Protected>
            }
          />
          <Route
            path="/compras"
            element={
              <Protected>
                <ComprasPage />
              </Protected>
            }
          />
          <Route
            path="/compras/:id"
            element={
              <Protected>
                <ComprasDetalhePage />
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
            path="/pedidos/:id/comanda"
            element={
              <Protected>
                <ComandaPage />
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
          <Route
            path="/cozinha"
            element={
              <Protected>
                <FilaKdsPage />
              </Protected>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
