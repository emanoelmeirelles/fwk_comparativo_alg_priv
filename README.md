# fwk_comparativo_alg_priv
# Dicionário de Dados — Framework de Comparação de Algoritmos de Privacidade

## Princípio

O framework **lê, agrega e plota**. Não recalcula métrica com fórmula própria,
não injeta constante, não estima o que não foi medido. Se uma coluna
obrigatória estiver ausente ou com tipo errado, o framework **falha com erro
explícito** — nunca preenche com zero, média ou suposição silenciosa.

Cada algoritmo  entrega **um CSV próprio**, um registro por execução individual (não pré-agregado — a agregação por `n_total` é responsabilidade do framework, não do algoritmo).

---

## Schema obrigatório — `resultados_<algoritmo>.csv`

| Coluna | Tipo | Unidade | Como deve ser obtida | Quem calcula |
|---|---|---|---|---|
| `algorithm` | string | — | Rótulo fixo identificando o algoritmo (ex.: `"Liu_Wang_2022"`, `"Hibrido_Multiestrategia"`) | Script do algoritmo |
| `run_id` | int | — | Índice sequencial da simulação (0, 1, 2, ...) | Script do algoritmo |
| `n_total` | int | contagem | Número **real** de dummies gerados nesta execução (pode divergir do `n` solicitado) | Script do algoritmo |
| `Gen_ms` | float | milissegundos | `time.perf_counter()` cronometrando **apenas** a chamada da função de geração de dummies | Script do algoritmo |
| `Query_ms` | float | milissegundos | `time.perf_counter()` cronometrando o envio real das consultas (uma por dummy) e recebimento das respostas — **medição real de rede/API**, nunca constante multiplicada por n | Script do algoritmo |
| `Filter_ms` | float | milissegundos | `time.perf_counter()` cronometrando a filtragem local (dedup + filtro espacial + filtro textual) | Script do algoritmo |
| `comm_cost_bytes` | int | bytes | Tamanho real do payload recebido do servidor (`len(json.dumps(payload).encode('utf-8'))` ou equivalente) — nunca `constante × n_pois` | Script do algoritmo |
| `entropy` | float | bits | `metrics_core.shannon_entropy_spatial(dummies, center, radius_m)` | **Obrigatoriamente** `metrics_core.py` |
| `precision` | float | [0,1] | `metrics_core.evaluate_precision_recall(...)` | **Obrigatoriamente** `metrics_core.py` |
| `recall` | float | [0,1] | `metrics_core.evaluate_precision_recall(...)` | **Obrigatoriamente** `metrics_core.py` |

`Total_ms` **não é uma coluna de entrada**. O framework calcula
`Total_ms = Gen_ms + Query_ms + Filter_ms` por linha, depois agrega. Nenhum
algoritmo deve entregar `Total_ms` pronto — isso abriria espaço para inflar
ou reduzir um dos três componentes sem que o framework perceba.

---

## Pré-condições para comparação válida (contrato, não schema)

Estas condições não aparecem como coluna, mas invalidam a comparação se
forem diferentes entre os dois CSVs:

1. **Mesmo dataset de POIs** (mesmo snapshot OSM, mesma cidade, mesmo raio de
   extração) para as execuções de ambos os algoritmos no mesmo cenário.
2. **Mesmo `center` e `radius_m`** passados para `shannon_entropy_spatial()`
   — caso contrário a grade de entropia cobre áreas diferentes e os números
   deixam de ser comparáveis mesmo vindo da mesma função.
3. **Mesmo `tolerance_m`** (raio de precisão) passado para
   `evaluate_precision_recall()` nos dois algoritmos.
4. **Mesmos valores de `n`** testados (ex.: `{5,10,15,20,25,30}`) nos dois
   CSVs, para que o `groupby("n_total")` produza pontos alinhados no eixo X.

O framework valida (1)–(4) na medida do possível (choca `n_total` presentes
nos dois arquivos) e avisa se um dos algoritmos tem valores de `n` que o
outro não tem — mas não pode validar sozinho se o dataset OSM foi o mesmo;
isso é responsabilidade de quem roda os experimentos.

---

## Mapeamento gráfico → colunas usadas

| Gráfico | Colunas de entrada | Cálculo do framework |
|---|---|---|
| Tempo Total de Execução | `Gen_ms`, `Query_ms`, `Filter_ms` | soma por linha, depois média por `n_total` |
| Entropia | `entropy` | média por `n_total` |
| Tempo Médio de Consulta | `Query_ms` | média por `n_total` |
| Custo de Comunicação | `comm_cost_bytes` | média por `n_total`, convertida para KB |
| Probabilidade de Rastreamento | `n_total` | `1/n_total` — **curva teórica**, rotulada como referência, não como métrica medida |
| Tempo de Geração Local | `Gen_ms` | média por `n_total` |




