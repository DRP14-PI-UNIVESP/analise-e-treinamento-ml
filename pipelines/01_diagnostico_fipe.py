import pandas as pd

CAMINHO_ARQUIVO = "data/bronze/fipex-prices-latest.csv"

df = pd.read_csv(
    CAMINHO_ARQUIVO,
    sep="\t"
)

print("Arquivo carregado com sucesso!")
print(f"Linhas: {len(df)}")
print(f"Colunas: {len(df.columns)}")

print("\nColunas:")
print(df.columns.tolist())

print("\nTipos das colunas:")
print(df.dtypes)

print("\nValores nulos:")
print(df.isna().sum())

print("\nRegistros sem ano_modelo:")

sem_ano = df["ano_modelo"].isna()

print(f"Quantidade: {sem_ano.sum()}")
print(f"Percentual: {sem_ano.mean() * 100:.2f}%")

print("\nExemplos de registros sem ano_modelo:")

print(
    df.loc[
        sem_ano,
        [
            "codigo_fipe",
            "nome_modelo",
            "nome_marca",
            "nome_combustivel",
            "valor_centavos",
            "valor_formatado",
            "mes_referencia",
            "ano_referencia"
        ]
    ].head(20)
)

sem_ano = df["ano_modelo"].isna()

print("\nCódigos FIPE com ano_modelo ausente:")

print(
    df.loc[sem_ano, "codigo_fipe"]
    .nunique()
)

print("\n10 códigos FIPE com mais registros sem ano_modelo:")

print(
    df.loc[sem_ano, "codigo_fipe"]
    .value_counts()
    .head(10)
)

print("\nAnálise dos registros sem ano_modelo:")

print(
    f"Códigos FIPE diferentes com ano_modelo ausente: "
    f"{df.loc[sem_ano, 'codigo_fipe'].nunique()}"
)

print("\n10 códigos FIPE com mais registros sem ano_modelo:")

print(
    df.loc[sem_ano, "codigo_fipe"]
    .value_counts()
    .head(10)
)

print("\nAnálise dos registros sem ano_modelo:")

print(
    f"Códigos FIPE diferentes com ano_modelo ausente: "
    f"{df.loc[sem_ano, 'codigo_fipe'].nunique()}"
)

print("\n10 códigos FIPE com mais registros sem ano_modelo:")

print(
    df.loc[sem_ano, "codigo_fipe"]
    .value_counts()
    .head(10)
)

print("\nQuantidade de anos de modelo por código FIPE:")

anos_por_codigo = (
    df.groupby("codigo_fipe")["ano_modelo"]
    .nunique(dropna=True)
)

print(anos_por_codigo.describe())

print("\nCódigos FIPE associados a mais de um ano_modelo:")

print(
    (anos_por_codigo > 1).sum()
)

print("\nTeste de duplicidade da chave temporal:")

chave = [
    "codigo_fipe",
    "ano_modelo",
    "mes_referencia",
    "ano_referencia"
]

duplicados = df.duplicated(subset=chave, keep=False)

print(f"Registros envolvidos em duplicidades: {duplicados.sum()}")

print(f"Quantidade de combinações duplicadas: {df.loc[duplicados, chave].drop_duplicates().shape[0]}")

print("\nExemplos de duplicidades:")

print(
    df.loc[
        duplicados,
        [
            "codigo_fipe",
            "nome_modelo",
            "nome_marca",
            "nome_combustivel",
            "ano_modelo",
            "valor_centavos",
            "valor_formatado",
            "mes_referencia",
            "ano_referencia"
        ]
    ]
    .sort_values(
        [
            "codigo_fipe",
            "ano_modelo",
            "ano_referencia",
            "mes_referencia"
        ]
    )
    .head(30)
)

print("\nInvestigação do código FIPE 001001-4:")

print(
    df[
        df["codigo_fipe"] == "001001-4"
    ][
        [
            "codigo_fipe",
            "nome_modelo",
            "nome_marca",
            "nome_combustivel",
            "ano_modelo",
            "valor_centavos",
            "valor_formatado",
            "mes_referencia",
            "ano_referencia"
        ]
    ].head(50).to_string(index=False)
)

print("\nQuantidade de registros do código 001001-4:")

print(
    df[df["codigo_fipe"] == "001001-4"]
    .shape[0]
)

print("\nCombinações duplicadas do código 001001-4:")

teste_001 = (
    df[df["codigo_fipe"] == "001001-4"]
    .groupby(
        [
            "codigo_fipe",
            "ano_modelo",
            "mes_referencia",
            "ano_referencia"
        ]
    )
    .size()
    .reset_index(name="quantidade")
)

print(
    teste_001[
        teste_001["quantidade"] > 1
    ].head(20).to_string(index=False)
)

print("\nComparação das duas observações duplicadas:")

exemplo = df[
    (df["codigo_fipe"] == "001001-4") &
    (df["ano_modelo"] == 1995) &
    (df["mes_referencia"] == 1) &
    (df["ano_referencia"] == 2001)
]

print(
    exemplo.to_string(index=False)
)

print("\nNovo teste de duplicidade:")

chave = [
    "codigo_fipe",
    "ano_modelo",
    "nome_combustivel",
    "mes_referencia",
    "ano_referencia"
]

duplicados = df.duplicated(subset=chave, keep=False)

print(f"Registros envolvidos em duplicidades: {duplicados.sum()}")

print(
    f"Quantidade de combinações duplicadas: "
    f"{df.loc[duplicados, chave].drop_duplicates().shape[0]}"
)

print("\nExemplos das duplicidades restantes:")

chave = [
    "codigo_fipe",
    "ano_modelo",
    "nome_combustivel",
    "mes_referencia",
    "ano_referencia"
]

duplicados = df.duplicated(
    subset=chave,
    keep=False
)

print(
    df.loc[
        duplicados,
        [
            "codigo_fipe",
            "nome_modelo",
            "nome_marca",
            "nome_combustivel",
            "ano_modelo",
            "valor_centavos",
            "valor_formatado",
            "mes_referencia",
            "ano_referencia"
        ]
    ]
    .sort_values(chave)
    .head(30)
    .to_string(index=False)
)

print("\nAnálise das duplicidades restantes:")

duplicados_df = df.loc[duplicados].copy()

print("\nQuantidade de combinações com mais de uma marca:")

print(
    duplicados_df
    .groupby(chave)["nome_marca"]
    .nunique()
    .value_counts()
    .sort_index()
)

print("\nQuantidade de combinações com mais de um modelo:")

print(
    duplicados_df
    .groupby(chave)["nome_modelo"]
    .nunique()
    .value_counts()
    .sort_index()
)

print("\nQuantidade de combinações com mais de um valor:")

print(
    duplicados_df
    .groupby(chave)["valor_centavos"]
    .nunique()
    .value_counts()
    .sort_index()
)

print("\nCombinações com mais de uma marca:")

marcas_diferentes = (
    duplicados_df
    .groupby(chave)["nome_marca"]
    .nunique()
)

grupos_multimarcas = marcas_diferentes[
    marcas_diferentes > 1
].index

print(
    duplicados_df[
        duplicados_df.set_index(chave).index.isin(grupos_multimarcas)
    ][
        [
            "codigo_fipe",
            "nome_modelo",
            "nome_marca",
            "nome_combustivel",
            "ano_modelo",
            "valor_centavos",
            "mes_referencia",
            "ano_referencia"
        ]
    ]
    .sort_values(chave)
    .head(50)
    .to_string(index=False)
)

print("\nQuantidade de marcas por código FIPE:")

marcas_por_codigo = (
    df.groupby("codigo_fipe")["nome_marca"]
    .nunique()
)

print(marcas_por_codigo.describe())

print("\nCódigos FIPE com mais de uma marca:")

print(
    marcas_por_codigo[marcas_por_codigo > 1]
    .sort_values(ascending=False)
    .head(20)
)

print("\nQuantidade de modelos por código FIPE:")

modelos_por_codigo = (
    df.groupby("codigo_fipe")["nome_modelo"]
    .nunique()
)

print(modelos_por_codigo.describe())

print("\nCódigos FIPE com mais de um modelo:")

print(
    modelos_por_codigo[modelos_por_codigo > 1]
    .sort_values(ascending=False)
    .head(20)
)

print("\nInvestigação do código FIPE 008251-1:")

print(
    df[df["codigo_fipe"] == "008251-1"][
        [
            "codigo_fipe",
            "nome_modelo",
            "nome_marca",
            "nome_combustivel",
            "ano_modelo",
            "valor_centavos",
            "mes_referencia",
            "ano_referencia"
        ]
    ]
    .drop_duplicates()
    .to_string(index=False)
)

print("\nInvestigação do código FIPE 008250-3:")

print(
    df[df["codigo_fipe"] == "008250-3"][
        [
            "codigo_fipe",
            "nome_modelo",
            "nome_marca",
            "nome_combustivel",
            "ano_modelo",
            "valor_centavos",
            "mes_referencia",
            "ano_referencia"
        ]
    ]
    .drop_duplicates()
    .to_string(index=False)
)

print("\n" + "=" * 60)
print("ANÁLISE DETALHADA DAS DUPLICIDADES")
print("=" * 60)

chave_temporal = [
    "codigo_fipe",
    "ano_modelo",
    "nome_combustivel",
    "mes_referencia",
    "ano_referencia"
]

duplicados = df.duplicated(
    subset=chave_temporal,
    keep=False
)

df_dup = df.loc[duplicados].copy()

print(f"\nRegistros envolvidos: {len(df_dup)}")
print(
    f"Combinações duplicadas: "
    f"{df_dup.groupby(chave_temporal, dropna=False).ngroups}"
)

print("\nQuantidade de valores diferentes dentro das duplicidades:")

analise = (
    df_dup
    .groupby(chave_temporal, dropna=False)
    .agg(
        qtd_modelos=("nome_modelo", "nunique"),
        qtd_marcas=("nome_marca", "nunique"),
        qtd_valores=("valor_centavos", "nunique"),
        qtd_registros=("codigo_fipe", "size")
    )
)

print(analise.value_counts().head(20))

print("\nExemplos de grupos com diferenças apenas no nome_modelo:")

somente_modelo = analise[
    (analise["qtd_modelos"] > 1) &
    (analise["qtd_marcas"] == 1) &
    (analise["qtd_valores"] == 1)
]

print(somente_modelo.head(10))

print("\n" + "=" * 60)
print("DUPLICIDADES EXATAS")
print("=" * 60)

duplicados_exatos = df.duplicated(
    keep=False
)

df_dup_exatos = df.loc[duplicados_exatos]

print(f"\nRegistros envolvidos: {len(df_dup_exatos)}")

print(
    f"Combinações de linhas duplicadas: "
    f"{df_dup_exatos.drop_duplicates().shape[0]}"
)

print("\nPrimeiros registros duplicados exatamente:")
print(
    df_dup_exatos
    .sort_values([
        "codigo_fipe",
        "ano_modelo",
        "nome_combustivel",
        "mes_referencia",
        "ano_referencia"
    ])
    .head(20)
)

print("\n" + "=" * 60)
print("VARIAÇÕES TEXTUAIS NAS DUPLICIDADES")
print("=" * 60)

grupos_textuais = (
    df_dup
    .groupby(chave_temporal, dropna=False)
    .filter(
        lambda grupo:
            grupo["nome_modelo"].nunique() > 1
            and grupo["nome_marca"].nunique() == 1
            and grupo["valor_centavos"].nunique() == 1
    )
)

print(f"\nRegistros encontrados: {len(grupos_textuais)}")

print(
    grupos_textuais[
        [
            "codigo_fipe",
            "nome_modelo",
            "nome_marca",
            "nome_combustivel",
            "ano_modelo",
            "valor_centavos",
            "mes_referencia",
            "ano_referencia"
        ]
    ].to_string(index=False)
)

print("\n" + "=" * 60)
print("IMPACTO DA REMOÇÃO DE DUPLICIDADES EXATAS")
print("=" * 60)

qtd_antes = len(df)

df_sem_duplicados = df.drop_duplicates()

qtd_depois = len(df_sem_duplicados)

print(f"\nRegistros antes: {qtd_antes}")
print(f"Registros depois: {qtd_depois}")
print(f"Registros removidos: {qtd_antes - qtd_depois}")
print(
    f"Percentual removido: "
    f"{((qtd_antes - qtd_depois) / qtd_antes) * 100:.4f}%"
)

print("\n" + "=" * 60)
print("VALIDAÇÃO DOS CAMPOS NUMÉRICOS")
print("=" * 60)

# ---------------------------------------------------------
# 1. ano_modelo
# ---------------------------------------------------------

print("\n[1] ano_modelo")

print("Valores mínimos e máximos:")
print(df["ano_modelo"].min(), df["ano_modelo"].max())

print("\nQuantidade de valores negativos:")
print((df["ano_modelo"] < 0).sum())

print("\nQuantidade de valores não inteiros:")
ano_com_valor = df["ano_modelo"].dropna()
print((ano_com_valor % 1 != 0).sum())


# ---------------------------------------------------------
# 2. valor_centavos
# ---------------------------------------------------------

print("\n[2] valor_centavos")

print("Valores mínimos e máximos:")
print(df["valor_centavos"].min(), df["valor_centavos"].max())

print("\nValores iguais a zero:")
print((df["valor_centavos"] == 0).sum())

print("\nValores negativos:")
print((df["valor_centavos"] < 0).sum())


# ---------------------------------------------------------
# 3. mes_referencia
# ---------------------------------------------------------

print("\n[3] mes_referencia")

print("Valores encontrados:")
print(sorted(df["mes_referencia"].unique()))

print("\nValores fora do intervalo 1-12:")
print(
    (
        (df["mes_referencia"] < 1) |
        (df["mes_referencia"] > 12)
    ).sum()
)


# ---------------------------------------------------------
# 4. ano_referencia
# ---------------------------------------------------------

print("\n[4] ano_referencia")

print("Valores mínimos e máximos:")
print(
    df["ano_referencia"].min(),
    df["ano_referencia"].max()
)

print("\nAnos de referência encontrados:")
print(
    sorted(df["ano_referencia"].unique())
)

print("\n" + "=" * 60)
print("VALIDAÇÃO TEMPORAL")
print("=" * 60)

print("\nAno de referência por mês:")

anos_invalidos = df.loc[
    ~df["mes_referencia"].between(1, 12)
]

print(
    f"Registros com mês de referência inválido: "
    f"{len(anos_invalidos)}"
)

print("\nQuantidade de registros por ano de referência:")
print(
    df["ano_referencia"]
    .value_counts()
    .sort_index()
)