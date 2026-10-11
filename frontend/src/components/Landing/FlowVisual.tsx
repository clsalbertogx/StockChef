import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";

const steps = [
  {
    number: "1",
    title: "Cliente acessa",
    description:
      "Cardápio público via link/QR. Sem login, sem app. Busca, filtra, vê fotos e descrições.",
    details: [
      "URL: /cardapio/:slug",
      "Busca + filtro categoria",
      "Modificadores por grupo",
      "PWA instalável",
    ],
  },
  {
    number: "2",
    title: "Adiciona ao carrinho",
    description:
      "Escolhe modificadores (obrigatórios/opcionais), observações, quantidade. Subtotal em tempo real.",
    details: [
      "Validação min/max por grupo",
      "Persistido no localStorage",
      "Offline-first",
      "Deltas de preço inclusos",
    ],
  },
  {
    number: "3",
    title: "Checkout com ViaCEP",
    description:
      "Entrega ou retirada. CEP preenche endereço. Taxa por zona, mínimo, ETA. Agendamento opcional.",
    details: [
      "ViaCEP stdlib (sem lib)",
      "Zonas por range de CEP",
      "Mínimo por zona",
      "Cash on delivery",
    ],
  },
  {
    number: "4",
    title: "Pedido no KDS",
    description:
      "Cai na fila de cozinha (polling 5s). Transições: confirmed → preparing → ready → delivered.",
    details: ["Polling 5s", "FIFO por created_at", "Transições por role", "Comanda imprimível"],
  },
  {
    number: "5",
    title: "Baixa de estoque",
    description:
      "Confirmação dispara outbox → baixa idempotente. Movimentos de estoque + custo médio atualizado.",
    details: [
      "Idempotência por event_id",
      "Custo médio ponderado",
      "Alerta de mínimo",
      "Inventário periódico",
    ],
  },
  {
    number: "6",
    title: "Gestão & Compras",
    description:
      "Sugestão de compra por consumo + lead + segurança. PO → recebimento parcial → custo médio vivo.",
    details: [
      "Sugestão automática",
      "PO + recebimento idempotente",
      "Custo médio vivo",
      "Fornecedores CRUD",
    ],
  },
];

export function FlowVisual() {
  return (
    <section className="py-20 lg:py-28 bg-white dark:bg-gray-900" aria-labelledby="flow-title">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2
            id="flow-title"
            className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl"
          >
            Do clique ao estoque — fluxo completo
          </h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            Cada etapa foi pensada para reduzir atrito, eliminar erros e dar visibilidade total ao
            gestor.
          </p>
        </div>
        <div className="relative">
          <div className="hidden lg:absolute left-1/2 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700 -ml-px" />
          <div className="space-y-8 lg:space-y-12">
            {steps.map((step) => (
              <div key={step.number} className="relative">
                <div className="flex flex-col lg:flex-row lg:items-center gap-6">
                  <div className="flex-shrink-0 w-14 h-14 rounded-full border-4 border-blue-600 bg-white dark:bg-gray-800 flex items-center justify-center text-2xl font-bold text-blue-600 dark:text-blue-400 z-10">
                    {step.number}
                  </div>
                  <div className="w-full lg:w-1/2">
                    <Card className="bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700">
                      <CardHeader>
                        <CardTitle className="text-xl">{step.title}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-gray-600 dark:text-gray-300 mb-4">{step.description}</p>
                        <ul className="flex flex-wrap gap-2">
                          {step.details.map((detail) => (
                            <li
                              key={detail}
                              className="px-3 py-1 bg-white dark:bg-gray-800 rounded-full text-xs text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700"
                            >
                              {detail}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
