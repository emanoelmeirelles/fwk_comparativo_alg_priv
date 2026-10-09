# fwk_comparativo_alg_priv

Framework para comparar algoritmos de privacidade em consultas espaço-textuais sob as mesmas condições experimentais. Este repositório acompanha a dissertação de mestrado *Preservação de Privacidade em Consultas Espaço-Textuais* (PGCC/UEFS, 2026), de Emanoel Meirelles, orientada por João Batista da Rocha Junior. O framework está descrito no Capítulo 4 da dissertação, e as figuras do Capítulo 5 foram geradas por este código.

O repositório contém o framework. Os algoritmos comparados na dissertação não fazem parte dele.

## Como o framework funciona

Cada algoritmo participante grava um CSV com uma linha por execução. O framework lê dois CSVs, verifica se seguem o formato de dados, agrega as execuções e gera os gráficos comparativos. Ele não recalcula métricas e não preenche dado ausente: se faltar uma coluna obrigatória, a execução para com erro. Se os dois arquivos declararem o mesmo algoritmo, ou se os valores testados em um experimento não coincidirem, a execução também para.

Colunas obrigatórias (`COLUNAS_OBRIGATORIAS` em `framework_comparativo_v7.py`):

`algorithm`, `run_id`, `experimento`, `cidade`, `palavra_chave`, `raio_busca_m`, `n_total`, `Gen_ms`, `Filter_ms`, `ttfb_ms_total`, `download_ms_total`, `parse_ms_total`, `bytes_fio`, `entropy`, `dist_min_usuario_m`, `precision`, `recall`, `n_ground_truth`

Além delas, o arquivo precisa ter `repeticao` e `localizacao_id`. Na dissertação, cada algoritmo rodou duas vezes seguidas na mesma localização, e só a segunda repetição entra na comparação.

Colunas opcionais: `Temporal_ms`, `n_rodadas`, `bytes_corpo`, `n_requisicoes`, `rede_ms_total` e `centroide_erro_m`. Quando uma delas falta, o framework preenche um valor padrão ou a deriva das outras, e informa isso na saída.

O tempo total de cada execução é `Gen_ms + Filter_ms + Temporal_ms + rede_ms_total`, e `rede_ms_total` é a soma de TTFB, download e parse.

## Arquivos

| Arquivo | Papel |
|---|---|
| `framework_comparativo_v7.py` | Validação, agregação e geração dos gráficos |
| `metricas.py` | Módulo de métricas que os algoritmos participantes devem usar (entropia, precisão e recall, erro do centroide, distância haversine, filtragem local) |
| `config_padrao.py` | Parâmetros dos experimentos da dissertação; o comparador lê dele a ordem das palavras-chave |

## Requisitos

Python 3 e os pacotes do `requirements.txt`:

```
pip install -r requirements.txt
```

## Uso

```
python3 framework_comparativo_v7.py resultados_algoritmo_a.csv resultados_algoritmo_b.csv
```

As figuras são gravadas em `graficos_osmlocal_rep2/`, uma pasta por experimento (cidade, palavra-chave, raio de busca e número de *dummies*).

## Condições da rodada da dissertação

Os dados de pontos de interesse vieram de uma instância local da API Overpass em Docker (imagem `wiktorn/overpass-api`). O banco foi carregado com os extratos da Geofabrik da Bahia e de São Paulo de 30/09/2026 (`timestamp=2026-09-30T20:22:42Z`). Os extratos foram recortados com `osmium extract -s smart` em caixas de ±0,05° em torno do centro de cada cidade (Salvador, Feira de Santana e São Paulo). O banco ficou congelado, sem atualizações.
