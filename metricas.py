# -*- coding: utf-8 -*-
"""
metricas.py  —  MODULO UNICO DE METRICAS DO FRAMEWORK COMPARATIVO
==================================================================

Por que este arquivo existe
---------------------------
Entropia, precisao e cobertura sao CONDICAO DE TESTE, nao parte de nenhum
algoritmo: os dois produtores precisam ser medidos pela mesma regua, senao a
comparacao mede a implementacao da metrica e nao a tecnica de privacidade.
Ate a v7 as tres funcoes estavam duplicadas em Liu_v7.py e em
Multiestrategia_v7.py. Eram identicas, mas nada garantia que continuassem
identicas depois de um ajuste feito de um lado so, e nenhuma execucao
acusaria a divergencia: os dois scripts seguiriam rodando e gravando CSVs
validos, com entropias calculadas por formulas diferentes.

Este modulo e a unica definicao dessas funcoes. Quem importar daqui esta,
por construcao, medindo do mesmo jeito.

Contrato
--------
Nenhuma funcao aqui conhece algoritmo, provedor de servicos ou experimento.
Todas recebem dados brutos e devolvem numero. Nao leem configuracao, nao
escrevem arquivo e nao imprimem nada.

Uso:
    from metricas import (haversine, metros_por_grau, entropia_espacial,
                          precisao_recall, filtrar_local)
"""
import math


# =============================================================================
# GEOMETRIA DE APOIO
#
# Fica aqui, e nao em cada produtor, pelo mesmo motivo das metricas: a
# distancia entre dois pontos entra tanto na geracao dos pontos ficticios
# quanto no casamento de POIs de precisao/cobertura. Duas implementacoes do
# mesmo elipsoide seriam duas reguas.
# =============================================================================
def haversine(lat1, lon1, lat2, lon2):
    """Distancia em metros entre dois pontos geograficos, esfera de raio
    6.371 km."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    v = (math.sin(p1) * math.sin(p2)
         + math.cos(p1) * math.cos(p2) * math.cos(dl))
    return math.acos(max(-1.0, min(1.0, v))) * R


def metros_por_grau(lat):
    """Metros por grau de latitude e de longitude na latitude dada.
    Devolve (mlat, mlon)."""
    mlat = 111132.954 - 559.822 * math.cos(2 * math.radians(lat))
    mlon = 111412.84 * math.cos(math.radians(lat))
    return mlat, mlon


# =============================================================================
# PRIVACIDADE
# =============================================================================
def entropia_espacial(dummies, centro, raio_m, lado_grade=6):
    """H = -sum(p_i log2 p_i) sobre uma grade de ocupacao
    lado_grade x lado_grade que cobre o quadrado de lado 2*raio_m centrado em
    `centro`. p_i e a fracao de dummies que cai na celula i.

    Devolve 0.0 com menos de dois dummies, caso em que a entropia e
    indefinida.

    NAO e a Eq. 1-3 de Liu e Wang (2022), que define q_i sobre PROBABILIDADE
    DE CONSULTA. E a metrica definida no Capitulo 3 da dissertacao, aplicada
    igualmente aos dois algoritmos. O desvio esta declarado no texto.
    """
    if len(dummies) < 2:
        return 0.0
    lat0, lon0 = centro
    celula = (2 * raio_m) / lado_grade
    contagem = {}
    for la, lo in dummies:
        dx = (lo - lon0) * 111320 * math.cos(math.radians(lat0))
        dy = (la - lat0) * 111320
        cx = min(max(int((dx + raio_m) // celula), 0), lado_grade - 1)
        cy = min(max(int((dy + raio_m) // celula), 0), lado_grade - 1)
        contagem[(cx, cy)] = contagem.get((cx, cy), 0) + 1
    total = sum(contagem.values())
    return -sum((c / total) * math.log2(c / total) for c in contagem.values())


def centroide(pontos):
    """Media aritmetica das coordenadas de um conjunto de pontos.

    Fica aqui, e nao em um dos produtores, pelo mesmo motivo da entropia: e
    condicao de teste. A distancia entre este centroide e a posicao real do
    usuario mede o ataque mais barato que existe contra um conjunto de
    dummies -- somar e dividir. Os dois algoritmos precisam ser medidos pela
    mesma conta para que o numero signifique alguma coisa.
    """
    return (sum(p[0] for p in pontos) / len(pontos),
            sum(p[1] for p in pontos) / len(pontos))


def erro_do_centroide(dummies, usuario):
    """Distancia, em metros, entre a media dos dummies e a posicao real.

    Quanto MAIOR, melhor para a privacidade. Proximo de zero significa que o
    provedor recupera a posicao do usuario com uma media aritmetica, sem
    precisar de nenhuma outra informacao.
    """
    cx, cy = centroide(dummies)
    return haversine(usuario[0], usuario[1], cx, cy)


# =============================================================================
# UTILIDADE
# =============================================================================
def precisao_recall(verdadeiros, obtidos, tolerancia_m):
    """Casamento por proximidade espacial, nao por id.

    Devolve (precisao, cobertura). Ground truth vazio devolve (None, None),
    INDEFINIDO, nunca zero: execucao sem nenhum POI da categoria no raio nao
    e falha do algoritmo, e entrar na media como 0.0 puxaria o resultado para
    baixo sem causa.
    """
    if not verdadeiros:
        return None, None
    casados = sum(
        any(haversine(p["lat"], p["lon"], v["lat"], v["lon"]) <= tolerancia_m
            for v in verdadeiros)
        for p in obtidos
    )
    precisao = casados / len(obtidos) if obtidos else 0.0
    return precisao, casados / len(verdadeiros)


# =============================================================================
# FILTRAGEM LOCAL
#
# Roda no dispositivo, sobre os dados ja recebidos. E o passo que devolve ao
# usuario o resultado que ele teria obtido consultando a propria posicao, e e
# tambem o passo cronometrado em Filter_ms. Igual nos dois produtores porque
# a diferenca entre eles esta na GERACAO, nao no que se faz com a resposta.
# =============================================================================
def filtrar_local(respostas, usuario, raio_busca_m, chave, valor):
    """Deduplica por (type, id), aplica o filtro espacial pelo raio de busca
    do usuario e o filtro textual pela palavra-chave.

    O provedor nunca soube a palavra-chave nem o raio do usuario: os dois
    filtros so existem deste lado.
    """
    vistos, espacial = set(), []
    for p in respostas:
        ch = (p.get("type"), p.get("id"))
        if ch in vistos:
            continue
        vistos.add(ch)
        if haversine(p["lat"], p["lon"], usuario[0], usuario[1]) <= raio_busca_m:
            espacial.append(p)
    alvo = str(valor).lower()
    return [p for p in espacial
            if str(p.get("tags", {}).get(chave, "")).lower() == alvo]
