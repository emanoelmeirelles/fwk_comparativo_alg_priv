# -*- coding: utf-8 -*-
"""
framework_comparativo.py
=========================
Framework de comparação de algoritmos de privacidade espaço-textual.

Recebe dois CSVs (um por algoritmo), no schema definido em
SCHEMA_FRAMEWORK.md, e produz os 6 gráficos comparativos. Não calcula
métrica própria, não injeta constante, não estima dado ausente.

Uso:
    python framework_comparativo.py resultados_liu.csv resultados_hibrido.csv

Se qualquer coluna obrigatória estiver ausente, o script para com erro
explícito — nunca completa com zero ou valor assumido.
"""
import sys
import os
import pandas as pd
import matplotlib.pyplot as plt

REQUIRED_COLUMNS = [
    "algorithm", "run_id", "n_total",
    "Gen_ms", "Query_ms", "Filter_ms",
    "comm_cost_bytes", "entropy", "precision", "recall",
]

OUT_DIR = "graficos_framework"
FIGSIZE = (9, 6)


def carregar_e_validar(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_csv(path)

    faltando = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if faltando:
        raise ValueError(
            f"'{path}' não atende ao contrato do framework.\n"
            f"Colunas obrigatórias ausentes: {faltando}\n"
            f"Ver SCHEMA_FRAMEWORK.md. O framework não preenche dado ausente."
        )

    if df["algorithm"].nunique() != 1:
        raise ValueError(
            f"'{path}' contém mais de um valor em 'algorithm': "
            f"{df['algorithm'].unique().tolist()}. Cada CSV deve representar "
            f"um único algoritmo."
        )

    return df


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula Total_ms por linha (soma pura, sem constante) e agrega por n_total."""
    df = df.copy()
    df["Total_ms"] = df["Gen_ms"] + df["Query_ms"] + df["Filter_ms"]

    agg = df.groupby("n_total", as_index=False).agg({
        "Gen_ms": "mean",
        "Query_ms": "mean",
        "Filter_ms": "mean",
        "Total_ms": "mean",
        "comm_cost_bytes": "mean",
        "entropy": "mean",
        "precision": "mean",
        "recall": "mean",
    })
    agg["algorithm"] = df["algorithm"].iloc[0]
    return agg.sort_values("n_total")


def checar_alinhamento_n(dfs: dict):
    """Avisa (não impede) se os algoritmos foram testados com n_total diferentes."""
    conjuntos = {nome: set(df["n_total"]) for nome, df in dfs.items()}
    nomes = list(conjuntos.keys())
    if conjuntos[nomes[0]] != conjuntos[nomes[1]]:
        print(
            f"[AVISO] '{nomes[0]}' e '{nomes[1]}' têm valores de n_total "
            f"diferentes: {sorted(conjuntos[nomes[0]])} vs "
            f"{sorted(conjuntos[nomes[1]])}. Os pontos não vão coincidir no "
            f"eixo X — isso indica que os experimentos não seguiram o mesmo "
            f"protocolo (ver SCHEMA_FRAMEWORK.md, pré-condição 4)."
        )


def _plot_duas_series(dfs: dict, coluna: str, ylabel: str, fname: str,
                       transformar=None):
    fig, ax = plt.subplots(figsize=FIGSIZE)
    cores = ["tab:red", "tab:green", "tab:blue", "tab:orange"]
    for i, (nome, df) in enumerate(dfs.items()):
        y = transformar(df[coluna]) if transformar else df[coluna]
        ax.plot(df["n_total"], y, marker="o", color=cores[i % len(cores)],
                label=nome)
    ax.set_xlabel("Número de Dummies (n)")
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    os.makedirs(OUT_DIR, exist_ok=True)
    plt.savefig(os.path.join(OUT_DIR, fname), dpi=150)
    plt.close()
    print(f"  Salvo: {fname}")


def gerar_graficos(dfs: dict):
    os.makedirs(OUT_DIR, exist_ok=True)

    _plot_duas_series(dfs, "Total_ms", "Tempo Total (ms)",
                       "fig_tempo_total_execucao.png")

    _plot_duas_series(dfs, "entropy", "Entropia (bits)",
                       "fig_entropia.png")

    _plot_duas_series(dfs, "Query_ms", "Tempo de Resposta (ms)",
                       "fig_tempo_medio_consulta.png")

    _plot_duas_series(dfs, "comm_cost_bytes", "Dados Transferidos (KB)",
                       "fig_custo_comunicacao.png",
                       transformar=lambda s: s / 1024)

    # Probabilidade de rastreamento: curva TEÓRICA (1/n), não é dado medido.
    # Calculada a partir de n_total apenas, e rotulada como referência.
    fig, ax = plt.subplots(figsize=FIGSIZE)
    cores = ["tab:red", "tab:green", "tab:blue", "tab:orange"]
    for i, (nome, df) in enumerate(dfs.items()):
        ax.plot(df["n_total"], 1 / df["n_total"], marker="o",
                color=cores[i % len(cores)], linestyle="--",
                label=f"{nome} (1/n — teórico)")
    ax.set_xlabel("Número de Dummies (n)")
    ax.set_ylabel("Probabilidade")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "fig_probabilidade_rastreamento.png"), dpi=150)
    plt.close()
    print("  Salvo: fig_probabilidade_rastreamento.png "
          "(curva teórica 1/n, não é métrica medida)")

    _plot_duas_series(dfs, "Gen_ms", "Tempo de Geração Local (ms)",
                       "fig_tempo_geracao_local.png")


def main():
    if len(sys.argv) != 3:
        print("Uso: python framework_comparativo.py <csv_algoritmo_A> <csv_algoritmo_B>")
        sys.exit(1)

    path_a, path_b = sys.argv[1], sys.argv[2]

    df_a_raw = carregar_e_validar(path_a)
    df_b_raw = carregar_e_validar(path_b)

    nome_a = df_a_raw["algorithm"].iloc[0]
    nome_b = df_b_raw["algorithm"].iloc[0]

    if nome_a == nome_b:
        raise ValueError(
            f"Os dois arquivos declaram o mesmo algoritmo ('{nome_a}'). "
            f"O framework compara dois algoritmos distintos."
        )

    dfs = {
        nome_a: preparar(df_a_raw),
        nome_b: preparar(df_b_raw),
    }

    checar_alinhamento_n(dfs)
    gerar_graficos(dfs)
    print("\nGráficos comparativos gerados sem fabricação de dado.")


if __name__ == "__main__":
    main()
