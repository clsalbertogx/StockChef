const pillars = [
  {
    icon: (
      <svg
        className="h-8 w-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    title: "Delivery Próprio",
    description:
      "Cardápio público por slug, carrinho PWA offline-first, checkout com ViaCEP, taxa de entrega por zona de CEP, agendamento opcional. Pedido cai direto no KDS.",
    features: ["Cash on delivery", "Idempotência", "Zonas por CEP", "PWA instalável"],
  },
  {
    icon: (
      <svg
        className="h-8 w-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
    title: "Ficha Técnica & Custo Real",
    description:
      "Cadastre insumos, crie fichas técnicas por produto, calcule custo médio ponderado automático e veja margem % e R$ por prato. Alerta de estoque mínimo automático.",
    features: ["Custo médio ponderado", "Margem % e R$", "Alerta de mínimo", "Receita versionada"],
  },
  {
    icon: (
      <svg
        className="h-8 w-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
        />
      </svg>
    ),
    title: "KDS + Comanda",
    description:
      "Fila de cozinha (KDS) com polling 5s, transições de status por role, comanda imprimível (@media print), eventos de auditoria completos. Polling 5s, sem WebSocket.",
    features: ["Polling 5s", "Transições por role", "Impressão térmica", "Auditoria completa"],
  },
  {
    icon: (
      <svg
        className="h-8 w-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"
        />
      </svg>
    ),
    title: "Compras Inteligentes",
    description:
      "Sugestão de compra automática baseada em consumo diário, lead time, estoque mínimo e segurança. Pedido de compra com recebimento parcial idempotente e custo médio atualizado.",
    features: ["Sugestão automática", "PO + recebimento", "Custo médio vivo", "Fornecedores CRUD"],
  },
];

export function Pillars() {
  return (
    <section
      className="py-20 lg:py-28 bg-gray-50 dark:bg-gray-900/50"
      aria-labelledby="pillars-title"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2
            id="pillars-title"
            className="text-3xl font-bold text-gray-900 dark:text-white sm:text-4xl"
          >
            Os 4 pilares do StockChef
          </h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            Cada pilar resolve uma dor real do dia a dia do restaurante. Juntos, formam a operação
            completa.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {pillars.map((pillar) => (
            <article
              key={pillar.title}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-shadow"
            >
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 mb-4">
                {pillar.icon}
              </div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                {pillar.title}
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-4 leading-relaxed">
                {pillar.description}
              </p>
              <ul className="space-y-2">
                {pillar.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"
                  >
                    <svg
                      className="h-4 w-4 text-emerald-500 flex-shrink-0"
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
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
