
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
import json
import re

import pandas as pd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DIRETORIO_DIAGNOSTICO = (
    BASE_DIR
    / "data"
    / "bronze"
    / "webmotors"
    / "diagnostico"
)

PADRAO_COLETA = "coleta_*"

ARQUIVO_BRONZE = (
    BASE_DIR
    / "data"
    / "bronze"
    / "webmotors"
    / "01_anuncios_brutos.parquet"
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def localizar_arquivo_entrada():
    """Localiza a coleta mais recente com anúncios filtrados."""

    arquivos = list(
        DIRETORIO_DIAGNOSTICO.glob(
            f"{PADRAO_COLETA}/respostas_anuncios_sp_usados.json"
        )
    )

    if not arquivos:
        raise FileNotFoundError(
            "Nenhum arquivo respostas_anuncios_sp_usados.json "
            f"foi encontrado em {DIRETORIO_DIAGNOSTICO}"
        )

    return max(
        arquivos,
        key=lambda caminho: caminho.parent.name,
    )


def obter_data_coleta(caminho_arquivo):
    """Extrai a data do nome da pasta da coleta."""

    nome_pasta = caminho_arquivo.parent.name

    padrao = re.search(
        r"coleta_(\d{8})_\d{6}",
        nome_pasta,
    )

    if not padrao:
        return None

    data = pd.to_datetime(
        padrao.group(1),
        format="%Y%m%d",
        errors="coerce",
    )

    if pd.isna(data):
        return None

    return data.date()


def obter_primeira_localizacao(seller):
    """Retorna a primeira localização válida do vendedor."""

    localizacoes = seller.get("Localization")

    if not isinstance(localizacoes, list):
        return {}

    for localizacao in localizacoes:
        if isinstance(localizacao, dict):
            return localizacao

    return {}


def valor_ou_none(valor):
    """Converte strings vazias em None."""

    if valor is None:
        return None

    if isinstance(valor, str) and not valor.strip():
        return None

    return valor


def extrair_numero(valor):
    """
    Extrai o primeiro número de valores como '265 cv' ou '2.0'.

    Retorna None quando não há um número válido.
    """

    if valor is None or isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        return valor

    texto = str(valor).strip()

    if not texto:
        return None

    encontrado = re.search(
        r"(?<!\d)\d+(?:[.,]\d+)?",
        texto,
    )

    if not encontrado:
        return None

    numero = encontrado.group(0).replace(",", ".")

    try:
        return float(numero)
    except ValueError:
        return None


def extrair_combustivel(specification, version):
    """
    Identifica o combustível apenas quando há evidência textual.

    Consulta campos explícitos da API e o título/versão do anúncio.
    Não tenta deduzir o combustível apenas pela marca ou modelo.
    """

    campos_combustivel = (
        "Fuel",
        "FuelType",
        "FuelName",
        "FuelTypeName",
        "FuelTypeDescription",
    )

    textos = []

    # Procura campos de combustível fornecidos pela API.
    for campo in campos_combustivel:
        valor = specification.get(campo)

        if isinstance(valor, dict):
            valor = (
                valor.get("Value")
                or valor.get("Name")
                or valor.get("Description")
            )

        if isinstance(valor, str) and valor.strip():
            textos.append(valor)

    # Considera o título, quando disponível.
    titulo = specification.get("Title")

    if isinstance(titulo, str) and titulo.strip():
        textos.append(titulo)

    # Considera a versão do veículo.
    if isinstance(version, dict):
        versao = version.get("Value")

        if isinstance(versao, str) and versao.strip():
            textos.append(versao)

    texto = " ".join(textos).upper()

    # Classificações específicas primeiro.
    if re.search(r"\bHIBRIDO\b|\bHÍBRIDO\b|\bHYBRID\b", texto):
        return "Híbrido"

    if re.search(r"\bELETRICO\b|\bELÉTRICO\b|\bELECTRIC\b", texto):
        return "Elétrico"

    if re.search(r"\bFLEX\b", texto):
        return "Flex"

    if re.search(r"\bDIESEL\b", texto):
        return "Diesel"

    if re.search(r"\bGASOLINA\b", texto):
        return "Gasolina"

    if re.search(r"\bETANOL\b|\bALCOOL\b|\bÁLCOOL\b", texto):
        return "Etanol"

    if re.search(r"\bGNV\b", texto):
        return "GNV"

    return None


def extrair_veiculos(respostas):
    """
    Consolida todas as páginas do arquivo filtrado.

    Regras:
    - aceita apenas respostas com SearchResults;
    - exige UniqueId válido;
    - exclui anúncios com MediaZeroKm diferente de False;
    - remove duplicatas globalmente por UniqueId.
    """

    registros_por_id = {}
    total_lidos = 0
    invalidos = 0
    duplicados = 0
    zero_km = 0

    paginas = set()

    for resposta in respostas:

        if not isinstance(resposta, dict):
            continue

        data = resposta.get("data")

        if not isinstance(data, dict):
            continue

        resultados = data.get("SearchResults")

        if not isinstance(resultados, list):
            continue

        # Identifica a página pela URL interna da consulta.
        url_api = resposta.get("url", "")
        parametros_api = parse_qs(urlparse(url_api).query)
        url_interna = parametros_api.get("url", [""])[0]

        if url_interna:
            for _ in range(3):
                decodificada = unquote(url_interna)

                if decodificada == url_interna:
                    break

                url_interna = decodificada

            parametros_internos = parse_qs(
                urlparse(url_interna).query
            )

            pagina_texto = parametros_internos.get(
                "page", [""]
            )[0]

            try:
                paginas.add(int(pagina_texto))
            except (TypeError, ValueError):
                pass

        for veiculo in resultados:

            total_lidos += 1

            if not isinstance(veiculo, dict):
                invalidos += 1
                continue

            unique_id = veiculo.get("UniqueId")

            if unique_id in (None, "", 0, "0"):
                invalidos += 1
                continue

            # Aceita apenas anúncios explicitamente usados.
            if veiculo.get("MediaZeroKm") is not False:
                zero_km += 1
                continue

            unique_id = str(unique_id)

            if unique_id in registros_por_id:
                duplicados += 1
                continue

            registros_por_id[unique_id] = veiculo

    print(f"Páginas identificadas: {sorted(paginas)}")
    print(f"Registros lidos: {total_lidos}")
    print(f"Registros sem ID válido: {invalidos}")
    print(f"Registros zero-quilômetro excluídos: {zero_km}")
    print(f"Duplicatas excluídas: {duplicados}")

    return list(registros_por_id.values())


def transformar_veiculo(veiculo, data_coleta):
    """Transforma um anúncio na estrutura da Bronze 2."""

    specification = veiculo.get("Specification") or {}
    seller = veiculo.get("Seller") or {}
    prices = veiculo.get("Prices") or {}

    make = specification.get("Make") or {}
    model = specification.get("Model") or {}
    version = specification.get("Version") or {}
    color = specification.get("Color") or {}

    localization = obter_primeira_localizacao(seller)

    return {
        "webmotors_id": str(veiculo.get("UniqueId")),

        "nome_marca": valor_ou_none(make.get("Value")),
        "nome_modelo": valor_ou_none(model.get("Value")),
        "nome_versao": valor_ou_none(version.get("Value")),

        "ano_fabricacao": specification.get("YearFabrication"),
        "ano_modelo": specification.get("YearModel"),
        "quilometragem": specification.get("Odometer"),

        "nome_combustivel": extrair_combustivel(
            specification,
            version,
        ),

        "cambio": valor_ou_none(
            specification.get("Transmission")
        ),
        "carroceria": valor_ou_none(
            specification.get("BodyType")
        ),
        "cor": valor_ou_none(color.get("Primary")),

        "potencia": extrair_numero(
            specification.get("HorsePower")
        ),
        "cilindrada": extrair_numero(
            specification.get("EngineSize")
        ),

        "tracao": valor_ou_none(
            specification.get("Traction")
        ),
        "blindado": specification.get("Armored"),
        "leilao": specification.get("Auction"),

        "valor_anuncio": prices.get("Price"),

        "cidade": valor_ou_none(seller.get("City")),
        "estado": valor_ou_none(seller.get("State")),
        "bairro": valor_ou_none(
            localization.get("Neighborhood")
        ),
        "cep": valor_ou_none(
            localization.get("ZipCode")
        ),

        "vendedor_id": seller.get("Id"),
        "tipo_vendedor": valor_ou_none(
            seller.get("SellerType")
        ),

        "atributos_veiculo": (
            json.dumps(
                specification.get("VehicleAttributes"),
                ensure_ascii=False,
            )
            if specification.get("VehicleAttributes") is not None
            else None
        ),

        "descricao": valor_ou_none(
            veiculo.get("LongComment")
        ),

        "fipe_percent": veiculo.get("FipePercent"),
        "good_deal": veiculo.get("GoodDeal"),

        "data_coleta": data_coleta,
    }


def transformar_registros(veiculos, data_coleta):
    """Transforma a lista de anúncios em um DataFrame."""

    registros = [
        transformar_veiculo(veiculo, data_coleta)
        for veiculo in veiculos
    ]

    return pd.DataFrame(registros)


def converter_colunas_numericas(df):
    """Converte os campos numéricos conhecidos."""

    colunas = [
        "ano_fabricacao",
        "ano_modelo",
        "quilometragem",
        "potencia",
        "cilindrada",
        "valor_anuncio",
        "fipe_percent",
    ]

    for coluna in colunas:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(
                df[coluna],
                errors="coerce",
            )

    return df


# ============================================================
# EXECUÇÃO
# ============================================================

print("=" * 70)
print("VALIDAÇÃO DOS DADOS BRUTOS — WEBMOTORS")
print("=" * 70)


# ------------------------------------------------------------
# [1] ARQUIVO E DATA DA COLETA
# ------------------------------------------------------------

print("\n[1] Localizando a coleta mais recente...")

ARQUIVO_ENTRADA = localizar_arquivo_entrada()

print(f"Arquivo: {ARQUIVO_ENTRADA}")

data_coleta = obter_data_coleta(ARQUIVO_ENTRADA)

if data_coleta is None:
    raise ValueError(
        "Não foi possível identificar a data da coleta."
    )

print(f"Data da coleta: {data_coleta}")

with open(ARQUIVO_ENTRADA, "r", encoding="utf-8") as arquivo:
    respostas = json.load(arquivo)

if not isinstance(respostas, list):
    raise ValueError(
        "O arquivo filtrado deveria conter uma lista de respostas."
    )

print(f"Respostas filtradas: {len(respostas)}")


# ------------------------------------------------------------
# [2] EXTRAÇÃO E CONSOLIDAÇÃO
# ------------------------------------------------------------

print("\n[2] Extraindo e consolidando anúncios...")

veiculos = extrair_veiculos(respostas)

print(f"Anúncios consolidados: {len(veiculos)}")

if not veiculos:
    raise ValueError(
        "Nenhum anúncio válido foi encontrado. "
        "Verifique o arquivo filtrado da coleta."
    )


# ------------------------------------------------------------
# [3] TRANSFORMAÇÃO
# ------------------------------------------------------------

print("\n[3] Transformando registros...")

df = transformar_registros(
    veiculos,
    data_coleta,
)

df = converter_colunas_numericas(df)

print(f"Linhas: {len(df)}")
print(f"Colunas: {len(df.columns)}")


# ------------------------------------------------------------
# [4] VALIDAÇÃO DE ESTRUTURA E NULOS
# ------------------------------------------------------------

print("\n[4] Estrutura e valores nulos...")

for coluna in df.columns:
    nulos = int(df[coluna].isna().sum())
    percentual = nulos / len(df) * 100

    print(
        f" - {coluna}: {df[coluna].dtype}; "
        f"{nulos} nulos ({percentual:.2f}%)"
    )


# ------------------------------------------------------------
# [5] VALIDAÇÃO DE IDENTIFICADORES
# ------------------------------------------------------------

print("\n[5] Validação de UniqueId...")

duplicados = int(df["webmotors_id"].duplicated().sum())
unicos = int(df["webmotors_id"].nunique())

print(f"IDs duplicados: {duplicados}")
print(f"IDs únicos: {unicos}")

if duplicados:
    raise ValueError(
        "Foram encontrados UniqueIds duplicados após a consolidação."
    )


# ------------------------------------------------------------
# [6] VALIDAÇÃO DE CAMPOS NUMÉRICOS
# ------------------------------------------------------------

print("\n[6] Estatísticas dos principais campos...")

for coluna in [
    "ano_fabricacao",
    "ano_modelo",
    "quilometragem",
    "potencia",
    "cilindrada",
    "valor_anuncio",
    "fipe_percent",
]:
    serie = df[coluna]

    print(f"\n{coluna}:")
    print(f"  preenchidos: {serie.notna().sum()}")
    print(f"  nulos: {serie.isna().sum()}")

    if serie.notna().any():
        print(f"  mínimo: {serie.min()}")
        print(f"  máximo: {serie.max()}")


# ------------------------------------------------------------
# [7] VALIDAÇÃO DO PREÇO
# ------------------------------------------------------------

print("\n[7] Validação do valor do anúncio...")

precos = df["valor_anuncio"]

precos_positivos = precos.notna() & (precos > 0)
precos_invalidos = precos.notna() & (precos <= 0)

print(f"Preços preenchidos: {precos.notna().sum()}")
print(f"Preços positivos: {precos_positivos.sum()}")
print(f"Preços nulos: {precos.isna().sum()}")
print(
    "Preços menores ou iguais a zero: "
    f"{precos_invalidos.sum()}"
)

if precos_positivos.any():
    print(
        "Menor preço positivo: "
        f"R$ {precos[precos_positivos].min():,.2f}"
    )
    print(
        "Maior preço positivo: "
        f"R$ {precos[precos_positivos].max():,.2f}"
    )
    print(
        "Preço médio positivo: "
        f"R$ {precos[precos_positivos].mean():,.2f}"
    )


# ------------------------------------------------------------
# [8] CATEGORIAS
# ------------------------------------------------------------

print("\n[8] Principais valores categóricos...")

for coluna in [
    "nome_marca",
    "nome_modelo",
    "nome_combustivel",
    "cambio",
    "carroceria",
    "cor",
    "estado",
    "tipo_vendedor",
]:
    print(
        f"\n{coluna}: "
        f"{df[coluna].nunique(dropna=True)} valores distintos"
    )

    print(
        df[coluna]
        .value_counts(dropna=False)
        .head(10)
        .to_string()
    )


# ------------------------------------------------------------
# [9] AMOSTRA
# ------------------------------------------------------------

print("\n[9] Amostra dos anúncios...\n")

colunas_amostra = [
    "webmotors_id",
    "nome_marca",
    "nome_modelo",
    "nome_versao",
    "nome_combustivel",
    "potencia",
    "cilindrada",
    "ano_modelo",
    "quilometragem",
    "valor_anuncio",
    "cidade",
    "estado",
    "data_coleta",
]

print(
    df[colunas_amostra]
    .sample(
        n=min(10, len(df)),
        random_state=42,
    )
    .to_string(index=False)
)


# ------------------------------------------------------------
# [10] GRAVAÇÃO DO PARQUET
# ------------------------------------------------------------

print("\n[10] Gravando a tabela Bronze 2...")

ARQUIVO_BRONZE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_parquet(
    ARQUIVO_BRONZE,
    index=False,
    engine="pyarrow",
)

print(f"Arquivo gravado: {ARQUIVO_BRONZE}")
print(f"Tamanho: {ARQUIVO_BRONZE.stat().st_size:,} bytes")


# ------------------------------------------------------------
# FINAL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDAÇÃO CONCLUÍDA")
print("=" * 70)
