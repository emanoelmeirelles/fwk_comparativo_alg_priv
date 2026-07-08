# -*- coding: utf-8 -*-
"""
metrics_core.py
================
Módulo único e compartilhado de métricas para o Framework de Comparação
de Algoritmos de Privacidade Espaço-Textual.

REGRA DE OURO: Os algoritmos comparados DEVEM importar este
módulo para calcular entropia, precisão e recall. Nenhum dos dois scripts
pode reimplementar essas fórmulas localmente.

"""
import math
from typing import List, Tuple, Dict

EARTH_RADIUS_M = 6371000


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância geodésica entre dois pontos, em metros."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    val = (math.sin(phi1) * math.sin(phi2) +
           math.cos(phi1) * math.cos(phi2) * math.cos(dlon))
    return math.acos(max(-1.0, min(1.0, val))) * EARTH_RADIUS_M


def shannon_entropy_spatial(dummies: List[Tuple[float, float]],
                             center: Tuple[float, float],
                             radius_m: float,
                             grid_size: int = 6) -> float:
    """
    Entropia espacial de Shannon sobre uma grade de ocupação.

    Cobre a área de ofuscação (quadrado de lado 2*radius_m centrado em
    `center`) com uma grade grid_size x grid_size. p_i é a fração de
    dummies que caem na célula i. H = -sum(p_i * log2(p_i)).

    Esta é uma escolha metodológica EXPLÍCITA — não a única fórmula
    possível — que substitui a ponderação por distância do rev016, cuja
    derivação de p_i não tinha correspondência documentada na
    dissertação. Corresponde à adaptação padrão de entropia espacial
    usada na literatura de cloaking (ex.: Bettini et al.) e deve ser
    citada como tal no Capítulo 3/4 revisado, com a grade explicitada
    como parâmetro do experimento.

    Retorna 0.0 se houver menos de 2 dummies (entropia indefinida).
    """
    n = len(dummies)
    if n < 2:
        return 0.0

    lat0, lon0 = center
    cell_size_m = (2 * radius_m) / grid_size

    counts: Dict[Tuple[int, int], int] = {}
    for lat, lon in dummies:
        # projeção local equirretangular (suficiente para áreas de poucos km)
        dx = (lon - lon0) * 111320 * math.cos(math.radians(lat0))
        dy = (lat - lat0) * 111320
        cx = int((dx + radius_m) // cell_size_m)
        cy = int((dy + radius_m) // cell_size_m)
        cx = min(max(cx, 0), grid_size - 1)
        cy = min(max(cy, 0), grid_size - 1)
        key = (cx, cy)
        counts[key] = counts.get(key, 0) + 1

    total = sum(counts.values())
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * math.log2(p)
    return h


def evaluate_precision_recall(real: List[dict], priv: List[dict],
                               tolerance_m: float) -> Tuple[float, float]:
    """
    Precisão e recall por proximidade espacial (não por igualdade de ID).

    precision = |matched| / |priv|
    recall    = |matched| / |real|

    `real` e `priv` são listas de dicts com chaves 'lat' e 'lon'.

    Esta é uma ADAPTAÇÃO da Eq. 2.3 da dissertação (cobertura por
    interseção de conjuntos) para dados ruidosos de OSM — deve ser
    documentada como aproximação por tolerância espacial, não
    apresentada como interseção exata de conjuntos.
    """
    matched = sum(
        any(haversine(p["lat"], p["lon"], r["lat"], r["lon"]) <= tolerance_m
            for r in real)
        for p in priv
    )
    precision = matched / len(priv) if priv else 0.0
    recall = matched / len(real) if real else 0.0
    return precision, recall
