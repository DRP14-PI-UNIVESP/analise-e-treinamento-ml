
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
import json

from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

URL = "https://www.webmotors.com.br/carros-usados"

MAX_PAGINAS = 5
TEMPO_INICIAL_MS = 8000
TEMPO_ESPERA_PAGINA_MS = 5000
TEMPO_MAXIMO_CONFIRMACAO_MS = 15000

DIR_DIAGNOSTICO = (
    BASE_DIR
    / "data"
    / "bronze"
    / "webmotors"
    / "diagnostico"
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def salvar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def obter_parametros_url(url):
    return parse_qs(urlparse(url).query)


def analisar_resposta(resposta):
    """Analisa uma resposta da API e valida os indicadores de página."""

    if not isinstance(resposta, dict):
        return None

    if resposta.get("status") != 200:
        return None

    url_api = resposta.get("url", "")
    parametros_api = obter_parametros_url(url_api)

    url_interna = parametros_api.get("url", [""])[0]

    if not url_interna:
        return None

    # A URL interna pode estar codificada mais de uma vez.
    for _ in range(3):
        url_decodificada = unquote(url_interna)
        if url_decodificada == url_interna:
            break
        url_interna = url_decodificada

    parametros_internos = obter_parametros_url(url_interna)
    caminho_interno = urlparse(url_interna).path.lower()

    cidade = parametros_internos.get(
        "estadocidade",
        parametros_api.get("estadocidade", [""])
    )[0].strip().lower()

    try:
        pagina_url = int(
            parametros_internos.get("page", ["1"])[0]
        )
        pagina_api = int(
            parametros_api.get("actualPage", ["0"])[0]
        )
    except (TypeError, ValueError):
        return None

    dados = resposta.get("data")

    if not isinstance(dados, dict):
        return None

    paginacao = dados.get("Pagination", {})

    if not isinstance(paginacao, dict):
        return None

    try:
        pagina_json = int(paginacao.get("PageCurrent", 0))
    except (TypeError, ValueError):
        return None

    resultados = dados.get("SearchResults")

    if not isinstance(resultados, list):
        return None

    return {
        "dados": dados,
        "resultados": resultados,
        "caminho_interno": caminho_interno,
        "cidade": cidade,
        "pagina_url": pagina_url,
        "pagina_api": pagina_api,
        "pagina_json": pagina_json,
        "pagina": pagina_url,
        "url_api": url_api,
        "url_interna": url_interna,
    }


def anuncio_usado_valido(veiculo):
    """Valida individualmente cada anúncio retornado pela API."""

    if not isinstance(veiculo, dict):
        return False

    identificador = veiculo.get("UniqueId")

    if identificador in (None, "", 0, "0"):
        return False

    # O campo do anúncio é mais relevante que o parâmetro externo.
    if veiculo.get("MediaZeroKm") is not False:
        return False

    return True


def corresponde_a_usados_sp(resposta):
    info = analisar_resposta(resposta)

    if info is None:
        return False

    return (
        "/carros-usados/sp" in info["caminho_interno"]
        and info["cidade"] == "são paulo"
        and info["pagina_url"] == info["pagina_api"]
        and info["pagina_api"] == info["pagina_json"]
    )


def preparar_resposta_filtrada(resposta):
    """
    Retorna uma cópia da resposta contendo apenas anúncios usados
    com identificador válido. Não altera a resposta original.
    """

    if not corresponde_a_usados_sp(resposta):
        return None

    info = analisar_resposta(resposta)

    anuncios = [
        veiculo
        for veiculo in info["resultados"]
        if anuncio_usado_valido(veiculo)
    ]

    if not anuncios:
        return None

    ids = [
        str(veiculo["UniqueId"])
        for veiculo in anuncios
    ]

    # Evita que a resposta tenha o mesmo anúncio mais de uma vez.
    if len(ids) != len(set(ids)):
        anuncios_unicos = []
        ids_vistos = set()

        for veiculo in anuncios:
            identificador = str(veiculo["UniqueId"])

            if identificador not in ids_vistos:
                ids_vistos.add(identificador)
                anuncios_unicos.append(veiculo)

        anuncios = anuncios_unicos

    copia = dict(resposta)
    dados_copia = dict(info["dados"])
    dados_copia["SearchResults"] = anuncios
    copia["data"] = dados_copia

    return copia


def respostas_por_pagina(respostas):
    """
    Escolhe a resposta mais completa de cada página.

    Critérios:
    - URL interna, actualPage e PageCurrent coincidentes;
    - consulta de usados em São Paulo;
    - anúncios individualmente identificados como usados;
    - maior quantidade de anúncios válidos;
    - em caso de empate, mantém a resposta capturada mais recentemente.
    """

    candidatas = {}

    for indice, resposta in enumerate(respostas):
        filtrada = preparar_resposta_filtrada(resposta)

        if filtrada is None:
            continue

        info = analisar_resposta(filtrada)
        pagina = info["pagina"]

        candidatas.setdefault(pagina, []).append(
            (len(info["resultados"]), indice, filtrada)
        )

    selecionadas = {}

    for pagina, opcoes in candidatas.items():
        # Maior quantidade de anúncios; desempate pela captura mais recente.
        _, _, melhor = max(
            opcoes,
            key=lambda item: (item[0], item[1])
        )
        selecionadas[pagina] = melhor

    return selecionadas


def obter_ids_validos(respostas):
    ids = set()

    for resposta in respostas:
        info = analisar_resposta(resposta)

        if info is None:
            continue

        for veiculo in info["resultados"]:
            if anuncio_usado_valido(veiculo):
                ids.add(str(veiculo["UniqueId"]))

    return ids


def esperar_pagina(respostas, pagina_alvo, tempo_maximo_ms):
    """Espera até que apareça uma resposta consistente da página desejada."""

    decorrido = 0
    intervalo = 500

    while decorrido < tempo_maximo_ms:
        paginas = respostas_por_pagina(respostas)

        if pagina_alvo in paginas:
            return True

        page.wait_for_timeout(intervalo)
        decorrido += intervalo

    return pagina_alvo in respostas_por_pagina(respostas)


# ============================================================
# PREPARAÇÃO
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

pasta_execucao = DIR_DIAGNOSTICO / f"coleta_{timestamp}"
pasta_execucao.mkdir(parents=True, exist_ok=True)

arquivo_bruto = pasta_execucao / "respostas_json_completas.json"
arquivo_filtrado = pasta_execucao / "respostas_anuncios_sp_usados.json"

print("=" * 70)
print("COLETA AUTOMÁTICA WEBMOTORS")
print("=" * 70)

print(f"\nLimite de páginas: {MAX_PAGINAS}")
print(f"Pasta de saída: {pasta_execucao}")


# ============================================================
# COLETA
# ============================================================

respostas_json = []

with sync_playwright() as playwright:

    print("\n[1] Iniciando navegador...")

    browser = playwright.chromium.launch(headless=False)

    page = browser.new_page(
        viewport={"width": 1440, "height": 900},
        locale="pt-BR"
    )

    # --------------------------------------------------------
    # CAPTURA DAS RESPOSTAS JSON
    # --------------------------------------------------------

    def capturar_resposta(response):
        try:
            content_type = response.headers.get(
                "content-type", ""
            ).lower()

            if "application/json" not in content_type:
                return

            try:
                dados = response.json()
            except Exception:
                return

            respostas_json.append({
                "url": response.url,
                "status": response.status,
                "method": response.request.method,
                "data": dados,
            })

        except Exception:
            pass

    page.on("response", capturar_resposta)

    # --------------------------------------------------------
    # ABERTURA
    # --------------------------------------------------------

    print("\n[2] Abrindo Webmotors...")

    try:
        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=120000
        )
    except Exception as erro:
        print("Aviso durante a abertura:", erro)

    page.wait_for_timeout(TEMPO_INICIAL_MS)

    print("URL atual:", page.url)

    # --------------------------------------------------------
    # PRIMEIRA PÁGINA
    # --------------------------------------------------------

    print("\n[3] Validando primeira página...")

    if not esperar_pagina(
        respostas_json,
        1,
        TEMPO_MAXIMO_CONFIRMACAO_MS
    ):
        print(
            "Aviso: não foi possível confirmar a página 1 "
            "com os critérios definidos."
        )
    else:
        info = analisar_resposta(
            respostas_por_pagina(respostas_json)[1]
        )
        print(
            f"Página 1 confirmada: "
            f"{len(info['resultados'])} anúncios usados válidos."
        )

    # --------------------------------------------------------
    # PAGINAÇÃO
    # --------------------------------------------------------

    print("\n[4] Coletando páginas...")

    for pagina_alvo in range(2, MAX_PAGINAS + 1):

        paginas = respostas_por_pagina(respostas_json)

        if pagina_alvo in paginas:
            info = analisar_resposta(paginas[pagina_alvo])
            print(
                f"Página {pagina_alvo} já capturada: "
                f"{len(info['resultados'])} anúncios válidos."
            )
            continue

        botao = page.locator(
            'button[aria-label="Próxima página"]'
        )

        if botao.count() == 0 or not botao.is_enabled():
            print("Botão de próxima página indisponível.")
            break

        print(f"\nSolicitando página {pagina_alvo}...")

        try:
            botao.click(timeout=15000)
            page.wait_for_timeout(TEMPO_ESPERA_PAGINA_MS)

        except Exception as erro:
            print("Erro durante a paginação:", erro)
            break

        print("URL do navegador:", page.url)

        if not esperar_pagina(
            respostas_json,
            pagina_alvo,
            TEMPO_MAXIMO_CONFIRMACAO_MS
        ):
            print(
                f"Página {pagina_alvo} não confirmada. "
                "Interrompendo para evitar dados incorretos."
            )
            break

        paginas = respostas_por_pagina(respostas_json)
        info = analisar_resposta(paginas[pagina_alvo])

        print(
            f"Página {pagina_alvo} confirmada: "
            f"{len(info['resultados'])} anúncios usados válidos."
        )

    # --------------------------------------------------------
    # CONSOLIDAÇÃO
    # --------------------------------------------------------

    print("\n[5] Consolidando respostas...")

    paginas = respostas_por_pagina(respostas_json)

    respostas_filtradas = [
        paginas[numero]
        for numero in sorted(paginas)
    ]

    salvar_json(arquivo_bruto, respostas_json)
    salvar_json(arquivo_filtrado, respostas_filtradas)

    # --------------------------------------------------------
    # RESUMO
    # --------------------------------------------------------

    total_anuncios = sum(
        len(analisar_resposta(resposta)["resultados"])
        for resposta in respostas_filtradas
    )

    ids_unicos = obter_ids_validos(respostas_filtradas)

    print("\n[6] RESUMO DA COLETA")
    print("-" * 70)
    print("Páginas capturadas:", sorted(paginas))
    print("Respostas filtradas:", len(respostas_filtradas))
    print("Anúncios válidos somados:", total_anuncios)
    print("UniqueId únicos globalmente:", len(ids_unicos))

    print("\nDetalhamento:")

    for resposta in respostas_filtradas:
        info = analisar_resposta(resposta)
        ids_pagina = {
            str(v["UniqueId"])
            for v in info["resultados"]
        }

        print(
            f"Página {info['pagina']}: "
            f"{len(info['resultados'])} anúncios válidos, "
            f"{len(ids_pagina)} IDs únicos"
        )

    if len(ids_unicos) < total_anuncios:
        print(
            "\nATENÇÃO: existem anúncios repetidos entre páginas. "
            "A deduplicação global deverá ser aplicada na validação."
        )

    if len(paginas) < MAX_PAGINAS:
        print(
            "\nATENÇÃO: coleta parcial. "
            "Nem todas as páginas solicitadas foram confirmadas."
        )

    print("\n[7] Fechando navegador...")
    browser.close()


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("COLETA FINALIZADA")
print("=" * 70)

print("Arquivo bruto:", arquivo_bruto)
print("Arquivo filtrado:", arquivo_filtrado)
