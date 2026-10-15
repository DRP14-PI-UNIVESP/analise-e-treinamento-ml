
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_ENTRADA = (
    BASE_DIR
    / "data"
    / "bronze"
    / "webmotors"
    / "01_anuncios_brutos.parquet"
)

ARQUIVO_SAIDA = (
    BASE_DIR
    / "data"
    / "prata"
    / "webmotors"
    / "02_webmotors_limpo.parquet"
)


COLUNAS_OBRIGATORIAS = [
    "webmotors_id",
    "nome_marca",
    "nome_modelo",
    "nome_versao",
    "ano_fabricacao",
    "ano_modelo",
    "quilometragem",
    "nome_combustivel",
    "cambio",
    "carroceria",
    "cor",
    "potencia",
    "cilindrada",
    "tracao",
    "blindado",
    "leilao",
    "valor_anuncio",
    "cidade",
    "estado",
    "bairro",
    "cep",
    "vendedor_id",
    "tipo_vendedor",
    "atributos_veiculo",
    "descricao",
    "fipe_percent",
    "good_deal",
    "data_coleta",
]


COLUNAS_TEXTO = [
    "nome_marca",
    "nome_modelo",
    "nome_versao",
    "nome_combustivel",
    "cambio",
    "carroceria",
    "cor",
    "tracao",
    "blindado",
    "cidade",
    "estado",
    "bairro",
    "cep",
    "tipo_vendedor",
]


COLUNAS_INTEIRAS = [
    "ano_fabricacao",
    "ano_modelo",
    "quilometragem",
]


COLUNAS_NUMERICAS = [
    "potencia",
    "cilindrada",
    "valor_anuncio",
    "fipe_percent",
]


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def converter_inteiro_opcional(serie, nome_coluna):
    """Converte para inteiro anulável e rejeita frações."""

    valores = pd.to_numeric(serie, errors="coerce")

    conversao_invalida = serie.notna() & valores.isna()

    if conversao_invalida.any():
        print(
            f"  Atenção: {conversao_invalida.sum()} "
            f"valores inválidos convertidos em nulos "
            f"na coluna {nome_coluna}."
        )

    fracionarios = valores.notna() & ((valores % 1) != 0)

    if fracionarios.any():
        exemplos = valores[fracionarios].head(5).tolist()

        raise ValueError(
            f"A coluna {nome_coluna} possui valores fracionários. "
            f"Exemplos: {exemplos}"
        )

    return valores.astype("Int64")


def imprimir_estatisticas_numericas(df, coluna):
    """Imprime estatísticas de uma coluna numérica."""

    serie = df[coluna]

    print(f"\n{coluna}:")
    print(f"  Preenchidos: {serie.notna().sum()}")
    print(f"  Nulos: {serie.isna().sum()}")

    if serie.notna().any():
        print(f"  Mínimo: {serie.min()}")
        print(f"  Máximo: {serie.max()}")


# ============================================================
# EXECUÇÃO
# ============================================================

def main():
    print("=" * 70)
    print("PREPARAÇÃO DA TABELA PRATA 2 — WEBMOTORS")
    print("=" * 70)

    # --------------------------------------------------------
    # [1] VERIFICAR ARQUIVOS
    # --------------------------------------------------------

    print("\n[1] Verificando arquivos...")

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo Bronze não encontrado: {ARQUIVO_ENTRADA}"
        )

    ARQUIVO_SAIDA.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(f"Entrada: {ARQUIVO_ENTRADA}")
    print(f"Saída: {ARQUIVO_SAIDA}")

    # --------------------------------------------------------
    # [2] LER A BRONZE
    # --------------------------------------------------------

    print("\n[2] Lendo a tabela Bronze...")

    df = pd.read_parquet(ARQUIVO_ENTRADA)

    quantidade_inicial = len(df)
    colunas_iniciais = len(df.columns)

    print(f"Linhas: {quantidade_inicial:,}")
    print(f"Colunas: {colunas_iniciais}")

    if df.empty:
        raise ValueError("A tabela Bronze não possui registros.")

    # --------------------------------------------------------
    # [3] VALIDAR ESTRUTURA
    # --------------------------------------------------------

    print("\n[3] Validando a estrutura...")

    ausentes = [
        coluna
        for coluna in COLUNAS_OBRIGATORIAS
        if coluna not in df.columns
    ]

    if ausentes:
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            + ", ".join(ausentes)
        )

    print("Todas as colunas obrigatórias estão presentes.")

    # --------------------------------------------------------
    # [4] PADRONIZAR TEXTOS
    # --------------------------------------------------------

    print("\n[4] Padronizando textos...")

    for coluna in COLUNAS_TEXTO:
        df[coluna] = (
            df[coluna]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    # Identificadores são textos, não medidas numéricas.
    df["webmotors_id"] = (
        df["webmotors_id"]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    # Mantém vendedor_id como inteiro anulável.
    # Ele será tratado como identificador, não como atributo do veículo.
    df["vendedor_id"] = converter_inteiro_opcional(
        df["vendedor_id"],
        "vendedor_id",
    )

    print("Textos e identificadores tratados.")

    # --------------------------------------------------------
    # [5] CONVERTER TIPOS NUMÉRICOS
    # --------------------------------------------------------

    print("\n[5] Convertendo campos numéricos...")

    for coluna in COLUNAS_INTEIRAS:
        df[coluna] = converter_inteiro_opcional(
            df[coluna],
            coluna,
        )

    for coluna in COLUNAS_NUMERICAS:
        originais = df[coluna]
        convertidos = pd.to_numeric(
            originais,
            errors="coerce",
        )

        invalidos = originais.notna() & convertidos.isna()

        if invalidos.any():
            print(
                f"  Atenção: {invalidos.sum()} valores "
                f"não numéricos em {coluna} foram convertidos em nulos."
            )

        df[coluna] = convertidos.astype("Float64")

    # --------------------------------------------------------
    # [6] VALIDAR IDENTIFICADORES
    # --------------------------------------------------------

    print("\n[6] Validando identificadores...")

    if df["webmotors_id"].isna().any():
        raise ValueError(
            "Existem anúncios sem webmotors_id válido."
        )

    duplicados = int(
        df["webmotors_id"].duplicated(keep=False).sum()
    )

    print(f"Registros envolvidos em IDs duplicados: {duplicados}")
    print(f"IDs únicos: {df['webmotors_id'].nunique()}")

    if duplicados:
        raise ValueError(
            "Foram encontrados webmotors_id duplicados. "
            "Investigue antes de continuar."
        )

    print(
        "Vendedores sem ID: "
        f"{df['vendedor_id'].isna().sum()}"
    )

    # --------------------------------------------------------
    # [7] VALIDAR PREÇOS E QUILOMETRAGEM
    # --------------------------------------------------------

    print("\n[7] Validando preços e quilometragem...")

    precos_invalidos = (
        df["valor_anuncio"].isna()
        | (df["valor_anuncio"] <= 0)
    )

    km_negativos = (
        df["quilometragem"].notna()
        & (df["quilometragem"] < 0)
    )

    print(f"Preços nulos ou menores/iguais a zero: {precos_invalidos.sum()}")
    print(f"Quilometragens negativas: {km_negativos.sum()}")

    if precos_invalidos.any():
        raise ValueError(
            "Existem preços nulos, inválidos ou menores/iguais a zero."
        )

    if km_negativos.any():
        raise ValueError(
            "Existem quilometragens negativas."
        )

    # Não removemos automaticamente preços altos.
    # Valores extremos serão apenas sinalizados para auditoria.
    print(
        "Preços acima de R$ 500.000: "
        f"{(df['valor_anuncio'] > 500000).sum()}"
    )

    print(
        "Quilometragens acima de 300.000 km: "
        f"{(df['quilometragem'] > 300000).sum()}"
    )

    # --------------------------------------------------------
    # [8] AUDITAR ANOS
    # --------------------------------------------------------

    print("\n[8] Auditando anos de fabricação e modelo...")

    for coluna in ["ano_fabricacao", "ano_modelo"]:
        invalidos = (
            df[coluna].notna()
            & ~df[coluna].between(1886, 2100)
        )

        print(f"{coluna} fora do intervalo: {invalidos.sum()}")

        if invalidos.any():
            exemplos = df.loc[invalidos, coluna].head(10).tolist()
            print(f"  Exemplos: {exemplos}")

    anos_inconsistentes = (
        df["ano_fabricacao"].notna()
        & df["ano_modelo"].notna()
        & (df["ano_modelo"] < df["ano_fabricacao"])
    )

    print(
        "Ano-modelo anterior ao ano de fabricação: "
        f"{anos_inconsistentes.sum()}"
    )

    idade_suspeita = (
        df["ano_modelo"].notna()
        & df["ano_modelo"].ge(2020)
        & df["quilometragem"].gt(200000)
    )

    print(
        "Veículos de modelo 2020 ou posterior com mais de "
        f"200.000 km: {idade_suspeita.sum()}"
    )

    # As inconsistências são registradas, não excluídas automaticamente.

    # --------------------------------------------------------
    # [9] AUDITORIA DA DATA DE COLETA
    # --------------------------------------------------------

    print("\n[9] Tratando a data de coleta...")

    datas_originais = df["data_coleta"].copy()

    df["data_coleta"] = pd.to_datetime(
        df["data_coleta"],
        errors="coerce",
    )

    datas_invalidas = (
        datas_originais.notna()
        & df["data_coleta"].isna()
    )

    print(f"Datas inválidas: {datas_invalidas.sum()}")

    if datas_invalidas.any() or df["data_coleta"].isna().any():
        raise ValueError(
            "Existem datas de coleta nulas ou inválidas."
        )

    # --------------------------------------------------------
    # [10] AUDITORIA DE VALORES NULOS
    # --------------------------------------------------------

    print("\n[10] Resumo de valores nulos...")

    nulos = df.isna().sum()
    colunas_com_nulos = nulos[nulos > 0]

    if colunas_com_nulos.empty:
        print("Nenhum valor nulo encontrado.")
    else:
        for coluna, quantidade in colunas_com_nulos.items():
            percentual = quantidade / len(df) * 100

            print(
                f" - {coluna}: {quantidade} "
                f"({percentual:.2f}%)"
            )

    campos_totalmente_nulos = [
        coluna
        for coluna in df.columns
        if df[coluna].isna().all()
    ]

    print(
        "Campos totalmente nulos: "
        + (
            ", ".join(campos_totalmente_nulos)
            if campos_totalmente_nulos
            else "nenhum"
        )
    )

    # --------------------------------------------------------
    # [11] ESTATÍSTICAS NUMÉRICAS
    # --------------------------------------------------------

    print("\n[11] Estatísticas numéricas...")

    for coluna in [
        "ano_fabricacao",
        "ano_modelo",
        "quilometragem",
        "potencia",
        "cilindrada",
        "valor_anuncio",
        "fipe_percent",
    ]:
        imprimir_estatisticas_numericas(df, coluna)

    # --------------------------------------------------------
    # [12] GRAVAR A PRATA
    # --------------------------------------------------------

    print("\n[12] Gravando a tabela Prata...")

    df.to_parquet(
        ARQUIVO_SAIDA,
        index=False,
        engine="pyarrow",
    )

    # --------------------------------------------------------
    # [13] VALIDAR O RESULTADO
    # --------------------------------------------------------

    print("\n[13] Validando o arquivo gerado...")

    verificado = pd.read_parquet(ARQUIVO_SAIDA)

    if len(verificado) != quantidade_inicial:
        raise RuntimeError(
            "A quantidade de registros mudou após a gravação."
        )

    if list(verificado.columns) != list(df.columns):
        raise RuntimeError(
            "As colunas do arquivo gerado diferem das colunas tratadas."
        )

    if verificado["webmotors_id"].duplicated().any():
        raise RuntimeError(
            "O arquivo final contém IDs duplicados."
        )

    print(f"Linhas de entrada: {quantidade_inicial:,}")
    print(f"Linhas de saída: {len(verificado):,}")
    print(f"Colunas de entrada: {colunas_iniciais}")
    print(f"Colunas de saída: {len(verificado.columns)}")
    print(f"Tamanho: {ARQUIVO_SAIDA.stat().st_size:,} bytes")
    print(f"Arquivo: {ARQUIVO_SAIDA}")

    print("\n" + "=" * 70)
    print("PREPARAÇÃO DA PRATA 2 CONCLUÍDA")
    print("=" * 70)


if __name__ == "__main__":
    main()
