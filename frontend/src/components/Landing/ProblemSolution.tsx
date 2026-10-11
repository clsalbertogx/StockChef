import { Badge } from "../ui/badge";
import { Card, CardContent, CardHeader } from "../ui/card";

const problems = [
  {
    problem: "Taxas de 23–30% por pedido",
    impact: "Margem corroída a cada venda",
    solution: "Assinatura fixa, zero comissão",
    badge: "Economia real",
  },
  {
    problem: "Estoque às cegas",
    impact: "Faltam ingredientes no rush",
    solution: "Ficha técnica + custo real + alerta de mínimo",
    badge: "Controle total",
  },
  {
    problem: "Pedidos perdidos no WhatsApp",
    impact: "Erros, atrasos, cliente insatisfeito",
    solution: "Cardápio PWA + KDS + comanda automática",
    badge: "Operação fluida",
  },
  {
    problem: "Dependência de marketplace",
    impact: "Dados do cliente não são seus",
    solution: "Seu cardápio, seus dados, sua marca",
    badge: "Independência",
  },
];

export function ProblemSolution() {
  return (
    <section className="py-20 lg:py-28 bg-white dark:bg-gray-900" aria-labelledby="problems-title">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2
            id="problems-title"
            className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl"
          >
            Por que restaurantes estão saindo dos marketplaces
          </h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            O modelo de comissão por pedido não fecha a conta. O StockChef inverte a lógica: você
            paga uma assinatura fixa e fica com 100% do faturamento.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {problems.map((item) => (
            <Card
              key={item.problem}
              className="border-gray-200 dark:border-gray-700 hover:shadow-lg transition-shadow"
            >
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {item.problem}
                    </h3>
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{item.impact}</p>
                  </div>
                  <Badge
                    variant="secondary"
                    className="bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 text-emerald-400"
                  >
                    {item.badge}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-900/30">
                  <p className="text-sm text-blue-800 dark:text-blue-300 font-medium">
                    Como o StockChef resolve:
                  </p>
                  <p className="mt-2 text-sm text-blue-700 dark:text-blue-400">{item.solution}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
