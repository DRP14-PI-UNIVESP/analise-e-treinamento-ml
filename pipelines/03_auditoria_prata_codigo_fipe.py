import pandas as pd


CAMINHO_ENTRADA = "data/prata/02_fipe_limpo.parquet"


print("=" * 70)
print("AUDITORIA DE CONSISTÊNCIA - CÓDIGO FIPE × ANO DO MODELO")
print("=" * 70)


# ---------------------------------------------------------
# 1. CARREGAMENTO
# ---------------------------------------------------------

print("\n[1] Carregando Tabela Prata...")

df = pd.read_parquet(CAMINHO_ENTRADA)

print(f"Registros carregados: {len(df):,}".replace(",", "."))


# ---------------------------------------------------------
# 2. SELEÇÃO DOS CÓDIGOS COM ANO NULO
# ---------------------------------------------------------

print("\n[2] Identificando códigos FIPE afetados...")

codigos_afetados = (
    df.loc[df["ano_modelo"].isna(), "codigo_fipe"]
    .unique()
)

print(
    f"Códigos FIPE com ano_modelo nulo: "
    f"{len(codigos_afetados):,}".replace(",", ".")
)


# ---------------------------------------------------------
# 3. FILTRAGEM DOS CÓDIGOS AFETADOS
# ---------------------------------------------------------

df_afetados = df[
    df["codigo_fipe"].isin(codigos_afetados)
].copy()


# ---------------------------------------------------------
# 4. ANÁLISE POR CÓDIGO FIPE
# ---------------------------------------------------------

print("\n[3] Analisando relação código FIPE × ano_modelo...")

analise = (
    df_afetados
    .groupby("codigo_fipe")
    .agg(
        total_registros=("codigo_fipe", "size"),
        registros_com_ano=("ano_modelo", "count"),
        registros_sem_ano=("ano_modelo", lambda x: x.isna().sum()),
        quantidade_anos=("ano_modelo", "nunique"),
        anos=("ano_modelo", lambda x: sorted(x.dropna().unique().tolist()))
    )
    .reset_index()
)


# ---------------------------------------------------------
# 5. PERCENTUAL DE NULOS POR CÓDIGO
# ---------------------------------------------------------

analise["percentual_nulos"] = (
    analise["registros_sem_ano"]
    / analise["total_registros"]
    * 100
)


# ---------------------------------------------------------
# 6. CLASSIFICAÇÃO DOS CÓDIGOS
# ---------------------------------------------------------

def classificar_linha(linha):

    if linha["registros_com_ano"] == 0:
        return "SEM_ANO_EM_NENHUM_REGISTRO"

    if linha["quantidade_anos"] == 1:
        return "ANO_UNICO"

    return "MULTIPLOS_ANOS"


analise["classificacao"] = analise.apply(
    classificar_linha,
    axis=1
)


# ---------------------------------------------------------
# 7. RESUMO DAS CLASSIFICAÇÕES
# ---------------------------------------------------------

print("\n[4] Classificação dos códigos FIPE...")

resumo_classificacao = (
    analise["classificacao"]
    .value_counts()
)

print(resumo_classificacao.to_string())


# ---------------------------------------------------------
# 8. PERCENTUAIS DAS CLASSIFICAÇÕES
# ---------------------------------------------------------

print("\n[5] Percentual das classificações...")

percentuais = (
    analise["classificacao"]
    .value_counts(normalize=True)
    * 100
)

for classificacao, percentual in percentuais.items():

    print(
        f"{classificacao}: {percentual:.2f}%"
    )


# ---------------------------------------------------------
# 9. CÓDIGOS COM ANO ÚNICO
# ---------------------------------------------------------

print("\n[6] Códigos com apenas um ano conhecido...")

ano_unico = analise[
    analise["classificacao"] == "ANO_UNICO"
].copy()

print(
    f"Quantidade: {len(ano_unico):,}"
    .replace(",", ".")
)

print("\nExemplos:")

print(
    ano_unico[
        [
            "codigo_fipe",
            "total_registros",
            "registros_com_ano",
            "registros_sem_ano",
            "quantidade_anos",
            "anos",
            "percentual_nulos"
        ]
    ]
    .head(20)
    .to_string(index=False)
)


# ---------------------------------------------------------
# 10. CÓDIGOS COM MÚLTIPLOS ANOS
# ---------------------------------------------------------

print("\n[7] Códigos com múltiplos anos conhecidos...")

multiplos_anos = analise[
    analise["classificacao"] == "MULTIPLOS_ANOS"
].copy()

print(
    f"Quantidade: {len(multiplos_anos):,}"
    .replace(",", ".")
)

print("\nExemplos:")

print(
    multiplos_anos[
        [
            "codigo_fipe",
            "total_registros",
            "registros_com_ano",
            "registros_sem_ano",
            "quantidade_anos",
            "anos",
            "percentual_nulos"
        ]
    ]
    .head(20)
    .to_string(index=False)
)


# ---------------------------------------------------------
# 11. CÓDIGOS COM 100% DOS REGISTROS NULOS
# ---------------------------------------------------------

print("\n[8] Verificando códigos sem nenhum ano conhecido...")

sem_ano = analise[
    analise["classificacao"] == "SEM_ANO_EM_NENHUM_REGISTRO"
]

print(
    f"Códigos encontrados: {len(sem_ano):,}"
    .replace(",", ".")
)


# ---------------------------------------------------------
# 12. CASOS COM ALTO PERCENTUAL DE NULOS
# ---------------------------------------------------------

print("\n[9] Códigos com maior percentual de registros nulos...")

print(
    analise[
        [
            "codigo_fipe",
            "total_registros",
            "registros_com_ano",
            "registros_sem_ano",
            "quantidade_anos",
            "anos",
            "percentual_nulos",
            "classificacao"
        ]
    ]
    .sort_values(
        "percentual_nulos",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)


# ---------------------------------------------------------
# 13. DISTRIBUIÇÃO DA QUANTIDADE DE ANOS
# ---------------------------------------------------------

print("\n[10] Distribuição da quantidade de anos por código...")

distribuicao_anos = (
    analise["quantidade_anos"]
    .value_counts()
    .sort_index()
)

print(distribuicao_anos.to_string())


# ---------------------------------------------------------
# 14. VALIDAÇÃO DOS CASOS DE ANO ÚNICO
# ---------------------------------------------------------

print("\n[11] Verificando se os códigos de ano único possuem nulos...")

total_registros_ano_unico = ano_unico[
    "total_registros"
].sum()

total_nulos_ano_unico = ano_unico[
    "registros_sem_ano"
].sum()

print(
    f"Registros pertencentes a códigos de ano único: "
    f"{total_registros_ano_unico:,}"
    .replace(",", ".")
)

print(
    f"Destes, registros sem ano: "
    f"{total_nulos_ano_unico:,}"
    .replace(",", ".")
)


# ---------------------------------------------------------
# 15. EXEMPLOS DETALHADOS
# ---------------------------------------------------------

print("\n[12] Exemplos detalhados de códigos com ano único...")

exemplos = ano_unico.head(5)["codigo_fipe"].tolist()

for codigo in exemplos:

    print("\n" + "-" * 70)
    print(f"CÓDIGO FIPE: {codigo}")
    print("-" * 70)

    print(
        df[
            df["codigo_fipe"] == codigo
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
        .sort_values(
            ["ano_referencia", "mes_referencia"]
        )
        .to_string(index=False)
    )


# ---------------------------------------------------------
# 16. RESUMO FINAL
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("RESUMO DA AUDITORIA")
print("=" * 70)

print(
    f"Códigos FIPE afetados: "
    f"{len(analise):,}".replace(",", ".")
)

print(
    f"Códigos com ano único: "
    f"{len(ano_unico):,}".replace(",", ".")
)

print(
    f"Códigos com múltiplos anos: "
    f"{len(multiplos_anos):,}".replace(",", ".")
)

print(
    f"Códigos sem nenhum ano: "
    f"{len(sem_ano):,}".replace(",", ".")
)

print(
    f"Registros nulos dentro de códigos de ano único: "
    f"{total_nulos_ano_unico:,}".replace(",", ".")
)

print("\nAuditoria concluída.")