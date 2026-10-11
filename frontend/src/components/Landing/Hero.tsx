import { Link } from "react-router-dom";
import { Button } from "../ui/button";

interface HeroProps {
  className?: string;
}

export function Hero({ className }: HeroProps) {
  return (
    <section
      className={`relative overflow-hidden bg-gradient-to-b from-blue-50 to-white dark:from-blue-950 dark:to-gray-900 py-20 lg:py-32 ${className}`}
      aria-labelledby="hero-title"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <h1
            id="hero-title"
            className="text-4xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-5xl lg:text-6xl"
          >
            Seu delivery próprio.
            <br />
            <span className="text-emerald-600 dark:text-emerald-400">Sem taxas por pedido.</span>
          </h1>
          <p className="mt-6 text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Cardápio digital, checkout PWA, taxa por zona e estoque por ficha técnica. Tudo em uma
            plataforma que é sua — sem comissão por venda.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/register">
              <Button size="lg" className="w-full sm:w-auto gap-2">
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
                  />
                </svg>
                Criar meu restaurante
              </Button>
            </Link>
            <Link to="/cardapio/demo">
              <Button variant="outline" size="lg" className="w-full sm:w-auto">
                Ver cardápio demo
              </Button>
            </Link>
          </div>
          <p className="mt-6 text-sm text-gray-500 dark:text-gray-400">
            Sem cartão de crédito · Setup em 2 minutos · Cancele quando quiser
          </p>
        </div>
        <div className="mt-16 relative">
          <div className="absolute inset-0 bg-gradient-to-t from-white dark:from-gray-900 to-transparent z-10 h-32 bottom-0" />
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-2xl bg-gray-50 dark:bg-gray-800">
            <div className="flex items-center gap-2 px-4 py-3 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
            <div className="p-8">
              <div className="space-y-4 text-center">
                <div className="flex items-center justify-center gap-4 text-sm text-gray-600 dark:text-gray-300">
                  <span className="px-3 py-1 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium">
                    Cardápio
                  </span>
                  <span className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300 font-medium">
                    Carrinho
                  </span>
                  <span className="px-3 py-1 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 font-medium">
                    Checkout
                  </span>
                  <span className="px-3 py-1 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300 font-medium">
                    KDS
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  {[
                    { label: "Pedidos hoje", value: "147", icon: "📦" },
                    { label: "Faturamento", value: "R$ 4.230", icon: "💰" },
                    { label: "Ticket médio", value: "R$ 28,80", icon: "🎯" },
                    { label: "Estoque OK", value: "94%", icon: "📊" },
                  ].map((stat) => (
                    <div
                      key={stat.label}
                      className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-100 dark:border-gray-700"
                    >
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">
                        {stat.value}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center justify-center gap-1 mt-1">
                        <span>{stat.icon}</span> {stat.label}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
