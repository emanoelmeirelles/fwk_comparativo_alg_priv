# -*- coding: utf-8 -*-
"""
framework_comparativo_v6.py
============================
Compara dois algoritmos a partir dos CSVs da v6 (consulta individual) e gera
os graficos dos quatro experimentos OFAT.

MUDA EM RELACAO AO FRAMEWORK v5
-------------------------------
  * Contrato de colunas novo. Query_ms e Network_ms nao existem mais: nao ha
    consulta a indice local, e o tempo de rede passou de MODELADO
    (RTT*n + bytes/banda) para MEDIDO por resposta.
  * Custo de comunicacao usa `bytes_fio` -- o corpo comprimido como veio no
    fio. O JSON descomprimido superestima em ~7,5x.
  * DOIS GRAFICOS NOVOS por experimento: precisao e cobertura (recall).
  * Grafico novo de decomposicao do tempo de rede (TTFB / download / parse),
    que e o que a v6 passou a medir e a v5 nao tinha como mostrar.
  * Grafico novo de distancia minima ao usuario -- e onde os dois algoritmos
    de fato divergem, e era invisivel no deck anterior.
  * Ground truth vazio NAO entra como zero. Linhas com precisao/recall
    indefinidos sao contadas e reportadas separadamente.

O QUE ELE NAO FAZ
-----------------
Nao calcula metrica propria, nao injeta constante, nao estima dado ausente.
Coluna obrigatoria faltando -> erro explicito e parada.

OSMLOCAL (01/10/2026)
--------------------
  * So a repeticao 2 entra (pedido do orientador: cada algoritmo roda duas
    vezes seguidas na mesma localizacao e so a segunda vale). Os CSVs sem a
    coluna `repeticao` sao recusados, em vez de agregados em silencio.
  * Barras de desvio-padrao ligadas em todas as figuras: desvio entre as
    localizacoes do mesmo ponto do OFAT (decisao de 01/10 (2)).
  * Eixo "Sobrecarga (ms)" passa a "Tempo de Execucao Local (ms)" (decisao
    de 01/10 (7)); "Erro do centroide" passa a "Erro de ataque central"
    (convencao de 12/09).

Uso:
    python3 framework_comparativo_v7.py \\
        resultados_producao/resultados_liu_osmlocal.csv \\
        resultados_producao/resultados_multiestrategia_osmlocal.csv
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config_padrao

# =============================================================================
# ESTILO -- mantido identico ao do framework v5 para as figuras novas casarem
# com as que ja estao no texto. Fonte 36 corresponde a subfigura entrando com
# width=0.46\textwidth. Se o width no .tex mudar, esta fonte muda junto:
#   0.46\textwidth -> 36  |  0.8\textwidth -> 21  |  0.9\textwidth -> 19
# =============================================================================
plt.rcParams.update({
    "font.size": 16, "axes.titlesize": 16, "axes.labelsize": 16,
    "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 15,
})

FIGSIZE = (9, 6)
OUT_DIR = "graficos_osmlocal_rep2"
# So esta repeticao entra nas figuras e no relatorio (ver docstring).
REPETICAO_VALIDA = 2
LARGURA_BARRA = 0.22
ESPACO_ENTRE_GRUPOS = 0.30
NOMES_EXIBICAO = {"Hibrido_Multiestrategia": "Multiestratégia",
                  "Liu_Wang_2022": "Liu e Wang (2022)"}

# Cor e estilo POR NOME DE ALGORITMO, nunca por posicao na linha de comando.
# Ate 24/08 eram listas indexadas pela ordem dos argumentos: trocar a ordem dos
# dois CSVs invertia a cor das 40 figuras, sem erro e sem aviso, e qualquer
# frase do texto que citasse cor passava a apontar para o algoritmo errado.
# Convencao fixada com o autor em 24/08: Liu vermelho com linha solida e
# bolinha cheia; Multiestrategia verde com linha tracejada e quadrado vazado.
# O tracejado nao e enfeite: e o que mantem as duas series separaveis na
# impressao em preto e branco e para quem confunde vermelho e verde.
CORES_POR_ALGORITMO = {
    "Liu_Wang_2022": "tab:red",
    "Hibrido_Multiestrategia": "tab:green",
}
ESTILOS_POR_ALGORITMO = {
    "Liu_Wang_2022": {"marker": "o", "linestyle": "-", "linewidth": 2.2,
                      "markersize": 7},
    "Hibrido_Multiestrategia": {"marker": "s", "linestyle": "--",
                                "linewidth": 1.6, "markersize": 11,
                                "markerfacecolor": "none"},
}
# Ordem canonica de desenho: define quem aparece primeiro na legenda e qual
# barra fica a esquerda nos graficos categoricos. Sem isso, trocar a ordem dos
# CSVs na linha de comando ainda mudava a figura, agora so no arranjo.
ORDEM_CANONICA = ["Liu_Wang_2022", "Hibrido_Multiestrategia"]


def ordenar_series(dfs):
    """Reordena o dicionario de series pela ORDEM_CANONICA. Algoritmo fora da
    lista vai para o fim, em ordem alfabetica, de forma estavel."""
    def chave(nome):
        return (ORDEM_CANONICA.index(nome) if nome in ORDEM_CANONICA
                else len(ORDEM_CANONICA), nome)
    return {k: dfs[k] for k in sorted(dfs, key=chave)}


# Reserva para um algoritmo novo que ainda nao esteja no dicionario.
CORES_RESERVA = ["tab:blue", "tab:orange", "tab:purple"]
ESTILOS_RESERVA = [{"marker": "^", "linestyle": "-.", "linewidth": 1.8,
                    "markersize": 9}]


def cor_de(nome, i):
    if nome not in CORES_POR_ALGORITMO:
        print(f"  [AVISO] algoritmo '{nome}' sem cor fixada; usando reserva.")
        return CORES_RESERVA[i % len(CORES_RESERVA)]
    return CORES_POR_ALGORITMO[nome]


def estilo_de(nome, i):
    if nome not in ESTILOS_POR_ALGORITMO:
        return dict(ESTILOS_RESERVA[i % len(ESTILOS_RESERVA)])
    return dict(ESTILOS_POR_ALGORITMO[nome])

# =============================================================================
# CONTRATO DE COLUNAS DA v6
# =============================================================================
# 18 obrigatorias. So entra aqui a coluna que o comparador NAO consegue
# derivar e sem a qual alguma figura deixa de existir. O framework se propoe
# a comparar qualquer produtor aderente ao dicionario -- cada coluna
# obrigatoria a mais encarece essa promessa.
COLUNAS_OBRIGATORIAS = [
    # identificacao e eixo OFAT: sem isso nao da para separar as linhas por
    # experimento nem saber em que ponto os demais parametros estavam
    "algorithm", "run_id", "experimento", "cidade", "palavra_chave",
    "raio_busca_m", "n_total",
    # custo local medido
    "Gen_ms", "Filter_ms",
    # rede medida, decomposta: e a decomposicao que permite dizer que o tempo
    # e dominado por fila no servidor, e nao por transferencia
    "ttfb_ms_total", "download_ms_total", "parse_ms_total",
    # custo de comunicacao: o valor NO FIO, comprimido
    "bytes_fio",
    # privacidade e utilidade
    "entropy", "dist_min_usuario_m",
    "precision", "recall", "n_ground_truth",
]

# Opcionais: ou o comparador deriva, ou a coluna e informativa, ou ela so
# existe em um dos algoritmos. Ausencia e preenchida e REPORTADA na saida,
# nunca em silencio.
COLUNAS_OPCIONAIS = {
    "Temporal_ms": 0.0,   # so a Multiestrategia tem codificacao temporal
    "n_rodadas": 1,       # lotes de fragmentacao; 1 = envio sem fragmentar
    "bytes_corpo": None,  # payload descomprimido; informativo, nao vira figura
    "n_requisicoes": None,  # derivavel de n_total quando e 1 consulta/dummy
    "rede_ms_total": None,  # soma de ttfb + download + parse
    "centroide_erro_m": None,  # erro do centroide: resultado principal do trabalho
}


def completar_derivadas(df, caminho):
    """Calcula as opcionais que o comparador sabe derivar.

    Mantem `rede_ms_total` e `n_requisicoes` fora das obrigatorias sem perder
    nada: quem produzir o CSV pode omiti-las, e quem as fornecer tem o valor
    respeitado (util se o protocolo agrupar consultas e n_requisicoes deixar
    de ser igual a n_total).
    """
    derivadas = []
    if df["rede_ms_total"].isna().all():
        df["rede_ms_total"] = (df["ttfb_ms_total"] + df["download_ms_total"]
                               + df["parse_ms_total"])
        derivadas.append("rede_ms_total = ttfb + download + parse")
    if df["n_requisicoes"].isna().all():
        df["n_requisicoes"] = df["n_total"]
        derivadas.append("n_requisicoes = n_total")
    if df["bytes_corpo"].isna().all():
        df["bytes_corpo"] = df["bytes_fio"]
        derivadas.append("bytes_corpo = bytes_fio (sem info de compressao)")
    if derivadas:
        print(f"  [{os.path.basename(caminho)}] derivadas: "
              f"{'; '.join(derivadas)}")
    return df

EXPERIMENTO_CONFIG = {
    "dataset": {"eixo": "cidade", "tipo": "categorico", "xlabel": "Cidade",
                "ordem": ["Feira de Santana", "Salvador", "São Paulo"]},
    "palavra_chave": {"eixo": "palavra_chave", "tipo": "categorico",
                      "xlabel": "Palavra-chave",
                      "ordem": list(config_padrao.PALAVRAS_CHAVE)},
    "raio_busca": {"eixo": "raio_busca_m", "tipo": "continuo",
                   "xlabel": "Raio de Busca (m)", "ordem": None},
    "n_dummies": {"eixo": "n_total", "tipo": "continuo",
                  "xlabel": "Número de Dummies (n)", "ordem": None},
}

# (coluna, ylabel, arquivo, transformacao, log_y, barras_de_erro)
METRICAS = [
    # Erro do centroide: distancia entre o centroide do conjunto enviado e a
    # posicao real. E o resultado principal do trabalho (decisao de 22/08) e
    # responde ao objetivo especifico 3. Vem primeiro por isso.
    ("centroide_erro_m", "Erro de ataque central (m)", "fig_erro_centroide.png",
     None, False, True),
    ("precision", "Precisão", "fig_precisao.png", None, False, True),
    ("recall", "Cobertura (Recall)", "fig_cobertura_recall.png",
     None, False, True),
    # Barras de erro (desvio-padrao das execucoes) ligadas em tudo. Com
    # SIMULATIONS>=3 elas sao a informacao mais importante da figura: a
    # entropia varia de 0,07 a 0,43 entre execucoes do mesmo ponto, e o
    # tempo varia ainda mais. Sem elas, um cruzamento de curvas parece
    # resultado quando e sobreposicao.
    ("entropy", "Entropia (bits)", "fig_entropia.png", None, False, True),
    ("bytes_fio", "Dados Transferidos (MB)", "fig_custo_comunicacao.png",
     lambda s: s / 1e6, False, True),
    ("Total_ms", "Tempo Total (s)", "fig_tempo_total_execucao.png",
     lambda s: s / 1000, False, True),
    ("dist_min_usuario_m", "Dist. mín. ao usuário (m)",
     "fig_distancia_minima.png", None, False, True),

    # --- repostas para casar com a Secao 5.2 da dissertacao ---------------
    # Sobrecarga = Gen_ms + Temporal_ms: o custo PROPRIO do metodo, o que
    # nao depende do volume devolvido pelo servidor. Escala log porque o Liu
    # fica na casa dos centesimos de ms e a Multiestrategia nos 46 ms da
    # codificacao temporal -- em escala linear a barra do Liu some.
    ("Overhead_ms", "Tempo de Execução Local (ms)", "fig_overhead_algoritmo.png",
     None, True, True),
    # Probabilidade de rastreamento efetiva 2^-H.
    # Calculada POR EXECUCAO e depois agregada -- 2^-media(H) nao e igual a
    # media(2^-H), e a diferenca aparece justamente onde a variancia e alta.
    ("prob_rastreamento", "Prob. de rastreamento",
     "fig_probabilidade_rastreamento.png", None, False, True),
]


# =============================================================================
# AUXILIARES DE LAYOUT
# =============================================================================
def _quebrar_rotulo(texto, limite=999):
    if len(texto) <= limite or " " not in texto:
        return texto
    linhas, atual = [], ""
    for p in texto.split():
        if atual and len(atual) + 1 + len(p) > limite:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    linhas.append(atual)
    return "\n".join(linhas)


def _centros(n_cat, n_ser=2):
    return np.arange(n_cat) * (n_ser * LARGURA_BARRA + ESPACO_ENTRE_GRUPOS)


def _legenda(ax):
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2,
              frameon=True, borderaxespad=0.0)


# =============================================================================
# CARGA E VALIDACAO
# =============================================================================
def carregar_e_validar(caminho):
    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    df = pd.read_csv(caminho)

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError(
            f"'{caminho}' não atende ao contrato de dados.\n"
            f"Colunas obrigatórias ausentes: {faltando}\n"
            f"O framework não preenche dado ausente.")

    preenchidas = []
    for col, padrao in COLUNAS_OPCIONAIS.items():
        if col not in df.columns:
            df[col] = padrao
            if padrao is not None:
                preenchidas.append(f"{col}={padrao}")
    if preenchidas:
        print(f"  [{os.path.basename(caminho)}] colunas opcionais ausentes, "
              f"preenchidas: {', '.join(preenchidas)}")
    df = completar_derivadas(df, caminho)

    # Repeticao: so a REPETICAO_VALIDA entra. Sem a coluna, para -- agregar
    # as duas repeticoes juntas dobraria o n e misturaria o tempo frio.
    for col in ("repeticao", "localizacao_id"):
        if col not in df.columns:
            raise ValueError(f"'{caminho}' sem a coluna '{col}': nao e CSV "
                             f"da rodada OSMlocal.")
    antes = len(df)
    df = df[df["repeticao"] == REPETICAO_VALIDA].copy()
    if df.empty:
        raise ValueError(f"'{caminho}' sem linhas com repeticao == "
                         f"{REPETICAO_VALIDA}.")
    print(f"  [{os.path.basename(caminho)}] repeticao == {REPETICAO_VALIDA}: "
          f"{len(df)} de {antes} linhas")

    if df["algorithm"].nunique() != 1:
        raise ValueError(
            f"'{caminho}' tem mais de um valor em 'algorithm': "
            f"{df['algorithm'].unique().tolist()}.")

    desconhecidos = set(df["experimento"]) - set(EXPERIMENTO_CONFIG)
    if desconhecidos:
        raise ValueError(
            f"'{caminho}' tem experimentos que o comparador não reconhece: "
            f"{sorted(desconhecidos)}.")
    return df


def preparar(df, experimento):
    """Filtra o experimento, calcula Total_ms e agrega pelo eixo.

    Total_ms = Gen + Filter + Temporal + rede medida.
    Todas as parcelas sao MEDIDAS -- nao ha mais termo modelado.
    """
    cfg = EXPERIMENTO_CONFIG[experimento]
    eixo = cfg["eixo"]
    sub = df[df["experimento"] == experimento].copy()
    if sub.empty:
        raise ValueError(f"Nenhuma linha com experimento='{experimento}'.")

    sub["Total_ms"] = (sub["Gen_ms"] + sub["Filter_ms"]
                       + sub["Temporal_ms"] + sub["rede_ms_total"])
    # Custo proprio do metodo: geracao dos dummies mais o atraso deliberado
    # da codificacao temporal. Nao inclui rede nem filtragem, que dependem do
    # volume devolvido pelo servidor e nao da tecnica.
    sub["Overhead_ms"] = sub["Gen_ms"] + sub["Temporal_ms"]
    # 2^-H por execucao, agregada depois (ver nota em METRICAS).
    sub["prob_rastreamento"] = 2.0 ** (-sub["entropy"])

    colunas = ["Gen_ms", "Filter_ms", "Temporal_ms", "Total_ms",
               "Overhead_ms", "prob_rastreamento",
               "ttfb_ms_total", "download_ms_total", "parse_ms_total",
               "rede_ms_total", "bytes_fio", "bytes_corpo", "entropy",
               "precision", "recall", "n_total", "n_requisicoes",
               "n_ground_truth", "dist_min_usuario_m", "centroide_erro_m"]

    # mean() de pandas ignora NaN. Isso e o que queremos para precisao/recall
    # (ground truth vazio = indefinido, nao zero), mas o numero de linhas
    # validas precisa ficar visivel -- por isso as contagens abaixo.
    agg = sub.groupby(eixo, as_index=False)[colunas].mean()
    desvio = sub.groupby(eixo, as_index=False)[colunas].std().fillna(0.0)
    validas = sub.groupby(eixo, as_index=False)[["precision", "recall"]].count()
    total = sub.groupby(eixo, as_index=False)["run_id"].count()

    agg["algorithm"] = sub["algorithm"].iloc[0]
    for c in colunas:
        agg[f"{c}__dp"] = desvio[c]
    agg["n_execucoes"] = total["run_id"]
    agg["n_precisao_valida"] = validas["precision"]
    agg["n_recall_valido"] = validas["recall"]

    if cfg["ordem"]:
        ordem = [v for v in cfg["ordem"] if v in set(agg[eixo])]
        agg[eixo] = pd.Categorical(agg[eixo], categories=ordem, ordered=True)
        agg = agg.sort_values(eixo).reset_index(drop=True)
    else:
        agg = agg.sort_values(eixo).reset_index(drop=True)
    return agg


def checar_alinhamento(dfs, experimento):
    eixo = EXPERIMENTO_CONFIG[experimento]["eixo"]
    conjuntos = {n: set(d[eixo].astype(str)) for n, d in dfs.items()}
    valores = list(conjuntos.values())
    if valores[0] != valores[1]:
        nomes = list(conjuntos)
        raise ValueError(
            f"Experimento '{experimento}': o eixo '{eixo}' não coincide entre "
            f"os dois algoritmos.\n  {nomes[0]}: {sorted(conjuntos[nomes[0]])}"
            f"\n  {nomes[1]}: {sorted(conjuntos[nomes[1]])}\n"
            f"Comparar pontos diferentes produziria gráfico enganoso.")


# =============================================================================
# GRAFICOS
# =============================================================================
def gerar_graficos(dfs, experimento, out_dir):
    cfg = EXPERIMENTO_CONFIG[experimento]
    eixo, tipo, xlabel = cfg["eixo"], cfg["tipo"], cfg["xlabel"]
    os.makedirs(out_dir, exist_ok=True)

    primeiro = list(dfs)[0]
    categorias = (list(dfs[primeiro][eixo].astype(str))
                  if tipo == "categorico" else None)
    valores_eixo = (None if tipo == "categorico"
                    else sorted(dfs[primeiro][eixo].unique()))

    def aplicar_eixo_x(ax, n_ser=2):
        if tipo == "categorico":
            ax.set_xticks(_centros(len(categorias), n_ser))
            ax.set_xticklabels([_quebrar_rotulo(c) for c in categorias],
                               rotation=30, ha="right", va="top")
        else:
            ax.set_xticks(valores_eixo)
            ax.set_xticklabels([str(int(v)) if float(v).is_integer() else str(v)
                                for v in valores_eixo])

    def estilo(nome, i):
        st = estilo_de(nome, i)
        if tipo == "categorico":
            st["linestyle"] = "none"
        return st

    def plotar(ax, coluna, transformar, com_erro, logy=False, n_ser=2):
        for i, (nome, df) in enumerate(dfs.items()):
            y = df[coluna]
            e = df.get(f"{coluna}__dp")
            if transformar is not None:
                y = transformar(y)
                e = transformar(e) if e is not None else None
            rotulo = NOMES_EXIBICAO.get(nome, nome)
            # Em escala log, media - dp <= 0 nao tem posicao no eixo. Nesses
            # pontos a barra fica so com a metade de cima, e o aviso sai aqui.
            if com_erro and e is not None and logy:
                y_ = np.asarray(y, dtype=float)
                e_ = np.asarray(e, dtype=float)
                cruza = (y_ - e_) <= 0
                if cruza.any():
                    print(f"  [AVISO] {experimento}/{coluna}/{rotulo}: "
                          f"media - dp <= 0 em {int(cruza.sum())} ponto(s); "
                          f"barra inferior omitida na escala log.")
                e = np.vstack([np.where(cruza, 0.0, e_), e_])
            if tipo == "categorico":
                x = (_centros(len(df), n_ser)
                     + (i - (n_ser - 1) / 2) * LARGURA_BARRA)
                ax.bar(x, y, LARGURA_BARRA, label=rotulo, color=cor_de(nome, i),
                       yerr=(e if com_erro else None), capsize=6,
                       error_kw={"elinewidth": 2})
            else:
                if com_erro and e is not None:
                    ax.errorbar(df[eixo], y, yerr=e, label=rotulo,
                                color=cor_de(nome, i), capsize=5,
                                **estilo(nome, i))
                else:
                    ax.plot(df[eixo], y, label=rotulo, color=cor_de(nome, i),
                            **estilo(nome, i))

    salvos = []
    for coluna, ylabel, fname, transformar, logy, com_erro in METRICAS:
        fig, ax = plt.subplots(figsize=FIGSIZE)
        # Nos graficos categoricos, a referencia teorica (entropia maxima e
        # probabilidade de rastreamento minima) entra como terceira barra de
        # cada grupo, a direita das duas series (pedido do autor, 01/10).
        n_ser = (3 if tipo == "categorico"
                 and coluna in ("entropy", "prob_rastreamento") else 2)
        plotar(ax, coluna, transformar, com_erro, logy, n_ser)
        if logy:
            ax.set_yscale("log")

        # Referencia teorica (itens #43 e #46 do cap5.md). Com n dummies numa
        # grade de 36 celulas, a entropia maxima e log2(min(n, 36)), atingida
        # quando cada dummy cai numa celula diferente; a probabilidade de
        # rastreamento minima e 2^-Hmax = 1/min(n, 36). Curva no eixo de n,
        # linha constante (n do experimento) nos demais.
        if coluna in ("entropy", "prob_rastreamento"):
            celulas = 6 * 6
            if eixo == "n_total":
                xs = np.array(valores_eixo, dtype=float)
            else:
                ns = set()
                for d_ in dfs.values():
                    ns |= set(np.round(d_["n_total"]).astype(int))
                if len(ns) != 1:
                    raise ValueError(f"{experimento}: n nao e unico {ns}")
                xs = np.array([float(ns.pop())])
            h = np.log2(np.minimum(xs, celulas))
            ref = h if coluna == "entropy" else 2.0 ** (-h)
            rot = ("Máximo teórico ($\\log_2 n$)" if coluna == "entropy"
                   else "Mínimo teórico ($1/n$)")
            if tipo == "categorico":
                n_cat = len(categorias)
                ax.bar(_centros(n_cat, 3) + 1 * LARGURA_BARRA,
                       [ref[0]] * n_cat, LARGURA_BARRA, label=rot,
                       color="0.80", edgecolor="black", linewidth=0.8,
                       hatch="//")
            elif eixo == "n_total":
                ax.plot(xs, ref, color="black", linestyle=":", linewidth=2.0,
                        marker="x", markersize=8, label=rot)
            else:
                ax.axhline(ref[0], color="black", linestyle=":",
                           linewidth=2.0, label=rot)

        # Precisao e recall vivem entre 0 e 1 e, quando o algoritmo recupera
        # tudo, ficam colados em 1,00. Plotar 0..1 nesse caso produz duas
        # barras cheias indistinguiveis. A janela abaixo aproxima o eixo do
        # intervalo onde os dados de fato estao, sem nunca passar de 1.
        if coluna in ("precision", "recall"):
            minimos = [float(np.nanmin(df[coluna])) for df in dfs.values()]
            piso = min(minimos)
            ax.set_ylim(max(0.0, min(0.95, piso - 0.03)), 1.005)
            ax.axhline(1.0, color="black", linewidth=1.0, linestyle=":",
                       alpha=0.5)
            if piso >= 0.9995:
                ax.text(0.5, 0.5, "1,000 em todas as execuções",
                        transform=ax.transAxes, ha="center", va="center",
                        fontsize=26, color="0.35")

        ax.set_xlabel(xlabel, labelpad=0)
        ax.set_ylabel(ylabel)
        aplicar_eixo_x(ax, n_ser)
        if tipo == "categorico":
            ax.margins(x=0.31)
        _legenda(ax)
        ax.grid(True, axis="y" if tipo == "categorico" else "both",
                linestyle="--", alpha=0.7)
        plt.savefig(os.path.join(out_dir, fname), dpi=150, bbox_inches="tight")
        plt.close()
        salvos.append(fname)

    # ---- decomposicao do tempo de rede (so a v6 tem como fazer) ------------
    # Barras empilhadas: TTFB (RTT + execucao no servidor), download
    # (proporcional ao payload) e parse (local). Separar as tres e o unico
    # jeito de mostrar que o tempo total NAO e dirigido pelo algoritmo.
    fig, ax = plt.subplots(figsize=FIGSIZE)
    n_cat = len(dfs[primeiro])
    pos = _centros(n_cat)
    hachuras = ["", "//", ".."]
    componentes = [("ttfb_ms_total", "TTFB"),
                   ("download_ms_total", "Download"),
                   ("parse_ms_total", "Parse")]
    for i, (nome, df) in enumerate(dfs.items()):
        base = np.zeros(len(df))
        x = pos + (i - 0.5) * LARGURA_BARRA
        for j, (col, _) in enumerate(componentes):
            v = df[col].to_numpy() / 1000.0
            ax.bar(x, v, LARGURA_BARRA, bottom=base, color=cor_de(nome, i),
                   alpha=1.0 - 0.28 * j, hatch=hachuras[j],
                   edgecolor="white", linewidth=0.6,
                   label=(f"{NOMES_EXIBICAO.get(nome, nome)}" if j == 0 else None))
            base += v
        # Barra de desvio-padrao do tempo de rede total, no topo da pilha.
        dp = df.get("rede_ms_total__dp")
        if dp is not None:
            ax.errorbar(x, base, yerr=dp.to_numpy() / 1000.0, fmt="none",
                        ecolor="black", elinewidth=1.5, capsize=5)
    rotulos = ([_quebrar_rotulo(c) for c in categorias] if tipo == "categorico"
               else [str(int(v)) if float(v).is_integer() else str(v)
                     for v in dfs[primeiro][eixo]])
    ax.set_xticks(pos)
    ax.set_xticklabels(rotulos, rotation=30, ha="right", va="top")
    ax.set_xlabel(xlabel, labelpad=0)
    ax.set_ylabel("Tempo de rede (s)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.7)
    # UMA legenda so, acima da area, em duas colunas: cor = algoritmo,
    # hachura = componente. Duas legendas separadas colidiam com as barras
    # ou eram cortadas pelo bbox apertado.
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=cor_de(n, i), edgecolor="white",
                     label=NOMES_EXIBICAO.get(n, n))
               for i, n in enumerate(dfs)]
    handles += [Patch(facecolor="0.75", edgecolor="white", hatch=hachuras[j],
                      label=rot) for j, (_, rot) in enumerate(componentes)]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.02),
              ncol=2, frameon=True, borderaxespad=0.0, fontsize=24,
              handlelength=1.5, columnspacing=1.0, labelspacing=0.3)
    fname = "fig_tempo_rede_decomposto.png"
    plt.savefig(os.path.join(out_dir, fname), dpi=150, bbox_inches="tight")
    plt.close()
    salvos.append(fname)

    for f in salvos:
        print(f"  [{experimento}] {f}")
    return salvos


# =============================================================================
# RELATORIO
# =============================================================================
def relatorio(dfs_brutos, experimentos):
    print("\n" + "=" * 78)
    print("  RELATORIO DE VALIDADE  (ler antes de usar os graficos)")
    print("=" * 78)
    for nome, df in dfs_brutos.items():
        exibicao = NOMES_EXIBICAO.get(nome, nome)
        indef_p = int(df["precision"].isna().sum())
        indef_r = int(df["recall"].isna().sum())
        print(f"\n  {exibicao}")
        print(f"    linhas ............................. {len(df)} "
              f"(so repeticao == {REPETICAO_VALIDA})")
        print(f"    localizacoes distintas ............. "
              f"{df.groupby('cidade')['localizacao_id'].nunique().to_dict()}")
        print(f"    barras das figuras ................. desvio-padrao "
              f"(ddof=1) entre localizacoes do mesmo ponto")
        print(f"    requisicoes de protocolo ........... "
              f"{int(df['n_requisicoes'].sum())} somadas "
              f"(o eixo palavra_chave repete a mesma coleta em 3 linhas)")
        print(f"    precisao indefinida (gt vazio) ..... {indef_p}")
        print(f"    cobertura indefinida (gt vazio) .... {indef_r}")
        if "n_ground_truth" in df:
            menores = df[df["n_ground_truth"] < 10]
            if len(menores):
                print(f"    ATENCAO: {len(menores)} linhas com ground truth "
                      f"< 10 POIs. Nelas o recall anda em degraus grandes "
                      f"(1/{int(menores['n_ground_truth'].min())} ou mais).")
        p_um = float((df["precision"] >= 0.9995).mean())
        r_um = float((df["recall"] >= 0.9995).mean())
        print(f"    precisao == 1,000 em .............. {100 * p_um:.0f}% das linhas")
        print(f"    cobertura == 1,000 em ............. {100 * r_um:.0f}% das linhas")
        if p_um > 0.99 and r_um > 0.99:
            print(f"    -> A metrica esta no teto e nao discrimina nada neste "
                  f"algoritmo. Diga isso no texto em vez de exibir o grafico "
                  f"como se fosse resultado.")
        print(f"    dist. min. ao usuario .............. "
              f"mediana {df['dist_min_usuario_m'].median():.1f} m, "
              f"minimo {df['dist_min_usuario_m'].min():.1f} m")
        fr = (df["ttfb_ms_total"] / df["rede_ms_total"]).mean()
        print(f"    TTFB como fracao do tempo de rede .. {100 * fr:.1f}%")
        if fr > 0.5:
            print(f"    -> O tempo de rede e dominado por TTFB (fila e "
                  f"execucao no servidor), nao por payload. Nao reporte "
                  f"'tempo total' como custo do algoritmo sem essa ressalva.")
    print("\n" + "=" * 78)


# =============================================================================
# MAIN
# =============================================================================
def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    caminho_a, caminho_b = sys.argv[1], sys.argv[2]

    a = carregar_e_validar(caminho_a)
    b = carregar_e_validar(caminho_b)
    nome_a, nome_b = a["algorithm"].iloc[0], b["algorithm"].iloc[0]
    if nome_a == nome_b:
        raise ValueError(
            f"Os dois arquivos declaram o mesmo algoritmo ('{nome_a}'). "
            f"O framework compara dois algoritmos distintos.")

    comuns = sorted(set(a["experimento"]) & set(b["experimento"]))
    if not comuns:
        raise ValueError("Os dois CSVs não têm nenhum experimento em comum.")
    ausentes = ((set(a["experimento"]) | set(b["experimento"])) - set(comuns))
    if ausentes:
        print(f"[AVISO] Experimentos fora de um dos arquivos, ignorados: "
              f"{sorted(ausentes)}")

    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    for experimento in comuns:
        dfs = ordenar_series({nome_a: preparar(a, experimento),
                              nome_b: preparar(b, experimento)})
        checar_alinhamento(dfs, experimento)
        total += len(gerar_graficos(dfs, experimento,
                                    os.path.join(OUT_DIR, experimento)))

    relatorio({nome_a: a, nome_b: b}, comuns)
    print(f"  {len(comuns)} experimentos x {total // len(comuns)} graficos = "
          f"{total} figuras em {OUT_DIR}/")
    print("=" * 78)


if __name__ == "__main__":
    main()
