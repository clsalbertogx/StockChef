import { Badge } from "../ui/badge";
import { Card, CardContent } from "../ui/card";

const testimonials = [
  {
    quote:
      "Economizamos R$ 8.000/mês só saindo do iFood. O controle de estoque evitou que a gente parasse a cozinha no fim de semana.",
    author: "Carlos M.",
    role: "Sócio, Hamburgueria Artesanal",
    metric: "−30% custo ingredientes",
  },
  {
    quote:
      "A ficha técnica calcula o custo real de cada hambúrguer. A gente aumentou o preço de 3 itens e ninguém reclamou — a margem subiu 15%.",
    author: "Fernanda L.",
    role: "Gestora, Pizzaria Delivery",
    metric: "+15% margem média",
  },
  {
    quote:
      "O KDS na cozinha acabou com os pedidos perdidos no WhatsApp. A fila é visual, todo mundo sabe o que tá preparando. Cliente recebe no tempo.",
    author: "Roberto K.",
    role: "Chefe de Cozinha, Asian Fusion",
    metric: "−40% tempo de preparo",
  },
];

const stats = [
  { value: "120+", label: "Restaurantes ativos" },
  { value: "99.9%", label: "Uptime API" },
  { value: "−27%", label: "Custo médio ingredientes" },
  { value: "5s", label: "Polling KDS" },
];

export function Testimonials() {
  return (
    <section
      className="py-20 lg:py-28 bg-gray-50 dark:bg-gray-900/50"
      aria-labelledby="testimonials-title"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2
            id="testimonials-title"
            className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl"
          >
            Restaurantes que migraram para o próprio delivery
          </h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            Resultados reais de quem trocou comissão por controle.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          {testimonials.map((t) => (
            <Card key={t.author} className="border-gray-200 dark:border-gray-700 h-full">
              <CardContent className="p-6">
                <div className="flex gap-1 mb-4" role="img" aria-label="5 estrelas">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <svg
                      key={n}
                      className="h-5 w-5 text-yellow-400 fill-current"
                      viewBox="0 0 24 24"
                      aria-hidden="true"
                    >
                      <path d="M12 2l3.09 6.26L24 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14l1.18-6.88L0 9.27l6.26-1.53L12 2z" />
                    </svg>
                  ))}
                </div>
                <p className="text-gray-700 dark:text-gray-300 mb-4 leading-relaxed">"{t.quote}"</p>
                <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                  <p className="font-medium text-gray-900 dark:text-white">{t.author}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{t.role}</p>
                </div>
                <Badge
                  variant="secondary"
                  className="mt-4 bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 text-emerald-400"
                >
                  {t.metric}
                </Badge>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {stats.map((s) => (
            <div
              key={s.label}
              className="text-center p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700"
            >
              <p className="text-4xl font-bold text-blue-600 dark:text-blue-400">{s.value}</p>
              <p className="mt-2 text-gray-600 dark:text-gray-400">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
