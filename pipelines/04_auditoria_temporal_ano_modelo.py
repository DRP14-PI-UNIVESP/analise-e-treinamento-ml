import pandas as pd

CAMINHO_ENTRADA = "data/prata/02_fipe_limpo.parquet"

print("=" * 70)
print("AUDITORIA TEMPORAL DO ANO_MODELO")
print("=" * 70)

# ============================================================
# 1. CARREGAMENTO
# ============================================================

print("\n[1] Carregando camada Prata...")

df = pd.read_parquet(CAMINHO_ENTRADA)

print(f"Registros carregados: {len(df):,}")

# ============================================================
# 2. CRIAÇÃO DO PERÍODO DE REFERÊNCIA
# ============================================================

print("\n[2] Criando período de referência...")

df["periodo"] = pd.to_datetime(
    df["ano_referencia"].astype(str)
    + "-"
    + df["mes_referencia"].astype(str)
    + "-01"
)

# ============================================================
# 3. ORDENAÇÃO TEMPORAL
# ============================================================

print("\n[3] Ordenando registros por código FIPE e período...")

df = df.sort_values(
    ["codigo_fipe", "periodo"]
).reset_index(drop=True)

# ============================================================
# 4. IDENTIFICANDO ANO ANTERIOR E POSTERIOR
# ============================================================

print("\n[4] Identificando anos conhecidos ao redor dos valores nulos...")

grupo = df.groupby("codigo_fipe")["ano_modelo"]

# Último ano conhecido antes do registro atual
df["ano_anterior"] = grupo.transform(
    lambda s: s.ffill().shift(1)
)

# Primeiro ano conhecido depois do registro atual
df["ano_posterior"] = grupo.transform(
    lambda s: s.bfill().shift(-1)
)

# ============================================================
# 5. SELECIONANDO APENAS OS NULOS
# ============================================================

nulos = df[df["ano_modelo"].isna()].copy()

print(f"\nRegistros com ano_modelo nulo: {len(nulos):,}")

# ============================================================
# 6. CLASSIFICAÇÃO DOS CASOS
# ============================================================

print("\n[5] Classificando os casos...")

nulos["classificacao_temporal"] = "SEM CONTEXTO"

# Possui ano anterior e posterior iguais
condicao_mesmo_ano = (
    nulos["ano_anterior"].notna()
    & nulos["ano_posterior"].notna()
    & (nulos["ano_anterior"] == nulos["ano_posterior"])
)

nulos.loc[
    condicao_mesmo_ano,
    "classificacao_temporal"
] = "ANTERIOR_E_POSTERIOR_IGUAIS"

# Possui anterior e posterior, mas diferentes
condicao_anos_diferentes = (
    nulos["ano_anterior"].notna()
    & nulos["ano_posterior"].notna()
    & (nulos["ano_anterior"] != nulos["ano_posterior"])
)

nulos.loc[
    condicao_anos_diferentes,
    "classificacao_temporal"
] = "ANTERIOR_E_POSTERIOR_DIFERENTES"

# Somente anterior
condicao_somente_anterior = (
    nulos["ano_anterior"].notna()
    & nulos["ano_posterior"].isna()
)

nulos.loc[
    condicao_somente_anterior,
    "classificacao_temporal"
] = "SOMENTE_ANTERIOR"

# Somente posterior
condicao_somente_posterior = (
    nulos["ano_anterior"].isna()
    & nulos["ano_posterior"].notna()
)

nulos.loc[
    condicao_somente_posterior,
    "classificacao_temporal"
] = "SOMENTE_POSTERIOR"

# Nenhum contexto
condicao_sem_contexto = (
    nulos["ano_anterior"].isna()
    & nulos["ano_posterior"].isna()
)

nulos.loc[
    condicao_sem_contexto,
    "classificacao_temporal"
] = "SEM_ANO_CONHECIDO_AO_REDOR"

# ============================================================
# 7. RESUMO
# ============================================================

print("\n" + "=" * 70)
print("RESULTADO DA AUDITORIA TEMPORAL")
print("=" * 70)

resumo = (
    nulos["classificacao_temporal"]
    .value_counts()
    .to_frame("quantidade")
)

resumo["percentual"] = (
    resumo["quantidade"]
    / len(nulos)
    * 100
)

print("\n", resumo)

# ============================================================
# 8. CASOS MAIS INTERESSANTES
# ============================================================

print("\n" + "=" * 70)
print("CASOS COM ANO ANTERIOR E POSTERIOR IGUAIS")
print("=" * 70)

casos_fortes = nulos[
    nulos["classificacao_temporal"]
    == "ANTERIOR_E_POSTERIOR_IGUAIS"
]

print(f"\nQuantidade: {len(casos_fortes):,}")

if len(casos_fortes) > 0:

    print(
        casos_fortes[
            [
                "codigo_fipe",
                "periodo",
                "ano_anterior",
                "ano_modelo",
                "ano_posterior",
                "nome_modelo",
                "nome_marca"
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

# ============================================================
# 9. CASOS COM ANOS DIFERENTES
# ============================================================

print("\n" + "=" * 70)
print("CASOS COM ANO ANTERIOR E POSTERIOR DIFERENTES")
print("=" * 70)

casos_diferentes = nulos[
    nulos["classificacao_temporal"]
    == "ANTERIOR_E_POSTERIOR_DIFERENTES"
]

print(f"\nQuantidade: {len(casos_diferentes):,}")

if len(casos_diferentes) > 0:

    print(
        casos_diferentes[
            [
                "codigo_fipe",
                "periodo",
                "ano_anterior",
                "ano_modelo",
                "ano_posterior",
                "nome_modelo",
                "nome_marca"
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

# ============================================================
# 10. DISTRIBUIÇÃO POR CÓDIGO FIPE
# ============================================================

print("\n" + "=" * 70)
print("CÓDIGOS FIPE COM MAIOR QUANTIDADE DE NULOS")
print("=" * 70)

top_codigos = (
    nulos["codigo_fipe"]
    .value_counts()
    .head(20)
)

print(top_codigos)

# ============================================================
# 11. EXPORTAÇÃO DA AUDITORIA
# ============================================================

CAMINHO_AUDITORIA = "data/prata/04_auditoria_temporal_ano_modelo.csv"

nulos.to_csv(
    CAMINHO_AUDITORIA,
    index=False
)

print("\nArquivo de auditoria salvo em:")
print(CAMINHO_AUDITORIA)

print("\n" + "=" * 70)
print("AUDITORIA TEMPORAL CONCLUÍDA")
print("=" * 70)