import pandas as pd


CAMINHO_ENTRADA = "data/bronze/fipex-prices-latest.csv"
CAMINHO_SAIDA = "data/prata/02_fipe_limpo.parquet"


print("=" * 60)
print("PREPARAÇÃO DA BASE FIPE - CAMADA PRATA")
print("=" * 60)


# ---------------------------------------------------------
# 1. CARREGAMENTO
# ---------------------------------------------------------

print("\n[1] Carregando base Bronze...")

df = pd.read_csv(
    CAMINHO_ENTRADA,
    sep="\t"
)

print(f"Registros carregados: {len(df)}")


# ---------------------------------------------------------
# 2. REMOÇÃO DE DUPLICIDADES EXATAS
# ---------------------------------------------------------

print("\n[2] Removendo duplicidades exatas...")

qtd_antes = len(df)

df = df.drop_duplicates()

qtd_depois = len(df)

print(f"Antes: {qtd_antes}")
print(f"Depois: {qtd_depois}")
print(f"Removidos: {qtd_antes - qtd_depois}")


# ---------------------------------------------------------
# 3. TRATAMENTO DOS TIPOS
# ---------------------------------------------------------

print("\n[3] Ajustando tipos de dados...")

df["ano_modelo"] = df["ano_modelo"].astype("Int64")

df["valor_centavos"] = df["valor_centavos"].astype("Int64")

df["mes_referencia"] = df["mes_referencia"].astype("Int64")

df["ano_referencia"] = df["ano_referencia"].astype("Int64")


# ---------------------------------------------------------
# 4. VALIDAÇÕES
# ---------------------------------------------------------

print("\n[4] Executando validações...")

assert df["mes_referencia"].between(1, 12).all()

assert (df["valor_centavos"] >= 0).all()

assert (df["ano_referencia"] >= 2001).all()

assert (df["ano_referencia"] <= 2025).all()

print("Validações concluídas com sucesso.")


# ---------------------------------------------------------
# 5. DIAGNÓSTICO FINAL
# ---------------------------------------------------------

print("\n[5] Diagnóstico da camada Prata...")

print(f"Registros finais: {len(df)}")

print("\nValores nulos:")
print(df.isna().sum())

print("\nTipos:")
print(df.dtypes)


# ---------------------------------------------------------
# 6. SALVAMENTO
# ---------------------------------------------------------

print("\n[6] Salvando arquivo Parquet...")

df.to_parquet(
    CAMINHO_SAIDA,
    index=False
)

print(f"Arquivo salvo em: {CAMINHO_SAIDA}")

print("\n" + "=" * 60)
print("CAMADA PRATA GERADA COM SUCESSO")
print("=" * 60)

import pandas as pd


CAMINHO_ENTRADA = "data/prata/02_fipe_limpo.parquet"


print("=" * 70)
print("AUDITORIA DOS VALORES AUSENTES - ANO DO MODELO")
print("=" * 70)


# ---------------------------------------------------------
# 1. CARREGAMENTO
# ---------------------------------------------------------

print("\n[1] Carregando Tabela Prata...")

df = pd.read_parquet(CAMINHO_ENTRADA)

print(f"Registros carregados: {len(df):,}".replace(",", "."))


# ---------------------------------------------------------
# 2. IDENTIFICAÇÃO DOS REGISTROS SEM ANO
# ---------------------------------------------------------

print("\n[2] Identificando registros sem ano_modelo...")

df_nulos = df[df["ano_modelo"].isna()].copy()

qtd_nulos = len(df_nulos)
qtd_total = len(df)

percentual = (qtd_nulos / qtd_total) * 100

print(f"Registros sem ano_modelo: {qtd_nulos:,}".replace(",", "."))
print(f"Percentual da base: {percentual:.2f}%")
print(
    f"Registros com ano_modelo: "
    f"{qtd_total - qtd_nulos:,}".replace(",", ".")
)


# ---------------------------------------------------------
# 3. QUANTIDADE DE CÓDIGOS FIPE AFETADOS
# ---------------------------------------------------------

print("\n[3] Códigos FIPE afetados...")

qtd_codigos = df_nulos["codigo_fipe"].nunique()

print(f"Códigos FIPE distintos: {qtd_codigos:,}".replace(",", "."))


print("\nTop 20 códigos FIPE com ano_modelo ausente:")

print(
    df_nulos["codigo_fipe"]
    .value_counts()
    .head(20)
    .to_string()
)


# ---------------------------------------------------------
# 4. MARCAS MAIS AFETADAS
# ---------------------------------------------------------

print("\n[4] Marcas mais afetadas...")

marcas = (
    df_nulos["nome_marca"]
    .value_counts()
    .head(20)
)

print(marcas.to_string())


# ---------------------------------------------------------
# 5. MODELOS MAIS AFETADOS
# ---------------------------------------------------------

print("\n[5] Modelos mais afetados...")

modelos = (
    df_nulos["nome_modelo"]
    .value_counts()
    .head(20)
)

print(modelos.to_string())


# ---------------------------------------------------------
# 6. COMBUSTÍVEIS
# ---------------------------------------------------------

print("\n[6] Distribuição por combustível...")

combustiveis = (
    df_nulos["nome_combustivel"]
    .value_counts()
)

print(combustiveis.to_string())


# ---------------------------------------------------------
# 7. ANO DE REFERÊNCIA
# ---------------------------------------------------------

print("\n[7] Distribuição por ano de referência...")

anos_referencia = (
    df_nulos["ano_referencia"]
    .value_counts()
    .sort_index()
)

print(anos_referencia.to_string())


# ---------------------------------------------------------
# 8. MÊS DE REFERÊNCIA
# ---------------------------------------------------------

print("\n[8] Distribuição por mês de referência...")

meses_referencia = (
    df_nulos["mes_referencia"]
    .value_counts()
    .sort_index()
)

print(meses_referencia.to_string())


# ---------------------------------------------------------
# 9. DISTRIBUIÇÃO POR ANO + MÊS
# ---------------------------------------------------------

print("\n[9] Distribuição temporal completa...")

distribuicao_temporal = (
    df_nulos
    .groupby(
        ["ano_referencia", "mes_referencia"]
    )
    .size()
    .reset_index(name="quantidade")
    .sort_values(
        ["ano_referencia", "mes_referencia"]
    )
)

print(distribuicao_temporal.to_string(index=False))


# ---------------------------------------------------------
# 10. VALORES MONETÁRIOS
# ---------------------------------------------------------

print("\n[10] Estatísticas dos valores dos registros sem ano...")

print(
    df_nulos["valor_centavos"]
    .describe()
    .to_string()
)


# ---------------------------------------------------------
# 11. VALORES IGUAIS A ZERO
# ---------------------------------------------------------

print("\n[11] Registros com valor igual a R$ 0,00...")

qtd_zero = (df_nulos["valor_centavos"] == 0).sum()

print(f"Quantidade: {qtd_zero:,}".replace(",", "."))

print(
    f"Percentual: {(qtd_zero / qtd_nulos) * 100:.2f}%"
)


# ---------------------------------------------------------
# 12. RELAÇÃO ENTRE CÓDIGO FIPE E ANO AUSENTE
# ---------------------------------------------------------

print("\n[12] Códigos FIPE exclusivamente sem ano_modelo...")

total_por_codigo = df["codigo_fipe"].value_counts()

nulos_por_codigo = df_nulos["codigo_fipe"].value_counts()

codigos_exclusivamente_nulos = (
    nulos_por_codigo[
        nulos_por_codigo == total_por_codigo.reindex(
            nulos_por_codigo.index
        )
    ]
)

print(
    f"Códigos que aparecem somente com ano_modelo nulo: "
    f"{len(codigos_exclusivamente_nulos):,}"
    .replace(",", ".")
)

print("\nTop 20:")

print(
    codigos_exclusivamente_nulos
    .sort_values(ascending=False)
    .head(20)
    .to_string()
)


# ---------------------------------------------------------
# 13. EXEMPLOS DE REGISTROS
# ---------------------------------------------------------

print("\n[13] Exemplos de registros...")

print(
    df_nulos[
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
    .head(20)
    .to_string(index=False)
)


# ---------------------------------------------------------
# 14. RESUMO FINAL
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("RESUMO DA AUDITORIA")
print("=" * 70)

print(f"Total da base:              {qtd_total:,}".replace(",", "."))
print(f"Sem ano_modelo:             {qtd_nulos:,}".replace(",", "."))
print(f"Percentual sem ano:         {percentual:.2f}%")
print(f"Códigos FIPE afetados:      {qtd_codigos:,}".replace(",", "."))
print(
    f"Códigos exclusivamente nulos: "
    f"{len(codigos_exclusivamente_nulos):,}"
    .replace(",", ".")
)
print(f"Registros com valor R$ 0:   {qtd_zero:,}".replace(",", "."))

print("\nAuditoria concluída.")