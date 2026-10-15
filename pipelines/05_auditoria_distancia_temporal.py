import pandas as pd

CAMINHO_ENTRADA = "data/prata/02_fipe_limpo.parquet"
CAMINHO_AUDITORIA = "data/prata/05_auditoria_distancia_temporal.csv"

print("=" * 70)
print("AUDITORIA DA DISTÂNCIA TEMPORAL DO ANO_MODELO")
print("=" * 70)

# ============================================================
# 1. CARREGAMENTO
# ============================================================

print("\n[1] Carregando camada Prata...")

df = pd.read_parquet(CAMINHO_ENTRADA)

print(f"Registros carregados: {len(df):,}")

# ============================================================
# 2. CRIAÇÃO DO PERÍODO
# ============================================================

print("\n[2] Criando período de referência...")

df["periodo"] = pd.to_datetime(
    df["ano_referencia"].astype(str)
    + "-"
    + df["mes_referencia"].astype(str)
    + "-01"
)

# ============================================================
# 3. ORDENAÇÃO
# ============================================================

print("\n[3] Ordenando por código FIPE e período...")

df = df.sort_values(
    ["codigo_fipe", "periodo"]
).reset_index(drop=True)

# ============================================================
# 4. LOCALIZANDO ANO ANTERIOR E POSTERIOR
# ============================================================

print("\n[4] Localizando anos conhecidos...")

grupo_ano = df.groupby("codigo_fipe")["ano_modelo"]

df["ano_anterior"] = grupo_ano.transform(
    lambda s: s.ffill().shift(1)
)

df["ano_posterior"] = grupo_ano.transform(
    lambda s: s.bfill().shift(-1)
)

# ============================================================
# 5. LOCALIZANDO PERÍODO ANTERIOR E POSTERIOR
# ============================================================

print("\n[5] Localizando períodos dos anos conhecidos...")

grupo_periodo = df.groupby("codigo_fipe")["periodo"]

df["periodo_anterior"] = grupo_periodo.transform(
    lambda s: s.where(df.loc[s.index, "ano_modelo"].notna()).ffill().shift(1)
)

df["periodo_posterior"] = grupo_periodo.transform(
    lambda s: s.where(df.loc[s.index, "ano_modelo"].notna()).bfill().shift(-1)
)

# ============================================================
# 6. SELECIONANDO NULOS
# ============================================================

nulos = df[df["ano_modelo"].isna()].copy()

print(f"\nRegistros com ano_modelo nulo: {len(nulos):,}")

# ============================================================
# 7. DISTÂNCIA EM MESES
# ============================================================

print("\n[6] Calculando distância temporal...")

nulos["distancia_anterior_meses"] = (
    (nulos["periodo"].dt.year - nulos["periodo_anterior"].dt.year) * 12
    + (nulos["periodo"].dt.month - nulos["periodo_anterior"].dt.month)
)

nulos["distancia_posterior_meses"] = (
    (nulos["periodo_posterior"].dt.year - nulos["periodo"].dt.year) * 12
    + (nulos["periodo_posterior"].dt.month - nulos["periodo"].dt.month)
)

# ============================================================
# 8. IDENTIFICAR CASOS COM ANOS IGUAIS
# ============================================================

casos_fortes = nulos[
    nulos["ano_anterior"].notna()
    & nulos["ano_posterior"].notna()
    & (nulos["ano_anterior"] == nulos["ano_posterior"])
].copy()

print(f"\nCasos com anterior e posterior iguais: {len(casos_fortes):,}")

# ============================================================
# 9. DISTÂNCIA DOS CASOS FORTES
# ============================================================

print("\n" + "=" * 70)
print("DISTÂNCIA TEMPORAL - CASOS COM ANOS IGUAIS")
print("=" * 70)

print("\nDistância até o ano conhecido anterior:")

print(
    casos_fortes["distancia_anterior_meses"]
    .value_counts()
    .sort_index()
    .head(30)
)

print("\nDistância até o ano conhecido posterior:")

print(
    casos_fortes["distancia_posterior_meses"]
    .value_counts()
    .sort_index()
    .head(30)
)

# ============================================================
# 10. FAIXAS DE DISTÂNCIA
# ============================================================

print("\n" + "=" * 70)
print("FAIXAS DE DISTÂNCIA")
print("=" * 70)

def classificar_distancia(valor):

    if pd.isna(valor):
        return "SEM CONTEXTO"

    if valor == 0:
        return "MESMO PERIODO"

    if valor == 1:
        return "1 MÊS"

    if valor <= 3:
        return "2-3 MESES"

    if valor <= 6:
        return "4-6 MESES"

    if valor <= 12:
        return "7-12 MESES"

    if valor <= 24:
        return "13-24 MESES"

    return "MAIS DE 24 MESES"


casos_fortes["faixa_anterior"] = (
    casos_fortes["distancia_anterior_meses"]
    .apply(classificar_distancia)
)

casos_fortes["faixa_posterior"] = (
    casos_fortes["distancia_posterior_meses"]
    .apply(classificar_distancia)
)

print("\nAnterior:")

print(
    casos_fortes["faixa_anterior"]
    .value_counts()
)

print("\nPosterior:")

print(
    casos_fortes["faixa_posterior"]
    .value_counts()
)

# ============================================================
# 11. DISTÂNCIA MÁXIMA ENTRE OS DOIS LADOS
# ============================================================

casos_fortes["maior_distancia_meses"] = casos_fortes[
    [
        "distancia_anterior_meses",
        "distancia_posterior_meses"
    ]
].max(axis=1)

print("\n" + "=" * 70)
print("MAIOR DISTÂNCIA ENTRE OS LADOS")
print("=" * 70)

print(
    casos_fortes["maior_distancia_meses"]
    .describe()
)

# ============================================================
# 12. CASOS COM EVIDÊNCIA MAIS PRÓXIMA
# ============================================================

print("\n" + "=" * 70)
print("EXEMPLOS COM EVIDÊNCIA MUITO PRÓXIMA")
print("=" * 70)

proximos = casos_fortes[
    (casos_fortes["distancia_anterior_meses"] <= 1)
    & (casos_fortes["distancia_posterior_meses"] <= 1)
]

print(f"\nQuantidade: {len(proximos):,}")

print(
    proximos[
        [
            "codigo_fipe",
            "periodo",
            "ano_anterior",
            "periodo_anterior",
            "ano_posterior",
            "periodo_posterior",
            "nome_modelo",
            "nome_marca"
        ]
    ]
    .head(20)
    .to_string(index=False)
)

# ============================================================
# 13. CASOS COM EVIDÊNCIA DISTANTE
# ============================================================

print("\n" + "=" * 70)
print("EXEMPLOS COM EVIDÊNCIA DISTANTE")
print("=" * 70)

distantes = casos_fortes[
    casos_fortes["maior_distancia_meses"] > 24
].copy()

print(f"\nQuantidade: {len(distantes):,}")

print(
    distantes[
        [
            "codigo_fipe",
            "periodo",
            "ano_anterior",
            "periodo_anterior",
            "ano_posterior",
            "periodo_posterior",
            "distancia_anterior_meses",
            "distancia_posterior_meses",
            "nome_modelo",
            "nome_marca"
        ]
    ]
    .head(20)
    .to_string(index=False)
)

# ============================================================
# 14. EXPORTAÇÃO
# ============================================================

print("\n[7] Salvando auditoria...")

nulos.to_csv(
    CAMINHO_AUDITORIA,
    index=False
)

print(f"Arquivo salvo em: {CAMINHO_AUDITORIA}")

print("\n" + "=" * 70)
print("AUDITORIA DE DISTÂNCIA TEMPORAL CONCLUÍDA")
print("=" * 70)