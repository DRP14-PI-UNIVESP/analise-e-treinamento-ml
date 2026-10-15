
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_ENTRADA = (
    BASE_DIR
    / "data"
    / "prata"
    / "webmotors"
    / "02_webmotors_limpo.parquet"
)

ARQUIVO_SAIDA = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "03_webmotors_ouro.parquet"
)


# ============================================================
# PREPARAÇÃO DA TABELA OURO
# ============================================================

def main():
    print("=" * 70)
    print("PREPARAÇÃO DA TABELA OURO — WEBMOTORS")
    print("=" * 70)

    # 1. Verificar arquivo de entrada
    print("\n[1] Verificando arquivo de entrada...")

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {ARQUIVO_ENTRADA}"
        )

    print(f"Entrada: {ARQUIVO_ENTRADA}")

    # 2. Carregar dados da Prata
    print("\n[2] Carregando dados da Prata...")

    df = pd.read_parquet(ARQUIVO_ENTRADA)

    quantidade_inicial = len(df)
    colunas_iniciais = len(df.columns)

    print(f"Linhas carregadas: {quantidade_inicial:,}")
    print(f"Colunas carregadas: {colunas_iniciais}")

    if df.empty:
        raise ValueError("A tabela Prata está vazia.")

    # 3. Validar dados essenciais
    print("\n[3] Validando dados essenciais...")

    colunas_obrigatorias = [
        "webmotors_id",
        "valor_anuncio",
        "ano_modelo",
        "quilometragem",
        "data_coleta",
    ]

    ausentes = [
        coluna
        for coluna in colunas_obrigatorias
        if coluna not in df.columns
    ]

    if ausentes:
        raise ValueError(
            f"Colunas obrigatórias ausentes: {ausentes}"
        )

    if df["webmotors_id"].isna().any():
        raise ValueError(
            "Existem anúncios sem identificador."
        )

    if df["webmotors_id"].duplicated().any():
        raise ValueError(
            "Existem identificadores duplicados."
        )

    df["valor_anuncio"] = pd.to_numeric(
        df["valor_anuncio"],
        errors="coerce",
    )

    if df["valor_anuncio"].isna().any():
        raise ValueError(
            "Existem anúncios sem preço numérico válido."
        )

    if (df["valor_anuncio"] <= 0).any():
        raise ValueError(
            "Existem preços menores ou iguais a zero."
        )

    df["ano_modelo"] = pd.to_numeric(
        df["ano_modelo"],
        errors="coerce",
    ).astype("Int64")

    df["quilometragem"] = pd.to_numeric(
        df["quilometragem"],
        errors="coerce",
    ).astype("Int64")

    print("Identificadores: válidos e únicos.")
    print("Preços: válidos e positivos.")

    # 4. Normalizar data de coleta
    print("\n[4] Preparando datas...")

    df["data_coleta"] = pd.to_datetime(
        df["data_coleta"],
        errors="coerce",
    )

    datas_invalidas = int(df["data_coleta"].isna().sum())

    print(f"Datas de coleta inválidas: {datas_invalidas}")

    # 5. Criar variáveis derivadas
    print("\n[5] Criando variáveis derivadas...")

    # Idade calculada pelo ano da coleta, não pelo ano atual.
    ano_coleta = df["data_coleta"].dt.year.astype("Int64")

    df["idade_veiculo"] = (
        ano_coleta - df["ano_modelo"]
    ).astype("Int64")

    df.loc[
        df["idade_veiculo"] < 0,
        "idade_veiculo",
    ] = pd.NA

    # Preço por quilômetro.
    # Quilometragem ausente ou zero resulta em valor ausente.
    quilometragem_positiva = df["quilometragem"].where(
        df["quilometragem"] > 0
    )

    df["preco_por_km"] = (
        df["valor_anuncio"]
        .div(quilometragem_positiva)
        .round(2)
        .astype("Float64")
    )

    # Faixas de preço para análise exploratória.
    # Não utilizar como variável preditora do próprio preço.
    df["faixa_preco"] = pd.cut(
        df["valor_anuncio"],
        bins=[
            0,
            50_000,
            100_000,
            200_000,
            500_000,
            1_000_000,
            float("inf"),
        ],
        labels=[
            "Até R$ 50 mil",
            "R$ 50–100 mil",
            "R$ 100–200 mil",
            "R$ 200–500 mil",
            "R$ 500 mil–1 milhão",
            "Acima de R$ 1 milhão",
        ],
        include_lowest=True,
    ).astype("string")

    # Faixas de quilometragem para análise exploratória.
    df["faixa_quilometragem"] = pd.cut(
        df["quilometragem"],
        bins=[
            -1,
            30_000,
            60_000,
            100_000,
            150_000,
            200_000,
            float("inf"),
        ],
        labels=[
            "Até 30 mil km",
            "30–60 mil km",
            "60–100 mil km",
            "100–150 mil km",
            "150–200 mil km",
            "Acima de 200 mil km",
        ],
    ).astype("string")

    # Indicadores de ausência para campos potencialmente úteis.
    colunas_monitoradas = [
        "nome_combustivel",
        "potencia",
        "cilindrada",
        "tracao",
        "bairro",
        "atributos_veiculo",
        "descricao",
        "fipe_percent",
        "good_deal",
    ]

    for coluna in colunas_monitoradas:
        if coluna in df.columns:
            df[f"{coluna}_ausente"] = (
                df[coluna].isna().astype("int8")
            )

    print("Variáveis criadas:")
    print("- idade_veiculo")
    print("- preco_por_km")
    print("- faixa_preco")
    print("- faixa_quilometragem")
    print("- indicadores de dados ausentes")

    # 6. Auditar valores atípicos sem excluir registros
    print("\n[6] Auditoria de possíveis valores atípicos...")

    print(
        "Anúncios acima de R$ 500 mil:",
        int((df["valor_anuncio"] > 500_000).sum()),
    )

    print(
        "Anúncios acima de R$ 1 milhão:",
        int((df["valor_anuncio"] > 1_000_000).sum()),
    )

    print(
        "Veículos com mais de 200 mil km:",
        int((df["quilometragem"] > 200_000).sum()),
    )

    print(
        "Idade do veículo ausente:",
        int(df["idade_veiculo"].isna().sum()),
    )

    print(
        "Preço por km ausente:",
        int(df["preco_por_km"].isna().sum()),
    )

    print(
        "Observação: nenhum anúncio foi excluído por ser atípico."
    )

    # 7. Preparar diretório de saída
    print("\n[7] Preparando diretório de saída...")

    ARQUIVO_SAIDA.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 8. Salvar Tabela Ouro
    print("\n[8] Salvando Tabela Ouro...")

    df.to_parquet(
        ARQUIVO_SAIDA,
        index=False,
        engine="pyarrow",
    )

    # 9. Validar arquivo gerado
    print("\n[9] Validando arquivo gerado...")

    df_validacao = pd.read_parquet(ARQUIVO_SAIDA)

    if len(df_validacao) != quantidade_inicial:
        raise ValueError(
            "A quantidade de linhas mudou durante a preparação."
        )

    if df_validacao["webmotors_id"].isna().any():
        raise ValueError(
            "Foram encontrados IDs ausentes na saída."
        )

    if df_validacao["webmotors_id"].duplicated().any():
        raise ValueError(
            "Foram encontrados IDs duplicados na saída."
        )

    colunas_derivadas = [
        "idade_veiculo",
        "preco_por_km",
        "faixa_preco",
        "faixa_quilometragem",
    ]

    colunas_derivadas_ausentes = [
        coluna
        for coluna in colunas_derivadas
        if coluna not in df_validacao.columns
    ]

    if colunas_derivadas_ausentes:
        raise ValueError(
            "Colunas derivadas ausentes: "
            f"{colunas_derivadas_ausentes}"
        )

    print(f"Linhas finais: {len(df_validacao):,}")
    print(f"Colunas finais: {len(df_validacao.columns)}")
    print(f"Arquivo: {ARQUIVO_SAIDA}")
    print(
        f"Tamanho: "
        f"{ARQUIVO_SAIDA.stat().st_size / 1024:.2f} KB"
    )

    print("\nResumo dos dados numéricos:")
    print(
        df_validacao[
            [
                "valor_anuncio",
                "quilometragem",
                "ano_modelo",
                "idade_veiculo",
                "preco_por_km",
            ]
        ].describe().round(2)
    )

    print("\nDistribuição por faixa de preço:")
    print(
        df_validacao["faixa_preco"]
        .value_counts(dropna=False)
        .sort_index()
    )

    print("\nDistribuição por faixa de quilometragem:")
    print(
        df_validacao["faixa_quilometragem"]
        .value_counts(dropna=False)
        .sort_index()
    )

    print("\n" + "=" * 70)
    print("PREPARAÇÃO DA TABELA OURO CONCLUÍDA!")
    print("=" * 70)


if __name__ == "__main__":
    main()
