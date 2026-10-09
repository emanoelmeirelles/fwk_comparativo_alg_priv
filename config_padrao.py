# -*- coding: utf-8 -*-
"""
config_padrao.py  —  FONTE UNICA DE VALORES DEFAULT
====================================================

Este e o UNICO lugar onde os parametros compartilhados dos experimentos sao
definidos. Os quatro scripts do pipeline importam daqui:

    coletar_osm_v5.py
    Liu_rev002_4experimentos_v5.py
    Multiestrategia_4experimentos_v5.py
    framework_comparativo_4experimentos_v5.py

Antes, cada valor era repetido a mao em varios scripts e mantido igual por
comentarios "== ..." (ex.: OBFUSCATION_RADIUS == R_ANON_FRAMEWORK). Isso era
fragil: bastava editar um e esquecer o outro para os dois algoritmos deixarem
de ser comparaveis. Agora edita-se AQUI, e todos os scripts leem o mesmo valor.

REGRA: mude valores so neste arquivo. Nenhuma logica de algoritmo depende deste
modulo -- apenas os parametros de configuracao dos experimentos.

+---------------------------------------------------------------------------+
|  TABELA DE VALORES DEFAULT                                                 |
+----------------------------+----------------------+-----------------------+
|  Parametro                 |  Valor default       |  Usado por            |
+----------------------------+----------------------+-----------------------+
|  DEFAULT_CIDADE            |  "Salvador"          |  Liu, Multi           |
|  DEFAULT_PALAVRA_CHAVE     |  "Restaurante"       |  Liu, Multi           |
|  DEFAULT_RAIO_BUSCA_M      |  750.0 m             |  Liu, Multi           |
|  DEFAULT_N                 |  15 dummies          |  Liu, Multi           |
|  R_ANON                    |  500.0 m             |  Liu, Multi           |
|  PRECISION_TOLERANCE_M     |  40.0 m              |  Liu, Multi           |
|  SIMULATIONS               |  200 execucoes        |  Multi, framework     |
|  OSM_FETCH_RADIUS_M        |  1250.0 m            |  coletar, Liu, Multi  |
+----------------------------+----------------------+-----------------------+
|  GRIDS OFAT (um eixo varia, os demais ficam no default)                   |
+----------------------------+----------------------------------------------+
|  RAIOS_BUSCA_M             |  [250, 500, 750, 1000, 1250] m               |
|  N_VALUES                  |  [5, 10, 15, 20, 25] dummies                 |
|  CIDADES (eixo dataset)    |  Sao Paulo, Salvador, Feira de Santana       |
|  PALAVRAS_CHAVE (eixo)     |  Restaurante, Lanchonete, Farmacia            |
+---------------------------------------------------------------------------+

Observacao: valores intrinsecos a UM algoritmo (ex.: REAL_LOCATION e os
parametros da reproducao das Figuras 4/5 de Liu & Wang, ou FRAC_CIRC /
GEOM_PERTURB_M da geracao multiestrategia) permanecem em seus proprios
scripts -- nao sao compartilhados e portanto nao entram aqui.
"""

import os

# =============================================================================
# CIDADES -- coordenadas (lat, lon). Precisam ser IDENTICAS nos tres scripts
# que tocam OSM (coletar, Liu, Multi), senao os algoritmos nao usam a mesma
# base de POIs. Eixo X do experimento "dataset".
# =============================================================================
#
# CORRECAO 26/07/2026: a coordenada anterior de "Salvador" era
# (-12.24, -38.94), que fica a 94 km de Salvador e a 4 km do centro de Feira
# de Santana -- as tags addr:city do payload coletado registravam "Feira de
# Santana", "Caseb" e "Santo Antonio dos Prazeres" (bairros de Feira). Como
# Salvador e a DEFAULT_CIDADE, o erro contaminava os quatro experimentos, nao
# so o eixo "dataset". O ponto abaixo fica a 2,1 km da Praca Municipal.
# Exige recoleta (coletar_osm_v5.py) e reexecucao dos dois algoritmos.
#
# CORRECAO 26/07/2026: a coordenada anterior de "Feira de Santana" era
# (-12.27, -38.97), 1,77 km ao sul do ponto abaixo. Naquele recorte havia ZERO
# POIs categorizados nos 250 m centrais e a densidade CRESCIA ate a borda
# (19,2/km2 no anel externo contra 0 no interno) -- padrao inverso ao de um
# centro urbano, sinal de que o ponto caia em area vazia. Total de POIs
# categorizados no recorte inteiro: 48. Exige recoleta e reexecucao.
#
# 26/07/2026: "Sao Paulo" passou de (-23.55, -46.63) para o ponto abaixo,
# a 21 m do anterior. A mudanca e de precisao, nao de lugar: as tres cidades
# passam a ter coordenada com cinco casas decimais, obtida pelo mesmo criterio.
#
# CRITERIO DE ESCOLHA DO CENTRO: centro urbano de cada municipio, aplicado
# igualmente as tres cidades. O criterio e externo aos dados -- NAO se escolhe
# o ponto que maximiza a contagem de POIs, o que seria selecao enviesada de
# amostra. Declarado na Secao 5.1.2 da dissertacao.
CIDADES = {
    "São Paulo": (-23.54981, -46.62998),
    "Salvador": (-12.98270, -38.51651),
    "Feira de Santana": (-12.25480, -38.96517),
}

# =============================================================================
# PALAVRAS-CHAVE -- nome exibido nos graficos -> valor de amenity no OSM.
# Eixo X do experimento "palavra_chave".
# =============================================================================
# REVISAO 26/07/2026. As tres anteriores (Restaurante, Quadra Esportiva, Loja
# de Roupas) foram escolhidas antes de haver contagem: na base coletada,
# Loja de Roupas dava 0 POIs em Feira de Santana e Restaurante dava 1, o que
# deixa precisao e recall indefinidos. As tres abaixo saem de contagem real
# (analisar_tipos_poi.py) sobre as bases das tres cidades.
#
# Criterio, nesta ordem:
#   1. Contagem suficiente nas TRES cidades -- o gargalo e sempre a mais
#      esparsa, entao ranqueia-se pelo MINIMO, nunca pelo total.
#   2. Contraste entre cidades -- o objetivo especifico 2 mede sensibilidade a
#      densidade urbana. Palavra-chave com contagem parecida nas tres cidades
#      nao consegue revelar efeito de densidade nenhum.
#   3. Mapeamento como ponto -- parque (leisure=park) e estacionamento
#      (amenity=parking) tinham contagem boa, mas sao poligonos reduzidos ao
#      centro do bounding box; com PRECISION_TOLERANCE_M de 40 m o erro de
#      geometria contaminaria a metrica.
#
# Farmacia entra como CONTROLE: contraste de 1,4x, quase constante entre as
# cidades. Se as metricas variarem em Restaurante e Lanchonete mas nao em
# Farmacia, o efeito acompanha a densidade de POIs e nao alguma peculiaridade
# da cidade. Nao usar healthcare=pharmacy junto: sao os MESMOS objetos
# (23/23, 30/30 e 20/20 ids coincidentes nas tres cidades).
PALAVRAS_CHAVE = {
    # nome exibido -> (chave OSM, valor). O filtro textual casa tags[chave]==valor.
    #                                       Feira / Salvador / SP   contraste
    "Restaurante": ("amenity", "restaurant"),  #  28 / 103 / 138      4,9x
    "Lanchonete": ("amenity", "fast_food"),    #  12 /  46 /  88      7,3x
    "Farmácia": ("amenity", "pharmacy"),       #  23 /  32 /  24      1,4x (controle)
}

# =============================================================================
# GRIDS OFAT -- valores varridos, um experimento por eixo.
# =============================================================================
RAIOS_BUSCA_M = [250.0, 500.0, 750.0, 1000.0, 1250.0]
N_VALUES = [5, 10, 15, 20, 25]

# =============================================================================
# DEFAULTS OFAT -- valor mantido nos eixos que NAO estao sendo variados.
# =============================================================================
DEFAULT_CIDADE = "Salvador"
DEFAULT_PALAVRA_CHAVE = "Restaurante"
DEFAULT_RAIO_BUSCA_M = 750.0
DEFAULT_N = 15

# =============================================================================
# INVARIANTES FISICOS COMPARTILHADOS -- precisam ser iguais nos dois
# algoritmos para a comparacao ser justa.
# =============================================================================
R_ANON = 500.0                 # raio de anonimato base (Ranon)
                               #   Multi: OBFUSCATION_RADIUS ; Liu: R_ANON_FRAMEWORK
PRECISION_TOLERANCE_M = 40.0   # tolerancia de casamento espacial precisao/recall
                               #   Multi: PRECISION_RADIUS ; Liu: PRECISION_TOLERANCE_M
SIMULATIONS = 5                # no de execucoes por ponto de dados.
                               # Historico: 300 -> 50 -> 10 -> 1.
                               #
                               # 5 e o valor de RESULTADO. Medido sobre a
                               # rodada de N=10: Medido sobre a rodada de N=10:
                               # a entropia varia entre execucoes do mesmo
                               # ponto com desvio de 0,14 a 0,34 e amplitude
                               # de ate 1,02 bits, enquanto a diferenca entre
                               # os dois algoritmos e 0,58. Com N=1 ha 66% de
                               # chance de pelo menos um dos 16 pontos do
                               # desenho mostrar o Liu com entropia MAIOR que
                               # a Multiestrategia, por sorteio.
                               #
                               #   N=1  210 req/alg  ~0,3 h   66% de inversao
                               #   N=3  630 req/alg  ~0,9 h   37%
                               #   N=5 1050 req/alg  ~1,5 h   29%
                               #   N=10 2100 req/alg ~2,9 h   21%
                               #
                               # Bytes, precisao e recall sao estaveis (CV de
                               # 3%), entao N=1 basta para conferir a mudanca
                               # da consulta. Suba para 5 antes de gerar os
                               # graficos que vao para a dissertacao.
                               #   Multi: SIMULATIONS ; Liu: NUM_RUNS_FRAMEWORK
OSM_FETCH_RADIUS_M = 1250.0    # raio da coleta unica de OSM (maior raio de busca)
                               #   coletar: RAIO_COLETA_M ; Multi: OSM_FETCH_RADIUS ;
                               #   Liu: OSM_FETCH_RADIUS_FRAMEWORK

# =============================================================================
# MODELO DE REDE -- Network_ms = RTT_MS * n_consultas + comm_cost_bytes / BANDA
# Substitui a latencia medida do Overpass, que era dominada por carga do
# servidor / rate-limiting no instante da medicao (nao-monotonica, nao
# reproduzivel). Este modelo cresce com o raio (mais bytes) e com n (mais
# consultas), e e REPRODUZIVEL: comm_cost e deterministico dado o snapshot;
# RTT e banda sao constantes de referencia documentadas. A latencia medida
# passa a ser apenas informativa (nao entra mais no Network_ms).
# =============================================================================
RTT_MS = 50.0                  # latencia de ida-e-volta por consulta (ms), referencia
BANDA_BYTES_POR_MS = 1250.0    # banda de download ~10 Mbps (1250 B/ms), referencia


# =============================================================================
# DERIVADO -- raios de latencia que coletar_osm_v5.py deve medir por cidade.
# A cidade default e a unica que aparece em TODOS os raios (experimento
# "raio_busca"); as demais so aparecem no experimento "dataset", com o raio
# default -- mas o raio de coleta (maior) e medido de qualquer forma porque e a
# consulta que traz o payload da base. Derivar daqui garante que os raios
# medidos acompanham automaticamente qualquer mudanca em RAIOS_BUSCA_M.
# =============================================================================
def raios_latencia_por_cidade():
    outras = sorted({DEFAULT_RAIO_BUSCA_M, OSM_FETCH_RADIUS_M})
    return {
        cidade: (sorted(RAIOS_BUSCA_M) if cidade == DEFAULT_CIDADE else outras)
        for cidade in CIDADES
    }


# #############################################################################
# ###                        BLOCO V6 -- CONSULTA INDIVIDUAL                ###
# #############################################################################
#
# A v5 baixava UM arquivo por cidade e os algoritmos consultavam esse arquivo.
# Consequencia: Query_ms media busca em indice local, e o tempo de rede era
# MODELADO por RTT_MS/BANDA_BYTES_POR_MS -- nao medido.
#
# Na v6 cada dummy gera UMA requisicao real a Overpass, e tempo e bytes sao
# medidos POR RESPOSTA. RTT_MS e BANDA_BYTES_POR_MS continuam definidos acima
# porque os scripts v5 os importam, mas NENHUM script v6 os usa.
#
# Custo do desenho, por algoritmo, com SIMULATIONS = 10:
#     dataset        3 cidades x 10 x 15 dummies ...........  450 requisicoes
#     palavra_chave  10 x 15 (UMA coleta reusada nas 3) .....  150
#     raio_busca     5 raios x 10 x 15 ....................... 750
#     n_dummies      10 x (5+10+15+20+25) .................... 750
#     ground truth   1 por (cidade, raio) usado ..............   7
#                                                          --------
#                                                            2.107
# #############################################################################

# --- Forma da consulta ------------------------------------------------------
# SOMENTE_COM_TAG: pede ao servidor apenas elementos que tenham ALGUMA tag.
#
# Motivo, medido numa resposta real do cache (Sao Paulo, 750 m, 34.096 POIs):
# 63,3% dos elementos devolvidos NAO tem tag nenhuma. Sao vertices de
# geometria -- cantos de predio, pontos de curva de rua -- e nunca casam com
# tags[chave]==valor, entao o filtro local os descarta de qualquer jeito.
# Pedi-los e trafego puro: 2,6x de reducao mediana no fio, medida em 400
# respostas do cache.
#
# POR QUE ISSO NAO VAZA A PALAVRA-CHAVE: o filtro e IDENTICO para qualquer
# termo de busca. Quem procura farmacia manda exatamente a mesma consulta de
# quem procura restaurante. Como a observacao do provedor nao varia com T,
# ela nao carrega informacao sobre T, e o I(T;O)=0 do Capitulo 3 continua
# valendo. Isso NAO seria verdade se a consulta filtrasse por amenity.
#
# NAO muda precisao nem recall: elemento sem tag nunca casaria.
SOMENTE_COM_TAG = True

# Versao da forma da consulta. Entra na chave do cache: respostas de versoes
# diferentes NUNCA se misturam, porque o payload de uma consulta filtrada e
# outro objeto que o de uma consulta sem filtro.
VERSAO_PAYLOAD = "v6.1-somente-com-tag" if SOMENTE_COM_TAG else "v6.0-tudo"

# Versao da TECNICA. Muda quando o algoritmo muda, mesmo que a consulta
# enviada continue identica. v8 e a introducao do centro de ofuscacao
# deslocado (CENTRO_DESLOCADO abaixo).
VERSAO_TECNICA = "v8-centro-c"

# VERSAO_CONSULTA continua sendo SO o payload, e de proposito: e ela que entra
# na chave do cache. Se a tecnica entrasse aqui, mudar o algoritmo invalidaria
# 1,4 GB de respostas ja baixadas sem nenhum motivo -- a resposta do servidor
# para uma coordenada nao depende de como a coordenada foi sorteada.
VERSAO_CONSULTA = VERSAO_PAYLOAD

# A tecnica entra no JORNAL, separada, e os guardas de retomada comparam as
# duas. Um jornal da v7 tem execucoes de um algoritmo que nao existe mais:
# retomar por cima dele produziria um CSV metade v7, metade v8, e nada no
# arquivo denunciaria a mistura. Com esta marca, a retomada aborta sozinha.

# --- Servidor ---------------------------------------------------------------
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_STATUS_URL = "https://overpass-api.de/api/status"
OVERPASS_USER_AGENT = ("UEFS-PGCC-dissertacao-multiestrategia-v6 "
                       "(emanoelmeirelles@gmail.com)")

# --- Ritmo de requisicao ----------------------------------------------------
# PAUSA_ENTRE_REQUISICOES_S e um CHUTE ate o piloto rodar. Rode
# piloto_overpass.py e substitua pelo valor que ele recomendar -- e a unica
# forma honesta de fixar esse numero, porque depende do servidor e do horario.
PAUSA_ENTRE_REQUISICOES_S = 5.0
USAR_SLOT_STATUS = True        # consulta /api/status e espera slot livre em vez
                               # de dormir as cegas. Cai para a pausa fixa se o
                               # endpoint nao responder ou mudar de formato.
MAX_TENTATIVAS = 5
BACKOFF_BASE_S = 60.0          # 429: espera BACKOFF_BASE * 2**tentativa

# --- Timeouts (segundos) ----------------------------------------------------
TIMEOUT_SERVIDOR_S = 90        # [out:json][timeout:N] -- quanto a Overpass pode
                               # gastar EXECUTANDO a consulta
TIMEOUT_CONEXAO_S = 15         # abertura da conexao TCP/TLS
TIMEOUT_LEITURA_S = 180        # espera entre bytes da resposta

# --- Onde o experimento ESCREVE ---------------------------------------------
# NAO escreva dentro do OneDrive.
#
# Em 2026-08-20 a execucao morreu no primeiro flush do jornal com
# "TimeoutError: [Errno 60] Operation timed out". Cada gravacao passa pela
# camada de sincronizacao do OneDrive, e o executor faz um flush por par --
# mais de mil gravacoes ao longo de horas. Basta uma travar para a rodada
# inteira cair, e ela cai depois de horas de requisicao ja gastas.
#
# O CODIGO continua no OneDrive, sincronizado como sempre. So as SAIDAS saem
# de la. Ao fim da rodada, copie DIR_RESULTADOS de volta para a pasta do
# projeto -- e ai, uma copia so, sem risco.
#
# Para voltar ao comportamento antigo, aponte DIR_TRABALHO para "." .
DIR_TRABALHO = os.path.expanduser("~/dissertacao_execucao")

# --- Cache e retomada -------------------------------------------------------
DIR_CACHE_CONSULTAS = os.path.join(DIR_TRABALHO, "cache_overpass")
DIR_RESULTADOS = os.path.join(DIR_TRABALHO, "resultados")
# Execucoes ja concluidas ficam num JSONL; ao reiniciar, o script pula o que
# ja esta la. Sem isso, um 429 no meio de 17 horas obriga a recomecar do zero.
ARQ_JORNAL_LIU = os.path.join(DIR_RESULTADOS, "jornal_liu_v7.jsonl")
ARQ_JORNAL_MULTI = os.path.join(DIR_RESULTADOS, "jornal_multiestrategia_v7.jsonl")

# --- Posicao do usuario -----------------------------------------------------
# DECISAO v6: o usuario e a coordenada da cidade em CIDADES, fixa. Os dois
# algoritmos usam exatamente o mesmo ponto, o que elimina o confundimento da
# v5 (Liu ancorado no centro, Multi sorteando um POI por execucao). Custo
# assumido: nao ha variabilidade de posicao -- as barras de erro refletem
# apenas a aleatoriedade da geracao de dummies, e os resultados descrevem o
# centro urbano, que e a regiao mais densa da base.
def posicao_usuario(cidade):
    return CIDADES[cidade]

# --- Semente ----------------------------------------------------------------
# Semente derivada de (experimento, valor, run_id): a execucao 7 gera os
# MESMOS dummies em qualquer maquina e depois de qualquer interrupcao.
SEMENTE_BASE = 20260805

def semente_da_execucao(experimento, valor, run_id):
    return (SEMENTE_BASE
            + 1_000_003 * (abs(hash((experimento, str(valor)))) % 100_000)
            + run_id) % (2 ** 32)

# --- Parametros intrinsecos de Liu & Wang (2022) ----------------------------
# R do artigo e o LADO do quadrado da area anonima (Tabela 1: "anonymous area
# side length"), e nao um raio. R_ANON acima e reaproveitado como esse lado.
LIU_R_QUERY_GEN_M = 40.0   # r: deslocamento maximo de cada offset (Secao 3.2 e
                           # Fig. 3; e o r da Eq. 4, p_min = 1/2 - 1/pi)
LIU_M_PER_GROUP = 1        # m: deslocamentos por locating point. n = k * m.
                           # ATENCAO: com m=1 a restricao ">r entre offsets do
                           # mesmo grupo" nunca dispara, porque o grupo tem um
                           # elemento so. O artigo usa m em {1,2,3} na Fig. 4 e
                           # nao declara m na Fig. 5. Suba para 2 ou 3 se
                           # quiser exercitar a restricao.
LIU_M_VALUES_FIG4 = [1, 2, 3]   # varredura literal da Secao 4.1
LIU_R_ANON_FIG4 = 400.0         # Secao 4.1
LIU_R_ANON_FIG5 = 700.0         # Secao 4.2

# --- Distancia minima ate o usuario (SO na Multiestrategia) -----------------
# O Capitulo 3 afirma que a localizacao do usuario nunca e transmitida. Na v5,
# o D0 caia a 23 m de mediana -- dentro de PRECISION_TOLERANCE_M, ou seja,
# dentro do proprio limiar com que o codigo decide que dois pontos sao o mesmo
# lugar. DIST_MINIMA_USUARIO_M passa a ser o piso.
# NAO se aplica ao Liu: o artigo manda deslocar a posicao real em no maximo r,
# e impor um piso descaracterizaria a linha de base.
DIST_MINIMA_USUARIO_M = 100.0

# --- Centro de ofuscacao deslocado (SO na Multiestrategia) ------------------
# ISTO E A MUDANCA DA v8.
#
# Ate a v7 os dummies eram gerados em torno da propria posicao do usuario. A
# distribuicao ficava simetrica em torno dele, e a media das coordenadas
# enviadas caia perto da posicao real: o provedor recuperava L_user com uma
# media aritmetica, sem precisar de nada mais.
#
# A subsecao Formalizacao do Capitulo 4 ja descrevia a correcao -- um centro
# de ofuscacao c distinto de L_user -- mas nem o pseudocodigo publicado nem o
# codigo implementavam. A v8 implementa: c e sorteado a cada execucao, uniforme
# em AREA no disco de raio RAIO_DESLOC_CENTRO_M em torno do usuario, e toda a
# geracao passa a ser centrada em c.
#
# Por que 250 m: c precisa ficar longe o bastante para que a media dos dummies
# nao aponte para o usuario, e perto o bastante para que o usuario continue
# DENTRO da area de ofuscacao de raio R_ANON, como a Figura da Formalizacao
# mostra. Com R_ANON = 500, meia distancia satisfaz os dois.
CENTRO_DESLOCADO = True
RAIO_DESLOC_CENTRO_M = 0.5 * R_ANON

# Ancora de utilidade: o primeiro dummy (D0) continua sorteado em torno do
# USUARIO, nao de c. Sem ele nao ha garantia de que alguma consulta cubra a
# posicao real, e a cobertura (recall) passa a depender de sorte geometrica.
# Custo declarado: um dos n pontos e correlacionado com L_user. A media do
# conjunto continua apontando para c, porque os outros n-1 dominam.
# Ponha False para medir quanto a ancora vale -- e o experimento que responde
# se ela e necessaria.
ANCORA_UTILIDADE = True


# =========================================================================
# OSMlocal (01/10/2026): rodada com Overpass local, pedida pelo orientador.
# Tudo abaixo SOBRESCREVE os valores acima. A pasta v7_intercalado/ continua
# com a configuracao da Overpass publica.
# =========================================================================
import hashlib as _hashlib
import json as _json

# Endereco do servidor. Para usar a Overpass publica com estes scripts:
#   OVERPASS_URL=https://overpass-api.de/api/interpreter python3 executor_intercalado.py
OVERPASS_URL = os.environ.get("OVERPASS_URL", "http://localhost:12345/api/interpreter")
OVERPASS_STATUS_URL = OVERPASS_URL.replace("/interpreter", "/status")
USAR_SLOT_STATUS = False          # servidor local nao tem fila de slots
PAUSA_ENTRE_REQUISICOES_S = 0.0   # pausa nao entra na medicao; zero acelera a rodada

# run_id passa a ser o indice da localizacao do usuario (0..N-1).
# Para um piloto: OSMLOCAL_N_LOC=2 python3 executor_intercalado.py
SIMULATIONS = int(os.environ.get("OSMLOCAL_N_LOC", "100"))
REPETICOES_SEGUIDAS = 2           # cada algoritmo roda 2x seguidas; vale a 2a
ALTERNAR_ORDEM = True             # alterna quem roda primeiro a cada localizacao
USAR_CACHE_DUMMIES = False        # com cache, a 2a execucao nao iria a rede

VERSAO_TECNICA = "v8-centro-c-osmlocal"

DIR_TRABALHO = os.path.expanduser("~/dissertacao_execucao_osmlocal")
DIR_CACHE_CONSULTAS = os.path.join(DIR_TRABALHO, "cache_overpass")
DIR_RESULTADOS = os.path.join(DIR_TRABALHO, "resultados")
ARQ_JORNAL_LIU = os.path.join(DIR_RESULTADOS, "jornal_liu_osmlocal.jsonl")
ARQ_JORNAL_MULTI = os.path.join(DIR_RESULTADOS, "jornal_multiestrategia_osmlocal.jsonl")
# Uma linha por requisicao (dummies e ground truth), gravada junto com o jornal.
ARQ_LOG_REQUISICOES = os.path.join(DIR_RESULTADOS, "requisicoes_osmlocal.jsonl")

ARQ_LOCALIZACOES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "localizacoes.json")
RAIO_SORTEIO_LOCALIZACOES_M = 600.0    # decisao de 01/10: ate 600 m do centro (era 1.250)
EXIGIR_POI_NOS_PONTOS_OFAT = True     # troca localizacao sem POI no ground truth
SEMENTE_LOCALIZACOES = 20261001

_LOCALIZACOES = None


def posicao_usuario(cidade, run_id=None):
    """Sem run_id: centro da cidade (usado so no aquecimento da conexao).
    Com run_id: a localizacao run_id da cidade, lida de localizacoes.json."""
    global _LOCALIZACOES
    if run_id is None:
        return CIDADES[cidade]
    if _LOCALIZACOES is None:
        with open(ARQ_LOCALIZACOES, encoding="utf-8") as f:
            _LOCALIZACOES = _json.load(f)["localizacoes"]
    la, lo = _LOCALIZACOES[cidade][run_id]
    return (la, lo)


def semente_da_execucao(experimento, valor, run_id):
    """Igual a versao anterior, mas com sha256 no lugar de hash(): o Python
    sorteia o hash de strings a cada processo, e a semente precisa ser a
    mesma numa retomada."""
    h = int(_hashlib.sha256(f"{experimento}|{valor}".encode()).hexdigest(), 16)
    return (SEMENTE_BASE + 1_000_003 * (h % 100_000) + run_id) % (2 ** 32)
