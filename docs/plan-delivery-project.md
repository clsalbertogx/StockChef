# Plano de Projeto — StockChef: SaaS de Delivery com Controle de Estoque Otimizado, Precificação Inteligente e Agentes de IA

## 1. Visão geral do produto

O produto proposto é uma plataforma SaaS multiempresa, acessível por desktop e mobile, voltada para fast-foods, restaurantes, lanchonetes, pizzarias, marmitarias, cafeterias, hamburguerias, dark kitchens e pequenos negócios alimentícios que operam ou desejam operar com **entrega própria**.

O diferencial competitivo não será apenas “receber pedidos”, mas sim conectar três camadas críticas do negócio:

1. **Operação de delivery**: pedidos, cozinha, despacho, entregadores, rastreamento, prova de entrega e atendimento.
2. **Gestão de estoque de matéria-prima**: controle por ficha técnica, validade, perdas, reposição, compras e custo real dos pratos.
3. **Inteligência de decisão**: análise de dados preditiva e prescritiva para sugerir compras, precificação, promoções, redução de ruptura, redução de desperdício e melhoria de margem.
4. **Agentes de IA operacionais**: assistentes autônomos ou semi-autônomos que monitoram, analisam, propõem ações e executam tarefas administrativas com supervisão humana.

Em resumo, o SaaS deve ser um “sistema nervoso central” do restaurante: recebe pedidos, dá baixa inteligente no estoque, alerta riscos, sugere compras, recomenda preços, organiza a entrega e usa IA para reduzir trabalho manual e melhorar margem.

---

## 2. Nome do projeto

Nome definido: **StockChef**.

---

## 3. Problema que o produto resolve

Muitos restaurantes e pequenos negócios alimentícios enfrentam:

- Estoque impreciso, com divergência entre sistema e realidade.
- Compras baseadas em intuição, causando falta de insumos ou excesso.
- Desperdício por validade, armazenamento inadequado ou erro de porcionamento.
- Preço de venda definido sem análise de custo real, concorrência e elasticidade.
- Delivery próprio desorganizado, sem rastreabilidade, ETA confiável ou controle de entregadores.
- Falta de visão consolidada de margem por prato, canal, horário e entregador.
- Rotinas administrativas manuais, repetitivas e suscetíveis a erro.
- Dificuldade de transformar dados operacionais em decisões práticas.

O SaaS proposto resolve isso unificando operação, estoque, finanças gerenciais e IA em uma única plataforma.

---

## 4. Proposta de valor

### Para o dono/gestor do restaurante

- Visão clara de lucro por prato, período, canal e unidade.
- Redução de ruptura de estoque e desperdício.
- Sugestões de compra com justificativa baseada em demanda prevista.
- Recomendações de preço com análise de custo, margem e mercado.
- Menos tempo em planilhas e mais tempo em decisão estratégica.

### Para a cozinha e operação

- Baixa automática de insumos a partir dos pedidos.
- Alertas de falta, validade próxima, divergência de inventário e custo anormal.
- Ficha técnica acessível mobile para conferência de preparo.
- Painel de pedidos integrado ao estoque e ao despacho.

### Para o delivery próprio

- Gestão de entregadores, zonas, taxas, turnos e ocorrências.
- Roteirização básica ou avançada conforme fase.
- Prova de entrega com foto, assinatura ou código.
- Comunicação com cliente via WhatsApp, SMS, push ou e-mail.
- Métricas de tempo médio de entrega, atrasos, taxa de cancelamento e custo por entrega.

### Para quem deseja criar entrega própria

- Simulador de viabilidade: quantos entregadores, veículos, zonas, custos fixos e variáveis.
- Comparação entre delivery próprio, agregados e híbrido.
- Checklist de implantação: cadastro, documentação, seguro, uniformes, app do entregador, política de área e taxa.

### Para o SaaS em si

- Agentes de IA que reduzem suporte humano, aumentam retenção e criam um diferencial difícil de copiar.
- Dados proprietários de consumo, estoque, preço e operação, permitindo melhoria contínua dos modelos.

---

## 5. Público-alvo

### Segmento primário

- Fast-foods independentes.
- Hamburguerias.
- Pizzarias.
- Marmitarias.
- Restaurantes de bairro.
- Dark kitchens.
- Cafeterias e confeitarias.
- Food trucks com operação fixa ou semi-fixa.
- Pequenas redes com 1 a 10 unidades.

### Segmento secundário

- Franquias pequenas.
- Mercados com rotisseria.
- Açaiterias.
- Pastelarias.
- Restaurantes corporativos com entrega.
- Negócios que hoje usam iFood/Rappi/WhatsApp e querem migrar para canal próprio.

---

## 6. Personas principais

### Persona 1 — Dona/Dono ou Gerente Geral

- Quer margem, previsibilidade e controle.
- Tem pouco tempo para análise profunda.
- Precisa de respostas simples: “comprar o quê?”, “por quanto vender?”, “onde estou perdendo dinheiro?”.

### Persona 2 — Cozinheiro/Chefe de Cozinha

- Precisa saber o que está acabando, o que vencer e como preparar cada item.
- Quer evitar interrupções por falta de insumo.
- Usa mobile ou tablet na cozinha.

### Persona 3 — Comprador/Estoquista

- Precisa de lista de compras objetiva.
- Quer comparar fornecedores, preços, prazos e quantidades mínimas.
- Precisa registrar recebimento, perda e inventário.

### Persona 4 — Entregador

- Precisa receber pedidos, rota, endereço, contato e confirmação de entrega.
- Quer simplicidade, bateria preservada e pagamento/gorjeta transparente.

### Persona 5 — Cliente final

- Quer pedir fácil, acompanhar entrega, pagar com Pix/cartão e falar com o restaurante.

### Persona 6 — Administrador do SaaS

- Gerencia clientes, planos, feature flags, suporte, uso de IA, billing e saúde da plataforma.

---

## 7. Escopo funcional recomendado

## 7.1 Módulos centrais

| Módulo | Descrição | Prioridade |
|---|---|---|
| Autenticação e multiempresa | Login, perfis, permissões, lojas/unidades, planos SaaS | MVP |
| Cadastros básicos | Produtos, categorias, insumos, fornecedores, unidades, conversões | MVP |
| Ficha técnica/recipe | Composição de cada prato por insumos e quantidades | MVP |
| Cardápio digital | Itens, adicionais, observações, fotos, disponibilidade, promoções | MVP |
| Pedidos | Criação, edição, cancelamento, status, impressão, KDS | MVP |
| Checkout do cliente | Web/PWA, carrinho, pagamento, endereço, horário, taxa | MVP |
| Pagamentos | Pix, cartão, dinheiro, vale, split básico, conciliação | MVP/V1 |
| Delivery próprio | Despacho, entregador, rota, ETA, acompanhamento, prova de entrega | MVP/V1 |
| Gestão de entregadores | Cadastro, documentos, turnos, ganho por entrega, avaliação | V1 |
| Estoque operacional | Entrada, saída, ajuste, perda, inventário, validade, lote | MVP |
| Compras | Sugestão de compra, pedido de compra, recebimento, histórico | MVP/V1 |
| Precificação | Custo do prato, margem alvo, sugestão de preço, simulações | V1 |
| Analytics/BI | Dashboards de vendas, margem, estoque, rupturas, desperdício | V1 |
| IA preditiva | Previsão de demanda, risco de ruptura, sugestão de compra | V1/V2 |
| Agentes de IA | Assistente operacional, estoquista, precificador, atendimento, financeiro | V2 |
| Atendimento ao cliente | Chat, WhatsApp, notificações, templates, histórico | V1 |
| Financeiro gerencial | Fluxo de caixa simplificado, contas a pagar, receita, custo | V1/V2 |
| Fiscal/integrações | Emissão NF, integração ERP/contador, certificados | V2/parceria |
| Administração SaaS | Billing, uso, limites, logs, suporte, onboarding | MVP/V1 |

---

## 8. Detalhamento por módulo

## 8.1 Cadastros e estrutura do negócio

Entidades mínimas:

- Tenant/empresa.
- Loja/unidade.
- Usuário e papel: dono, gerente, caixa, cozinha, comprador, entregador, suporte.
- Categoria de produto.
- Produto/item do cardápio.
- Adicionais/combos/variações.
- Insumo/matéria-prima.
- Unidade de medida: kg, g, L, ml, unidade, pacote, folha etc.
- Conversão de unidade: exemplo: 1 caixa = 24 unidades; 1 pacote = 500 g.
- Fornecedor.
- Ficha técnica do produto.
- Zona de entrega.
- Taxa de entrega.
- Forma de pagamento.
- Imposto/taxa variável, se necessário.

Regra importante: todo produto vendido deve poder estar vinculado a uma ficha técnica. Isso permite baixa automática de estoque e cálculo de custo real.

Exemplo:

Produto: X-Burger
Ficha técnica:

- Pão de brioche: 1 unidade.
- Carne 160 g: 1 unidade.
- Queijo cheddar: 30 g.
- Alface: 10 g.
- Molho especial: 15 ml.
- Embalagem: 1 unidade.

Quando vende 1 X-Burger, o sistema dá baixa nesses insumos.

---

## 8.2 Cardápio e pedidos

Funcionalidades:

- Criar produtos com foto, descrição, preço, categoria, disponibilidade.
- Criar adicionais cobrados ou não cobrados.
- Definir horários de funcionamento e pausas.
- Aceitar pedidos para retirada, mesa, delivery próprio e, futuramente, marketplace.
- Controlar status: recebido, em preparo, pronto, saiu para entrega, entregue, cancelado, reembolso.
- Imprimir comanda ou enviar para Kitchen Display System.
- Permitir observações do cliente.
- Bloquear item sem estoque suficiente ou permitir venda com alerta configurável.
- Registrar cancelamento com motivo.
- Histórico completo por pedido.

---

## 8.3 Checkout do cliente

Para MVP, recomendo iniciar com **PWA responsivo**, evitando custo alto de app nativo do cliente logo no início.

Funcionalidades:

- Acesso por link, QR code na embalagem ou loja física.
- Menu por categoria.
- Carrinho.
- Seleção de endereço.
- Cálculo de taxa por zona/bairro/km.
- Escolha de horário: agora ou agendado.
- Pagamento online: Pix, cartão, boleto opcional.
- Pagamento na entrega, se o lojista permitir.
- Acompanhamento do pedido.
- Chat/WhatsApp para dúvidas.
- Cupom de desconto.
- Programa de fidelidade simples, em fase posterior.

---

## 8.4 Delivery próprio

Este módulo é essencial para o posicionamento do produto.

Funcionalidades:

- Cadastro de entregadores.
- Vínculo por turno ou disponibilidade.
- Atribuição manual ou automática de pedido.
- Mapa com localização do entregador, se houver consentimento.
- ETA estimado.
- Rota básica por endereço, zona ou proximidade.
- Prova de entrega: foto, assinatura digital, código PIN ou confirmação do cliente.
- Ocorrências: endereço errado, cliente não atende, atraso, acidente, avaria.
- Taxa de entrega configurável por zona, faixa de distância, horário e tipo de pedido.
- Custo por entrega: km, tempo, combustível, manutenção, pagamento ao entregador.
- Indicadores: tempo médio de despacho, tempo de trânsito, taxa de atraso, cancelamento por entrega.

Para negócios que desejam criar entrega própria:

- Simulador de estrutura mínima.
- Recomendação de número de entregadores por pico.
- Estimativa de custo fixo e variável.
- Checklist de implantação.
- Modelo de remuneração por entrega, hora ou km.
- Comparação com delivery de terceiros.

---

## 8.5 Estoque otimizado

O controle de estoque deve ser o coração analítico do SaaS.

### Funcionalidades operacionais

- Entrada de compra.
- Saída por venda.
- Saída por perda/desperdício.
- Ajuste de inventário.
- Transferência entre unidades, em fases futuras.
- Controle por lote e validade.
- FEFO: First Expire, First Out.
- Custo médio ponderado móvel.
- Inventário cíclico.
- Contagem manual pelo mobile.
- Alerta de validade próxima.
- Alerta de estoque abaixo do mínimo.
- Alerta de divergência entre esperado e contado.
- Registro de motivo de perda: vencimento, queima, erro de preparo, queda, furto, devolução.

### Funcionalidades inteligentes

- Previsão de consumo por insumo.
- Cálculo de ponto de reposição.
- Estoque de segurança.
- Sugestão de quantidade de compra.
- Consideração de lead time do fornecedor.
- Consideração de quantidade mínima de compra.
- Consideração de orçamento disponível.
- Consideração de validade e capacidade de armazenamento.
- Priorização por risco de ruptura e impacto na receita.
- Simulação: “se eu não comprar carne hoje, perco X pedidos amanhã”.

---

## 8.6 Compras de matéria-prima

Funcionalidades:

- Lista de sugestão de compra diária/semanal.
- Pedido de compra para fornecedor.
- Recebimento parcial ou total.
- Conferência de nota/fatura.
- Histórico de preço por fornecedor.
- Variação de preço ao longo do tempo.
- Avaliação de fornecedor: prazo, qualidade, preço, atraso.
- Cotação simples entre fornecedores.
- Aprovação de compra pelo gestor.
- Integração futura com ERP/contador.

A sugestão de compra deve vir com explicação:

> “Sugiro comprar 12 kg de queijo porque a previsão de consumo para os próximos 3 dias é 10,4 kg, o estoque atual é 2,1 kg, o lead time do fornecedor é 1 dia e o estoque de segurança recomendado é 1,5 kg.”

Isso aumenta confiança e adoção.

---

## 8.7 Precificação inteligente

O sistema deve calcular o custo real do prato considerando:

- Insumos da ficha técnica.
- Embalagem.
- Taxa de pagamento, se aplicável.
- Custo variável de delivery, se o lojista quiser incluir.
- Perda média histórica do insumo.
- Variação recente de preço de compra.

Depois, pode sugerir preço com base em:

- Margem alvo configurada pelo usuário.
- Custo-plus.
- Concorrência local, quando houver coleta de dados permitida.
- Elasticidade estimada por histórico de vendas e promoções.
- Preço psicológico: R$ 29,90 em vez de R$ 30,00.
- Impacto na demanda: aumentar preço pode reduzir vendas, mas melhorar margem.
- Cenários: manter preço, aumentar 5%, reduzir 8%, criar combo, criar promoção condicionada.

Exemplo de saída:

> “O X-Burger está com margem de contribuição de 48%. O preço atual é R$ 27,90. Considerando custo de R$ 11,20, concorrência média de R$ 29,50 e sensibilidade a preço moderada, sugiro testar R$ 29,90 por 14 dias. Estimativa de impacto: -4% em volume e +9% em margem bruta.”

Importante: no início, a IA deve recomendar, não alterar automaticamente preço sem aprovação.

---

## 8.8 Agentes de IA para gestão completa do SaaS

Os agentes não devem ser apenas um chatbot genérico. Eles precisam ser especializados, com ferramentas, contexto, limites e trilha de auditoria.

### Agente Estoquista

Funções:

- Monitorar estoque, validade e consumo.
- Detectar risco de ruptura.
- Gerar sugestão de compra.
- Analisar divergências de inventário.
- Identificar perdas anormais.
- Perguntar ao usuário: “Deseja aprovar a compra sugerida?”.

### Agente Precificador

Funções:

- Analisar custo, margem, vendas e concorrência.
- Sugerir reajuste de preço.
- Simular cenários.
- Identificar pratos com margem negativa.
- Recomendar combos ou ajustes de porção.

### Agente Operacional de Delivery

Funções:

- Monitorar pedidos atrasados.
- Sugerir reatribuição de entregador.
- Alertar cozinha sobre picos de demanda.
- Detectar padrões de atraso por horário, zona ou entregador.
- Preparar resumo diário de operação.

### Agente de Atendimento ao Cliente

Funções:

- Responder dúvidas frequentes via WhatsApp/chat.
- Informar status do pedido.
- Coletar feedback.
- Escalar para humano quando necessário.
- Aplicar políticas de reembolso/cupom dentro de limites configurados.

### Agente Financeiro Gerencial

Funções:

- Conciliar pagamentos.
- Alertar sobre queda de margem.
- Projetar fluxo de caixa simples.
- Identificar despesas anormais.
- Gerar relatório semanal para o dono.

### Agente de Onboarding e Success

Funções:

- Ajudar o cliente do SaaS a configurar cardápio, fichas técnicas e fornecedores.
- Detectar dados incompletos.
- Recomendar próximas ações.
- Reduzir churn nos primeiros 30 dias.

### Agente de Qualidade de Dados

Funções:

- Verificar cadastros inconsistentes.
- Alertar unidade de medida errada.
- Detectar ficha técnica incompleta.
- Apontar produtos vendidos sem insumo vinculado.
- Sugerir correções.

### Princípios para agentes de IA

- Human-in-the-loop para ações sensíveis: compra, mudança de preço, reembolso, comunicação em massa.
- Explicabilidade: toda recomendação deve ter motivo.
- Limites de autonomia: valores máximos, percentuais máximos, horários.
- Logging completo: quem aprovou, o que o agente sugeriu, quais ferramentas usou.
- Feedback loop: aceitar/rejeitar sugestão melhora o modelo.
- Guardrails: nunca executar ação destrutiva sem confirmação.
- Privacidade: não usar dados de um tenant para treinar resposta destinada a outro sem anonimização e política adequada.

---

## 9. MVP recomendado

Para não construir um sistema gigante antes de validar, recomendo um MVP focado em **“pedido + estoque + entrega própria + primeira camada de IA”**.

### MVP deve ter

- Cadastro de loja, usuários e permissões.
- Cadastro de insumos, fornecedores e unidades.
- Cadastro de produtos com ficha técnica.
- Cardápio digital via PWA.
- Pedido com pagamento Pix/cartão.
- Painel de pedidos para desktop e mobile.
- Baixa automática de estoque por pedido.
- Registro de perda e inventário simples.
- Alerta de estoque mínimo.
- Sugestão de compra baseada em regras: mínimo, máximo, lead time e consumo médio.
- Delivery próprio básico: atribuição, status, prova de entrega.
- Dashboard simples: vendas, itens mais vendidos, estoque crítico, margem por prato.
- Agente de IA assistivo inicial: resumo diário, alertas e perguntas em linguagem natural sobre dados do restaurante.

### MVP não precisa ter inicialmente

- App nativo do cliente.
- App nativo do entregador, se puder começar com PWA.
- Roteirização avançada.
- Múltiplas unidades complexas.
- Integração com iFood/Rappi.
- Fiscal completo.
- ML avançado com dezenas de modelos.
- Automação total de compras e preços.
- White-label completo.

---

## 10. Arquitetura técnica sugerida

## 10.1 Visão macro

A arquitetura deve ser multi-tenant, segura, escalável e orientada a eventos, porque pedidos, estoque, pagamentos e entregas geram muitos estados assíncronos.

Componentes:

- Frontend web administrativo: desktop para gestão.
- Frontend mobile: PWA responsivo para operação, cozinha, gerente e entregador.
- Frontend do cliente: PWA responsivo.
- API backend: orquestra regras de negócio.
- Banco relacional: dados transacionais.
- Cache/fila: performance e assincronismo.
- Armazenamento de arquivos: imagens, comprovantes, fotos de entrega.
- Data warehouse/lakehouse: analytics e IA.
- Serviço de ML: previsão, recomendação, detecção de anomalia.
- Orquestrador de agentes de IA: ferramentas, memória, aprovação, logs.
- Integrações: pagamento, WhatsApp, maps, notificações.
- Observabilidade: logs, métricas, tracing, alertas.

---

## 10.2 Stack recomendada

### Frontend web

Usar as imagens como referencia.

- @docs/images/reference-administrative-ui-ux-design-1.jpeg
- @docs/images/reference-administrative-ui-ux-design-2.jpeg
- @docs/images/reference-administrative-ui-ux-design-3.jpeg

Opção mais eficiente para começar:

- React + TypeScript.
- Next.js ou Vite + React Router.
- Tailwind CSS ou design system próprio.
- Shadcn/UI.
- TanStack Query para estado servidor.
- Chart.js, Recharts ou Apache ECharts para dashboards.
- Conceitos IHC.

### Mobile

Usar as imagens como referencia.

- @docs/images/reference-delivery-ui-ux-design-1.png
- @docs/images/reference-delivery-ui-ux-design-2.png

Opção mais eficiente para começar:

- PWA responsivo.
- TypeScript.
- Offline-first com WatermelonDB e MMKV juntos. MMKV: para estado global rápido, tokens, configurações, tema (dark/light) e pequenos caches de sessão. WatermelonDB: para todos os dados estruturados.
- Push notifications via Firebase Cloud Messaging/APNs.
- Conceitos IHC.

### Backend

Para MVP, recomendo **monólito modular** antes de microserviços completos.

- Python + FastAPI.
- Forte integração com dados/IA.
- Uso da Clean Architecture e Design Patterns facilitando regras de negócio e integrações.

### Banco de dados

- PostgreSQL como banco principal.
- Row-Level Security ou tenant_id disciplinado para multi-tenancy.
- Redis para cache, sessões, filas leves e rate limiting.
- TimescaleDB para séries temporais e analytics.
- pgvector para embeddings/RAG dos agentes.
- MinIO ou UploadThing para arquivos.

### Filas e eventos

- RabbitMQ.

Eventos importantes:

- order.created
- order.confirmed
- order.cancelled
- stock.reserved
- stock.decremented
- stock.adjusted
- purchase.received
- delivery.assigned
- delivery.completed
- payment.captured
- price.changed
- ai.recommendation.generated
- ai.action.approved
- ai.action.rejected

### Infraestrutura

- Containers Docker.
- GitHub Actions para CI/CD.

### IA e LLM

- OpenAI, Anthropic, Google Gemini, Azure OpenAI ou modelos open-source hospedados.
- LangGraph/LangChain/LlamaIndex ou framework próprio para agentes.
- ML tradicional: LightGBM, XGBoost, Prophet, statsmodels, scikit-learn.
- MLOps: MLflow, DVC, Airflow/Dagster/Prefect.
- Feature store simples: tabela de features no Postgres/TimescaleDB ou Feast, se necessário.

---

## 10.3 Modelo de dados essencial

Entidades principais:

- tenants
- stores
- users
- roles
- permissions
- suppliers
- ingredients
- units
- unit_conversions
- products
- product_modifiers
- recipes
- recipe_items
- stock_items
- stock_movements
- inventory_counts
- losses
- purchase_orders
- purchase_order_items
- goods_receipts
- zones
- delivery_fees
- drivers
- driver_shifts
- orders
- order_items
- order_events
- payments
- refunds
- deliveries
- delivery_events
- proofs_of_delivery
- prices
- price_experiments
- forecasts
- recommendations
- agent_runs
- agent_tools
- audit_logs
- subscriptions
- plans
- usage_metrics

---

## 11. Estratégia de dados e IA

A IA só funciona bem se houver fundação de dados sólida. O projeto deve seguir quatro níveis de análise:

1. **Descritiva**: o que aconteceu?
2. **Diagnóstica**: por que aconteceu?
3. **Preditiva**: o que pode acontecer?
4. **Prescritiva**: o que devemos fazer?

---

## 11.1 Dados descritivos

Dashboards iniciais:

- Vendas por dia, hora, produto, categoria, canal.
- Ticket médio.
- Pratos mais vendidos.
- Pratos com maior margem.
- Pratos com margem negativa.
- Estoque atual por insumo.
- Itens abaixo do mínimo.
- Itens próximos da validade.
- Perdas por motivo.
- Tempo médio de preparo.
- Tempo médio de entrega.
- Cancelamentos por motivo.
- Custo de delivery por pedido.

---

## 11.2 Dados diagnósticos

Alertas e análises:

- Por que a margem caiu?
- Qual insumo subiu de preço?
- Qual prato está vendendo menos após aumento de preço?
- Qual entregador/zona está atrasando mais?
- Qual horário gera mais perda?
- Qual fornecedor está entregando fora do prazo?
- Qual produto está sendo vendido sem estoque suficiente configurado?

---

## 11.3 Modelos preditivos

### Previsão de demanda

Objetivo: prever venda de produtos e consumo de insumos.

Variáveis:

- Histórico de vendas.
- Dia da semana.
- Feriados.
- Horário.
- Promoções.
- Clima, se disponível.
- Eventos locais.
- Campanhas de marketing.
- Sazonalidade.
- Preço atual.
- Disponibilidade de estoque.

Modelos iniciais:

- Média móvel.
- Holt-Winters.
- Prophet.
- LightGBM/XGBoost para features tabulares.

Métricas:

- MAPE.
- WAPE.
- RMSE.
- Bias.
- Acurácia por família de produto.

Importante: começar com previsão simples e evoluir. Não tentar deep learning no início.

### Previsão de consumo de insumo

Derivada da previsão de venda dos produtos multiplicada pela ficha técnica.

Exemplo:

Se prevê vender 80 X-Burgers amanhã, e cada X-Burger usa 30 g de queijo, o consumo previsto de queijo é 2,4 kg.

### Risco de ruptura

Calcula probabilidade de faltar insumo antes da próxima reposição.

Fórmula conceitual:

- Estoque disponível.
- Consumo previsto até lead time.
- Estoque de segurança.
- Variabilidade de demanda.
- Variabilidade de lead time do fornecedor.

### Previsão de desperdício

Modela perdas por:

- Validade.
- Histórico de descarte.
- Volume comprado.
- Condição de armazenamento, se registrada.
- Erro de preparo.

### Detecção de anomalia

Identifica:

- Venda atípica.
- Cancelamento anormal.
- Desvio de inventário.
- Fraude em pagamento.
- Entregador com comportamento estranho.
- Preço fora do padrão.
- Consumo de insumo incompatível com vendas.

---

## 11.4 Modelos prescritivos

### Otimização de compra

Entradas:

- Previsão de demanda.
- Estoque atual.
- Pedidos em trânsito.
- Lead time.
- Quantidade mínima do fornecedor.
- Preço por faixa de quantidade.
- Validade.
- Capacidade de armazenamento.
- Orçamento disponível.
- Nível de serviço desejado, por exemplo 95%.

Saídas:

- O que comprar.
- Quanto comprar.
- De qual fornecedor.
- Quando comprar.
- Qual prioridade.
- Qual impacto se não comprar.

Métodos:

- Regras determinísticas no MVP.
- Ponto de reposição + estoque de segurança.
- EOQ adaptado.
- Otimização com restrição de orçamento.
- Heurísticas para perecíveis.
- Depois, otimização matemática ou reinforcement learning simples, se houver maturidade.

### Sugestão de preço

Entradas:

- Custo variável do prato.
- Margem alvo.
- Preço atual.
- Histórico de demanda por preço.
- Concorrência, se coletada legalmente.
- Elasticidade estimada.
- Promoções anteriores.
- Posicionamento do negócio.

Saídas:

- Faixa de preço recomendada.
- Preço sugerido.
- Impacto estimado em volume.
- Impacto estimado em margem.
- Risco associado.
- Período de teste recomendado.

### Recomendação de cardápio

- Descontinuar item com baixa venda e baixa margem.
- Reformular item com alta venda e margem baixa.
- Criar combo com item de alta margem.
- Ajustar porção.
- Trocar insumo por similar mais barato sem impactar percepção.
- Destacar item lucrativo no menu digital.

---

## 11.5 Agentes de IA: arquitetura operacional

Cada agente deve ter:

- Papel claro.
- Ferramentas autorizadas.
- Contexto do tenant.
- Memória de curto e longo prazo.
- Políticas de segurança.
- Fluxo de aprovação.
- Log de decisões.

Ferramentas possíveis:

- Consultar banco via API segura.
- Calcular custo/margem.
- Gerar forecast.
- Buscar dados de mercado.
- Enviar notificação.
- Criar rascunho de pedido de compra.
- Criar rascunho de campanha.
- Abrir chamado de suporte.
- Atualizar status de pedido, se permitido.
- Consultar documentos internos via RAG.

Exemplo de fluxo do Agente Estoquista:

1. Agenda diária executa análise de estoque.
2. Agente consulta previsão de demanda e estoque atual.
3. Identifica 4 insumos com risco alto.
4. Gera sugestão de compra.
5. Calcula impacto no caixa.
6. Envia para aprovação do gerente no mobile.
7. Gerente aprova, edita ou rejeita.
8. Sistema cria pedido de compra rascunho.
9. Agente registra feedback para melhorar próxima recomendação.

---

## 12. Roadmap de desenvolvimento

Below, a practical phased plan. The total estimated duration for a robust commercial version is approximately **8 to 12 months**, depending on team size, integrations and pilot feedback.

## Fase 0 — Descoberta, blueprint e validação

Duração: 2 a 4 semanas.

Objetivos:

- Entender profundamente o operação de 5 a 15 restaurantes potenciais.
- Definir persona principal e caso de uso prioritário.
- Mapear fluxo de pedido, estoque, compra, entrega e preço.
- Definir modelo de dados inicial.
- Escolher stack e arquitetura.
- Criar protótipo navegável.
- Definir métricas de sucesso do MVP.
- Levantar requisitos LGPD, fiscais e de pagamento.

Entregáveis:

- PRD inicial.
- User journey maps.
- Wireframes de baixa/alta fidelidade.
- Modelo de dados conceitual.
- Arquitetura de referência.
- Backlog priorizado.
- Plano de pilotagem.

Critério de saída:

- Stakeholders alinhados sobre escopo do MVP.
- Protótipo validado com pelo menos 5 potenciais usuários.

---

## Fase 1 — Fundação do SaaS e cadastros críticos

Duração: 4 a 6 semanas.

Objetivos:

- Construir base multi-tenant.
- Implementar autenticação, autorização e organização.
- Criar cadastros de loja, usuário, produto, insumo, fornecedor e ficha técnica.
- Implementar painel administrativo básico.

Escopo:

- Login/logout.
- Recuperação de senha.
- MFA opcional.
- Perfis: owner, manager, cashier, kitchen, buyer, driver, support.
- Cadastro de empresa/loja.
- Cadastro de insumos com unidade e conversão.
- Cadastro de fornecedores.
- Cadastro de produtos.
- Cadastro de ficha técnica.
- Upload de imagens.
- Auditoria básica.

Entregáveis:

- Ambiente dev/staging/prod.
- CI/CD básico.
- Banco multi-tenant funcional.
- Painel web de cadastros.
- API documentada.

Critério de saída:

- Um restaurante consegue cadastrar cardápio, insumos, fornecedores e fichas técnicas completas.

---

## Fase 2 — Pedidos, checkout e operação básica

Duração: 5 a 7 semanas.

Objetivos:

- Permitir venda real via canal próprio.
- Controlar ciclo de pedido.
- Integrar pagamento mínimo viável.

Escopo:

- PWA do cliente.
- Carrinho.
- Endereço.
- Taxa de entrega por zona.
- Horários de funcionamento.
- Criação de pedido.
- Painel de pedidos desktop/mobile.
- Status do pedido.
- Impressão de comanda ou fila de cozinha.
- Pagamento Pix e cartão via PSP.
- Cancelamento com motivo.
- Notificações básicas.
- Histórico do pedido.

Entregáveis:

- Fluxo ponta a ponta: cliente pede, restaurante recebe, cozinha prepara, pedido é concluído.
- Integração de pagamento em sandbox e produção restrita.
- Painel operacional funcional.

Critério de saída:

- Pedido real pode ser criado, pago, processado e concluído com registro de eventos.

---

## Fase 3 — Delivery próprio e gestão de entregadores

Duração: 4 a 6 semanas.

Objetivos:

- Operar entrega própria com controle mínimo confiável.
- Dar visibilidade ao cliente e ao gestor.

Escopo:

- Cadastro de entregador.
- Zona de entrega.
- Atribuição de pedido.
- PWA do entregador.
- Atualização de status.
- Mapa simples ou link de rota.
- ETA básico.
- Prova de entrega.
- Ocorrências.
- Taxa por entrega.
- Relatório de desempenho do entregador.
- Notificação ao cliente.

Entregáveis:

- Operação de delivery própria funcional.
- Painel de despacho.
- Mobile do entregador.

Critério de saída:

- 100% dos pedidos delivery podem ser atribuídos, acompanhados e concluídos com prova de entrega.

---

## Fase 4 — Estoque, compras e controle de perdas

Duração: 5 a 7 semanas.

Objetivos:

- Tornar o estoque confiável.
- Conectar venda, compra, perda e custo.

Escopo:

- Movimentação automática por pedido.
- Entrada de compra.
- Recebimento parcial.
- Ajuste de inventário.
- Contagem mobile.
- Registro de perda.
- Validade e lote.
- FEFO.
- Custo médio ponderado.
- Estoque mínimo/máximo.
- Ponto de reposição simples.
- Sugestão de compra por regra.
- Pedido de compra rascunho.
- Aprovação pelo gestor.
- Relatórios de estoque.

Entregáveis:

- Módulo de estoque operacional completo.
- Primeira versão da sugestão de compra.
- Dashboard de rupturas e perdas.

Critério de saída:

- O sistema consegue refletir estoque real com razoável precisão e gerar sugestão de compra útil.

---

## Fase 5 — Analytics, precificação e primeira camada de IA

Duração: 6 a 8 semanas.

Objetivos:

- Transformar dados em recomendações.
- Introduzir previsão e sugestão de preço.

Escopo:

- Data pipeline básico.
- Métricas de negócio.
- Dashboard de margem por prato.
- Previsão de demanda simples.
- Projeção de consumo de insumo.
- Alerta de risco de ruptura.
- Sugestão de compra aprimorada.
- Calculadora de preço.
- Sugestão de faixa de preço.
- Simulação de cenários.
- Agente de perguntas em linguagem natural sobre dados do restaurante.
- Relatório diário automatizado.

Entregáveis:

- MVP analítico.
- Modelos iniciais em modo sombra ou recomendação assistida.
- Agente conversacional básico.

Critério de saída:

- O gestor recebe recomendações explicáveis de compra e preço com aceitação mensurável.

---

## Fase 6 — Agentes de IA especializados e automações seguras

Duração: 6 a 10 semanas.

Objetivos:

- Criar agentes úteis para gestão completa.
- Automatizar tarefas de baixo risco.
- Manter supervisão humana para ações sensíveis.

Escopo:

- Agente Estoquista.
- Agente Precificador.
- Agente Operacional de Delivery.
- Agente de Atendimento.
- Agente Financeiro Gerencial.
- Agente de Onboarding.
- Orquestração de agentes.
- Ferramentas seguras.
- Fluxos de aprovação.
- Logs de auditoria.
- Feedback de aceite/rejeição.
- RAG para manuais, políticas internas e FAQ.
- Notificações proativas.

Entregáveis:

- Suite de agentes assistivos.
- Painel de atividades da IA.
- Política de autonomia configurável por tenant.

Critério de saída:

- Agentes produzem recomendações relevantes sem alucinação crítica e com trilha auditável.

---

## Fase 7 — Piloto comercial, billing, segurança e lançamento

Duração: 4 a 8 semanas.

Objetivos:

- Validar com clientes reais.
- Ajustar UX, performance e confiança na IA.
- Preparar cobrança recorrente.

Escopo:

- Onboarding assistido.
- Planos e assinatura.
- Limite de uso.
- Facturação.
- Hardening de segurança.
- Testes de carga.
- LGPD operacional.
- Backup e disaster recovery.
- Documentação.
- Suporte.
- Métricas de adoção.

Entregáveis:

- Versão beta pública ou fechada.
- Primeiros clientes pagantes.
- Playbook de implantação.

Critério de saída:

- Pelo menos 10 a 30 restaurantes pilotos usando o sistema diariamente, com NPS/CSAT e retenção iniciais aceitáveis.

---

## Fase 8 — Evolução pós-lançamento

Temas futuros:

- App nativo do cliente.
- App nativo do entregador com melhor offline.
- Roteirização avançada.
- Múltiplas unidades.
- Franquias.
- Integração com iFood, Rappi, WhatsApp Business API, PDV, balança, impressora fiscal, ERP.
- Emissão fiscal.
- Programa de fidelidade.
- Marketing automation.
- Compras cooperadas entre restaurantes.
- Benchmarking anonimizado por região/categoria.
- Agentes autônomos para tarefas de baixo risco.
- Marketplace de fornecedores.
- Financiamento/compra antecipada baseada em risco, se houver regulatório adequado.

---

## 13. Cronograma resumido sugerido

| Fase | Duração estimada | Principal entrega |
|---|---:|---|
| 0. Descoberta | 2–4 semanas | Blueprint, protótipo, backlog |
| 1. Fundação | 4–6 semanas | Multi-tenant e cadastros |
| 2. Pedidos | 5–7 semanas | Venda ponta a ponta |
| 3. Delivery | 4–6 semanas | Entrega própria operacional |
| 4. Estoque/Compras | 5–7 semanas | Estoque confiável e sugestão básica |
| 5. Analytics/IA | 6–8 semanas | Previsão, preço, dashboards |
| 6. Agentes | 6–10 semanas | Assistentes especializados |
| 7. Piloto/Launch | 4–8 semanas | Clientes reais, billing, segurança |

Total aproximado:

- MVP comercial enxuto: 5 a 7 meses.
- Plataforma robusta com IA e agentes: 8 a 12 meses.

---

## 14. Equipe recomendada

## Equipe mínima viável

- 1 Product Owner/Gestor de Produto.
- 1 Tech Lead/Arquiteto.
- 2 Desenvolvedores Full-stack.
- 1 Desenvolvedor Mobile.
- 1 Designer UX/UI.
- 1 Engenheiro de Dados/ML.
- 1 Especialista em IA/LLM, pode ser o mesmo de dados em parte do tempo.
- 1 DevOps/SRE, pode ser fractional.
- 1 QA/Testes, pode ser compartilhado.
- Consultoria jurídica/LGPD.
- Consultoria contábil/fiscal, se for emitir nota ou integrar ERP.

## Equipe ideal para velocidade maior

- 2 Full-stack sênior.
- 2 Full-stack pleno.
- 1 Mobile.
- 1 Data Engineer.
- 1 ML Engineer.
- 1 AI Engineer/Agent specialist.
- 1 DevOps.
- 1 QA automation.
- 1 UX/UI.
- 1 PM.
- 1 Customer Success para piloto.

---

## 15. Governança do projeto

Recomenda-se operar em sprints de 2 semanas.

Cerimônias:

- Sprint planning.
- Daily curta.
- Review/demo quinzenal com stakeholders.
- Retrospectiva.
- Backlog refinement semanal.
- Comitê de risco/IA mensal.
- Steering committee quinzenal ou mensal.

Documentos vivos:

- PRD.
- Arquitetura de solução.
- Modelo de dados.
- Glossário de negócio.
- Política de IA.
- Plano de testes.
- Runbook de operação.
- Registro de riscos.
- Métricas de produto.

Critério importante: nenhuma feature de IA vai para produção sem:

- Caso de teste.
- Métrica de sucesso.
- Plano de rollback.
- Trilha de auditoria.
- Aprovação humana para ações sensíveis.

---

## 16. Estimativa de investimento

Valores dependem muito de região, modelo de contratação, escopo e maturidade da equipe. Abaixo, faixas estimativas em BRL para orientação de planejamento.

## Opção A — MVP enxuto, time pequeno, 5 a 7 meses

Faixa: **R$ 250.000 a R$ 500.000**

Inclui:

- Web admin.
- PWA cliente.
- PWA operacional e entregador.
- Pedidos.
- Estoque básico.
- Compras por regra.
- Dashboard.
- IA assistiva simples.
- Integração de pagamento.
- Piloto fechado.

Não inclui necessariamente:

- Agentes avançados.
- Roteirização complexa.
- App nativo loja.
- Fiscal completo.
- Múltiplas unidades.

## Opção B — Plataforma completa com IA e agentes, 8 a 12 meses

Faixa: **R$ 650.000 a R$ 1.300.000+**

Inclui:

- Tudo do MVP.
- Modelos preditivos.
- Prescrição de compra/preço.
- Agentes especializados.
- Analytics mais maduro.
- Billing SaaS.
- Segurança reforçada.
- Onboarding automatizado.
- Suporte e observabilidade.
- Piloto maior e lançamento comercial.

## Custos recorrentes estimados pós-lançamento

Dependendo do volume:

- Infraestrutura cloud: R$ 3.000 a R$ 25.000+/mês.
- LLM/APIs de IA: R$ 1.000 a R$ 20.000+/mês, conforme uso.
- PSP/payment: taxas por transação.
- WhatsApp/maps/SMS: variável.
- Equipe mínima de manutenção: R$ 30.000 a R$ 120.000+/mês, conforme tamanho.

Esses valores são ordens de grandeza para planejamento, não proposta comercial.

---

## 17. KPIs de produto e negócio

## KPIs do restaurante cliente

- Acuracidade de estoque.
- Taxa de ruptura.
- Percentual de desperdício.
- Giro de estoque.
- Custo de mercadoria vendida, CMV.
- Margem de contribuição por prato.
- Tempo médio de entrega.
- Taxa de atraso.
- Cancelamento por falta de estoque.
- Adoção das sugestões de compra.
- Adoção das sugestões de preço.
- Variação de margem após recomendações.

## KPIs do SaaS

- MRR.
- ARPU.
- Churn mensal.
- Net Revenue Retention.
- CAC.
- LTV.
- Ativação em 7/14/30 dias.
- Número de pedidos processados.
- GMV, se houver pagamento online.
- NPS/CSAT.
- Tempo de suporte por ticket.
- Uso de IA por tenant.
- Taxa de aceite de recomendações.
- Taxa de erro crítico de agente.

## KPIs de IA

- MAPE/WAPE da previsão.
- Precisão da sugestão de compra.
- Redução de ruptura.
- Redução de excesso de estoque.
- Melhoria de margem.
- Confiança do usuário.
- Tempo economizado.
- Taxa de alucinação/erro em ações críticas.
- Percentual de recomendações explicadas com sucesso.

---

## 18. Riscos do projeto e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Dados cadastrais ruins | IA recomenda errado | Onboarding guiado, validações, agente de qualidade de dados |
| Baixa adesão do restaurante | Produto não roda | UX simples, mobile, automação de tarefas chatas, piloto próximo |
| Estoque impreciso | Compras e preço errados | Inventário cíclico, auditoria, alertas, integração com balança/PDV futuro |
| IA alucinar ou tomar ação errada | Perda financeira/confiança | Human-in-the-loop, limites, logs, sandbox, aprovação |
| Complexidade fiscal/pagamento | Atraso legal | Usar PSPs, começar sem emissão fiscal complexa, consultoria |
| Delivery próprio com entregador informal | Questões trabalhistas/segurança | Termos claros, seguro, checklist, orientação jurídica |
| Escopo inflado | Atraso | MVP rigoroso, MoSCoW, fases claras |
| Concorrência de marketplaces | Dificuldade de aquisição | Focar em margem, estoque, canal próprio e IA operacional |
| Performance em pico de pedidos | Perda de venda | Cache, filas, load testing, autoscaling |
| Privacidade/LGPD | Multa/perda de confiança | Privacy by design, DPO, retenção, consentimento, criptografia |

---

## 19. Segurança, LGPD e compliance

O sistema lidará com dados pessoais de clientes, entregadores, funcionários e dados financeiros dos restaurantes.

Medidas mínimas:

- Criptografia em trânsito e repouso.
- Controle de acesso baseado em papel.
- MFA para administradores.
- Logs de auditoria.
- Política de retenção de dados.
- Anonimização/pseudonimização para analytics.
- Consentimento quando necessário.
- Encarregado/DPO ou responsável legal.
- Contratos de operador com fornecedores de nuvem/IA.
- Testes de penetração periódicos.
- Backup e restore testado.
- Segregação lógica ou física por tenant.
- Política clara de uso de dados para treinamento de modelos.

Se houver pagamento online, considerar PCI-DSS SAQ adequado ou delegar ao PSP. Nunca armazenar dados sensíveis de cartão diretamente sem escopo de conformidade.

Para agentes de IA:

- Definir política de uso.
- Não enviar dados sensíveis desnecessariamente para LLM externo.
- Usar mascaramento/pii redaction.
- Registrar prompts, ferramentas chamadas, respostas e aprovações.
- Permitir opt-out de automações.
- Criar ambiente de avaliação antes de produção.

---

## 20. Modelo de monetização sugerido

## Planos por assinatura

### Plano Essencial

Para pequeno negócio começando com delivery próprio.

Inclui:

- 1 loja.
- Cardápio digital.
- Pedidos.
- Estoque básico.
- Delivery simples.
- Dashboard mínimo.
- Suporte padrão.

Sugestão de preço: R$ 99 a R$ 199/mês.

### Plano Profissional

Para restaurante que quer inteligência de estoque e preço.

Inclui:

- 1 a 3 lojas.
- Fichas técnicas completas.
- Sugestão de compra.
- Precificação assistida.
- Relatórios avançados.
- Agente de IA básico.
- WhatsApp/notificações.
- Suporte prioritário.

Sugestão de preço: R$ 299 a R$ 599/mês.

### Plano Enterprise/Franquia

- Múltiplas unidades.
- Permissões avançadas.
- Integrações.
- SLA.
- Agentes personalizados.
- Onboarding dedicado.
- API.
- White-label opcional.

Preço sob consulta, possivelmente R$ 999+/mês ou por volume de pedidos.

## Fontes de receita adicionais

- Taxa por pedido, se fizer sentido para pequenos.
- Add-on de IA avançada.
- Add-on de app nativo do cliente.
- Add-on de roteirização.
- Comissão sobre compras via marketplace de fornecedores, futuro.
- Serviços de implantação.
- Treinamento.
- White-label para redes/franquias.

Recomendação: evitar modelo apenas por transação no início, porque o valor principal está em gestão e margem. Assinatura por valor percebido tende a ser mais sustentável.

---

## 21. Estratégia de entrada no mercado

## Nicho inicial mais promissor

Começar com um segmento específico facilita mensagem, onboarding e modelo de dados.

Sugestões:

1. Hamburguerias artesanais.
2. Pizzarias.
3. Marmitarias fit.
4. Dark kitchens.
5. Cafeterias/confeitarias.

Para estoque e ficha técnica, hamburguerias e pizzarias são bons porque têm insumos recorrentes, combinações e margens sensíveis.

## Oferta para pilotos

- 60 a 90 dias grátis ou com desconto.
- Onboarding assistido.
- Compromisso de feedback semanal.
- Acesso antecipado a agentes de IA.
- Case de sucesso em troca.

## Mensagem central

“Pare de perder dinheiro por falta de estoque, compra errada e preço sem análise. Tenha delivery próprio, estoque inteligente e agentes de IA cuidando da operação do seu restaurante.”

## Canais

- Prospecção direta em bairros com alta densidade de food service.
- Parceria com contadores, consultores de restaurante, suppliers.
- Conteúdo sobre margem, CMV, ruptura e delivery próprio.
- Calculadora de prejuízo por estoque mal gerenciado.
- Demonstração ao vivo com dados fictícios realistas.

---

## 22. Backlog inicial priorizado

## Épico 1 — Fundação multi-tenant

Histórias:

- Como owner, quero criar minha empresa e loja para começar a usar o sistema.
- Como admin, quero convidar usuários e definir papéis.
- Como usuário, quero recuperar minha senha com segurança.
- Como sistema, preciso isolar dados por tenant.

## Épico 2 — Cadastro de insumos e produtos

Histórias:

- Como comprador, quero cadastrar insumos com unidade e custo.
- Como gerente, quero cadastrar produtos com preço e categoria.
- Como chef, quero montar ficha técnica de cada prato.
- Como sistema, devo validar conversão de unidade.

## Épico 3 — Pedido e checkout

Histórias:

- Como cliente, quero acessar o cardápio pelo celular e fazer pedido.
- Como cliente, quero pagar via Pix ou cartão.
- Como caixa, quero ver pedidos recebidos em tempo real.
- Como cozinha, quero ver fila de preparo.
- Como sistema, devo registrar todos os eventos do pedido.

## Épico 4 — Delivery próprio

Histórias:

- Como despachante, quero atribuir pedido a um entregador.
- Como entregador, quero receber pedidos e atualizar status.
- Como cliente, quero acompanhar meu pedido.
- Como gestor, quero ver tempo de entrega por entregador.
- Como sistema, devo exigir prova de entrega.

## Épico 5 — Estoque inteligente

Histórias:

- Como sistema, devo dar baixa de insumos ao confirmar pedido.
- Como estoquista, quero registrar perda com motivo.
- Como gerente, quero fazer contagem de inventário pelo mobile.
- Como sistema, devo alertar validade próxima.
- Como comprador, quero receber sugestão de compra.

## Épico 6 — Compras

Histórias:

- Como comprador, quero transformar sugestão em pedido de compra.
- Como fornecedor, quero receber ordem de compra por PDF/e-mail, futuro.
- Como estoquista, quero registrar recebimento parcial.
- Como gestor, quero aprovar compras acima de limite.

## Épico 7 — Precificação

Histórias:

- Como gestor, quero ver custo real de cada prato.
- Como gestor, quero simular novo preço.
- Como sistema, devo sugerir faixa de preço com base em margem.
- Como gestor, quero aplicar preço sugerido com aprovação.

## Épico 8 — Analytics

Histórias:

- Como dono, quero dashboard de vendas e margem.
- Como gestor, quero ver itens com ruptura.
- Como comprador, quero ver variação de preço de insumos.
- Como admin SaaS, quero ver uso por cliente.

## Épico 9 — Agentes de IA

Histórias:

- Como gerente, quero perguntar “o que preciso comprar amanhã?” e receber resposta explicada.
- Como dono, quero relatório diário por WhatsApp.
- Como sistema, agente estoquista deve gerar sugestão de compra.
- Como gestor, quero aprovar ou rejeitar recomendação da IA.
- Como admin, quero auditar todas as ações do agente.

---

## 23. Critérios de aceite para o MVP

O MVP só deve ser considerado pronto quando:

- Um restaurante consegue cadastrar cardápio, insumos, fornecedores e fichas técnicas em menos de 4 horas com suporte.
- Um cliente consegue fazer pedido via PWA e pagar online.
- O pedido entra no painel operacional e atualiza status.
- A baixa de estoque ocorre automaticamente.
- O entregador consegue receber, executar e concluir entrega.
- A prova de entrega é registrada.
- O gestor consegue ver estoque crítico e sugestão de compra.
- O dashboard mostra vendas, margem por prato e rupturas.
- O agente inicial consegue responder perguntas básicas sobre dados do tenant com fonte.
- Não há perda de pedido em cenário de pico básico.
- Logs e auditoria estão ativos.
- Backup e restore foram testados.

---

## 24. Métricas de sucesso do MVP

Metas iniciais sugeridas para piloto:

- 80% dos pedidos do piloto passam pelo sistema.
- Acuracidade de estoque acima de 90% após 30 dias de uso.
- Redução de 10% a 25% em rupturas de insumos críticos.
- Redução de 5% a 15% em desperdício.
- Melhoria de 2 a 5 pontos percentuais em margem de contribuição em pratos monitorados.
- Tempo de fechamento/caixa reduzido em 30%.
- Taxa de aceite das sugestões de compra acima de 50%.
- NPS do piloto acima de 40.
- Menos de 1 incidente crítico por mês.

Essas metas devem ser ajustadas por segmento e maturidade do cliente.

---

## 25. Plano de testes

## Testes funcionais

- Cadastro completo.
- Ciclo do pedido.
- Pagamento.
- Cancelamento/reembolso.
- Baixa de estoque.
- Inventário.
- Compra/recebimento.
- Entrega.
- Permissões.

## Testes não funcionais

- Performance com 50, 100, 500 pedidos simultâneos, conforme expectativa.
- Resiliência a falha de pagamento/mapa/WhatsApp.
- Offline mobile.
- Segurança.
- LGPD.
- Backup/restore.
- Escalabilidade.

## Testes de IA

- Backtesting de previsão.
- Avalição de sugestão de compra contra decisão humana.
- Teste de alucinação do agente.
- Teste de ferramenta maliciosa/prompt injection.
- Teste de aprovação/rejeição.
- Teste de viés e explicabilidade.

## Testes com usuários

- 5 restaurantes no design partner.
- Observação em horário de pico.
- Entrevista pós-uso.
- Medição de tempo para tarefas críticas.
- Teste de confiança na recomendação.

---

## 26. Estrutura sugerida de sprints iniciais

## Sprint 1

- Descoberta final.
- Modelo de dados.
- Setup repo/CI/CD.
- Wireframes principais.
- Autenticação básica.

## Sprint 2

- Multi-tenant.
- Usuários/perfis.
- Cadastro de loja.
- Cadastro de insumos.

## Sprint 3

- Produtos.
- Fichas técnicas.
- Upload de imagem.
- Validações.

## Sprint 4

- PWA cliente básico.
- Carrinho.
- Endereço.
- Taxa de entrega.

## Sprint 5

- Criação de pedido.
- Painel de pedidos.
- Status.
- Notificação interna.

## Sprint 6

- Pagamento Pix/cartão sandbox.
- Conciliação simples.
- Cancelamento.

## Sprint 7

- Baixa de estoque.
- Alerta de estoque mínimo.
- Movimentações.

## Sprint 8

- Mobile cozinha/gerente.
- Fila de preparo.
- Atualização de status.

## Sprint 9

- Entregador PWA.
- Atribuição.
- Prova de entrega.

## Sprint 10

- Inventário mobile.
- Perdas.
- Validade.

## Sprint 11

- Sugestão de compra por regra.
- Pedido de compra.
- Recebimento.

## Sprint 12

- Dashboard de vendas/margem.
- Relatório diário.
- Agente conversacional básico.

Depois disso, entrar em ciclos de IA, agentes, billing e piloto.

---

## 27. Decisões arquiteturais importantes

### Começar com monólito modular

Microserviços desde o início podem atrasar. Melhor criar módulos bem separados:

- identity.
- catalog.
- orders.
- inventory.
- purchasing.
- delivery.
- pricing.
- analytics.
- ai-agents.
- billing.
- notifications.

Se necessário, extrair serviços depois.

### Multi-tenancy

Para começar, banco compartilhado com tenant_id e Row-Level Security é mais simples e barato. Para clientes enterprise, considerar schema isolado ou banco dedicado.

### Event-driven para estoque e pedidos

Baixa de estoque não deve ser feita de forma frágil no request HTTP. Usar eventos/idempotência para evitar duplicidade.

### Offline-first no mobile

Cozinha e entregador podem perder internet. O app deve permitir ações locais e sincronizar depois, com resolução de conflito clara.

### IA como camada auxiliar, não crítica

No início, a IA não pode bloquear venda ou compra. Se o modelo falhar, o sistema deve cair para regras determinísticas.

### Explicabilidade obrigatória

Toda recomendação deve mostrar:

- Dados usados.
- Suposições.
- Fórmula/regra.
- Confiança.
- Impacto estimado.
- Botão de aprovar/editar/rejeitar.

---

## 28. Exemplo de fluxo completo do produto

1. O restaurante cadastra o insumo “queijo cheddar” com unidade kg, custo R$ 45/kg, validade 15 dias, estoque atual 3 kg, mínimo 2 kg.
2. Cadastra o produto “X-Burger” com ficha técnica usando 30 g de queijo.
3. O cliente acessa o cardápio via PWA e pede 2 X-Burgers.
4. O sistema valida estoque, reserva 60 g de queijo, cobra pagamento e envia para cozinha.
5. A cozinha prepara e marca pronto.
6. O despachante atribui a um entregador.
7. O entregador inicia entrega, atualiza status e anexa foto da entrega.
8. O sistema dá baixa definitiva no estoque, atualiza custo médio e registra receita.
9. No fim do dia, o agente estoquista analisa consumo e prevê necessidade para amanhã.
10. O sistema sugere comprar 5 kg de queijo porque previsão de consumo é 4,2 kg, estoque restante é 1,1 kg e lead time é 1 dia.
11. O gerente aprova pelo mobile.
12. O agente financeiro projeta impacto no caixa e alerta se ultrapassar orçamento.
13. O dashboard mostra margem do X-Burger e sugere testar preço de R$ 29,90 para melhorar contribuição.

---

## 29. Diferenciais competitivos a proteger

O produto pode ser copiado superficialmente, mas dificilmente copiado se construir:

- Base de dados proprietária de consumo, estoque, preço e operação.
- Modelos calibrados por segmento: pizzaria, hamburgueria, marmitaria etc.
- Agentes com workflows profundos, não apenas chat.
- Rede de fornecedores, se houver marketplace futuro.
- Integrações com PDV, balança, impressora, WhatsApp, PSP e fiscal.
- Confiança do cliente por explicabilidade e resultados mensuráveis.
- Onboarding rápido e automatizado.
- Comunidade e benchmarks anonimizados.

---

## 30. Plano de 30, 60 e 90 dias

## Primeiros 30 dias

- Realizar entrevistas com 10 a 20 restaurantes.
- Definir segmento inicial.
- Mapear fluxo atual de pedido, estoque, compra e entrega.
- Criar modelo de dados v1.
- Produzir protótipo navegável.
- Definir stack e infraestrutura.
- Montar squad inicial.
- Recrutar 3 a 5 design partners.

Entrega: blueprint validado e backlog de MVP.

## Dias 31 a 60

- Implementar fundação multi-tenant.
- Cadastrar produtos, insumos, fornecedores e fichas técnicas.
- Criar PWA de cardápio.
- Implementar pedidos e painel operacional.
- Iniciar integração de pagamento sandbox.
- Começar módulo de estoque.

Entrega: fluxo de pedido básico funcionando em ambiente controlado.

## Dias 61 a 90

- Completar checkout e pagamento.
- Implementar delivery próprio mínimo.
- Ativar baixa automática de estoque.
- Criar dashboard inicial.
- Implementar sugestão de compra por regra.
- Iniciar treinamento/avaliação de modelo de previsão simples.
- Colocar 2 a 5 restaurantes em piloto interno.

Entrega: MVP testável com usuários reais.

---

## 31. Recomendações finais de produto

1. **Não comece tentando ser todos os módulos.** Comece com pedido + estoque + entrega própria + sugestão simples.
2. **A ficha técnica é o ativo mais importante.** Sem ela, não há custo real, baixa inteligente nem previsão confiável.
3. **IA deve explicar, não apenas recomendar.** O dono do restaurante precisa confiar.
4. **Agentes devem ter autonomia limitada.** Primeiro assistente, depois automação de baixo risco.
5. **Mobile é crítico.** Cozinha e entregador não vivem no desktop.
6. **Onboarding precisa ser obsessivamente simples.** Se o cliente não cadastrar estoque e fichas, o diferencial morre.
7. **Meça resultado financeiro.** Redução de ruptura, desperdício e melhoria de margem vendem mais que “tecnologia de IA”.
8. **Comece com PWA para cliente e entregador.** App nativo pode vir depois, quando houver tração.
9. **Construa camada de dados desde o primeiro dia.** Logs estruturados e eventos são insumo para IA.
10. **Use pilotos pagos ou semi-pagos.** Cliente gratuito demais pode não dar feedback sério.

---

## 32. Resumo executivo do plano

O projeto deve desenvolver um SaaS multi-tenant para delivery próprio com foco em restaurantes e pequenos negócios alimentícios. A plataforma unirá gestão de pedidos, operação de entrega, controle de estoque por ficha técnica, compras inteligentes, precificação assistida e agentes de IA especializados.

A construção recomendada segue em fases:

1. Descoberta e blueprint.
2. Fundação multi-tenant e cadastros.
3. Pedidos e checkout.
4. Delivery próprio.
5. Estoque e compras.
6. Analytics e IA preditiva/prescritiva.
7. Agentes de IA assistivos.
8. Piloto, billing, segurança e lançamento.

O MVP deve provar que o sistema reduz ruptura, melhora acuracidade de estoque, economiza tempo do gestor e gera recomendações confiáveis de compra e preço. A versão plena deve se diferenciar pela combinação de operação de delivery, inteligência de supply chain alimentar e agentes de IA auditáveis, com supervisão humana.

Se quiser, no próximo passo eu posso transformar isso em:

- **PRD completo**;
- **backlog em formato Ágil/Jira**;
- **modelo de dados detalhado**;
- **arquitetura técnica com diagramas**;
- **estimativa de horas por sprint**;
- **pitch para investidor**;
- **plano comercial e de precificação SaaS**.
