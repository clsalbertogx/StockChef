import { Link } from "react-router-dom";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

const plans = [
  {
    name: "Essencial",
    price: "R$ 149",
    period: "/mês",
    description: "Para começar seu delivery próprio",
    features: [
      "Cardápio público ilimitado",
      "Carrinho PWA + checkout",
      "Até 500 pedidos/mês",
      "Zonas de entrega ilimitadas",
      "KDS + comanda",
      "Ficha técnica + margem",
      "Suporte por e-mail",
    ],
    cta: "Começar grátis 14 dias",
    popular: false,
  },
  {
    name: "Profissional",
    price: "R$ 299",
    period: "/mês",
    description: "Para restaurantes em crescimento",
    features: [
      "Tudo do Essencial",
      "Pedidos ilimitados",
      "Múltiplas lojas",
      "Compras + sugestão automática",
      "Inventário + perdas",
      "Relatórios avançados",
      "Suporte prioritário (WhatsApp)",
    ],
    cta: "Começar grátis 14 dias",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Sob consulta",
    period: "",
    description: "Para redes e franquias",
    features: [
      "Tudo do Profissional",
      "Multi-franquia + hierarquia",
      "API aberta + webhooks",
      "SSO (SAML/OIDC)",
      "SLA 99.9% + suporte 24/7",
      "Onboarding dedicado",
      "Customizações contratuais",
    ],
    cta: "Falar com vendas",
    popular: false,
  },
];

export function Pricing() {
  return (
    <section className="py-20 lg:py-28 bg-white dark:bg-gray-900" aria-labelledby="pricing-title">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2
            id="pricing-title"
            className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl"
          >
            Preço simples. Sem surpresas.
          </h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            Assinatura fixa mensal. Zero taxa por pedido. Cancele quando quiser.
            <br />
            <span className="font-medium text-emerald-600 dark:text-emerald-400">
              14 dias grátis · Sem cartão de crédito
            </span>
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <Card
              key={plan.name}
              className={`relative border-gray-200 dark:border-gray-700 ${
                plan.popular ? "ring-2 ring-emerald-500 dark:ring-emerald-500/50 shadow-lg" : ""
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-emerald-600 text-white px-3 py-1 text-sm">
                    Mais popular
                  </Badge>
                </div>
              )}
              <CardHeader className="text-center">
                <CardTitle className="text-xl font-semibold">{plan.name}</CardTitle>
                <div className="mt-2 flex items-baseline justify-center gap-1">
                  <span className="text-4xl font-bold text-gray-900 dark:text-white">
                    {plan.price}
                  </span>
                  <span className="text-gray-500 dark:text-gray-400">{plan.period}</span>
                </div>
                <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">{plan.description}</p>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-3 text-sm text-gray-600 dark:text-gray-400"
                    >
                      <svg
                        className="h-5 w-5 text-emerald-500 flex-shrink-0 mt-0.5"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                        aria-hidden="true"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>
                <Link to={plan.popular ? "/register" : "/register"}>
                  <Button
                    className="w-full"
                    variant={plan.popular ? "default" : "outline"}
                    size="lg"
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="mt-12 text-center">
          <p className="text-gray-600 dark:text-gray-400">
            Todas as funcionalidades inclusas. Sem taxa de setup. Cancelamento em 1 clique.
          </p>
        </div>
      </div>
    </section>
  );
}
