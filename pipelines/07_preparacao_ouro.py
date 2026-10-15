import duckdb
import os


# ============================================================
# CONFIGURAÇÕES
# ============================================================

CAMINHO_ENTRADA = "data/prata/02_fipe_limpo.parquet"
CAMINHO_SAIDA = "data/ouro/03_fipe_ouro.parquet"


print("=" * 70)
print("PREPARAÇÃO DA CAMADA OURO")
print("=" * 70)


# ============================================================
# 1. PREPARANDO DIRETÓRIO DE SAÍDA
# ============================================================

print("\n[1] Preparando diretório de saída...")

os.makedirs("data/ouro", exist_ok=True)

print("Diretório pronto.")


# ============================================================
# 2. CONECTANDO AO DUCKDB
# ============================================================

print("\n[2] Conectando ao DuckDB...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# 3. LENDO CAMADA PRATA
# ============================================================

print("\n[3] Lendo camada Prata...")

quantidade_entrada = con.execute(f"""
    SELECT COUNT(*)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()[0]

print(f"Registros encontrados: {quantidade_entrada:,}")


# ============================================================
# 4. CRIANDO TABELA OURO
# ============================================================

print("\n[4] Criando tabela Ouro...")

con.execute(f"""
    COPY (
        SELECT
            codigo_fipe,
            nome_modelo,
            nome_marca,
            nome_combustivel,
            ano_modelo,
            valor_centavos,

            valor_centavos / 100.0 AS valor_fipe,

            valor_formatado,
            mes_referencia,
            ano_referencia,

            MAKE_DATE(
                ano_referencia,
                mes_referencia,
                1
            ) AS data_referencia,

            CASE
                WHEN ano_modelo IS NOT NULL
                THEN ano_referencia - ano_modelo
                ELSE NULL
            END AS idade_veiculo,

            CASE
                WHEN ano_modelo IS NULL
                    THEN 'SEM_ANO_MODELO'

                WHEN ano_referencia - ano_modelo < 0
                    THEN 'ANO_MODELO_POSTERIOR'

                ELSE 'ANO_MODELO_COMPATIVEL'
            END AS situacao_ano_modelo

        FROM '{CAMINHO_ENTRADA}'
    )
    TO '{CAMINHO_SAIDA}'
    (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print("Tabela Ouro criada.")


# ============================================================
# 5. VALIDANDO QUANTIDADE DE REGISTROS
# ============================================================

print("\n[5] Validando quantidade de registros...")

quantidade_ouro = con.execute(f"""
    SELECT COUNT(*)
    FROM '{CAMINHO_SAIDA}'
""").fetchone()[0]

print(f"Registros na Ouro: {quantidade_ouro:,}")

if quantidade_ouro != quantidade_entrada:
    raise ValueError(
        "ERRO: quantidade de registros diferente entre Prata e Ouro."
    )


# ============================================================
# 6. VALIDANDO VALOR_FIPE
# ============================================================

print("\n[6] Validando valor_fipe...")

validacao_valor = con.execute(f"""
    SELECT
        MIN(valor_fipe),
        MAX(valor_fipe),
        COUNT(*) FILTER (
            WHERE valor_fipe IS NULL
        ),
        COUNT(*) FILTER (
            WHERE valor_fipe < 0
        )
    FROM '{CAMINHO_SAIDA}'
""").fetchone()

print(f"Menor valor_fipe: R$ {validacao_valor[0]:,.2f}")
print(f"Maior valor_fipe: R$ {validacao_valor[1]:,.2f}")
print(f"Valores nulos: {validacao_valor[2]:,}")
print(f"Valores negativos: {validacao_valor[3]:,}")

if validacao_valor[2] > 0:
    raise ValueError("ERRO: existem valores_fipe nulos.")

if validacao_valor[3] > 0:
    raise ValueError("ERRO: existem valores_fipe negativos.")


# ============================================================
# 7. VALIDANDO IDADE DO VEÍCULO
# ============================================================

print("\n[7] Validando idade_veiculo...")

validacao_idade = con.execute(f"""
    SELECT
        MIN(idade_veiculo),
        MAX(idade_veiculo),
        COUNT(*) FILTER (
            WHERE idade_veiculo IS NULL
        ),
        COUNT(*) FILTER (
            WHERE idade_veiculo < 0
        )
    FROM '{CAMINHO_SAIDA}'
""").fetchone()

print(f"Menor idade: {validacao_idade[0]}")
print(f"Maior idade: {validacao_idade[1]}")
print(f"Idades nulas: {validacao_idade[2]:,}")
print(f"Idades negativas: {validacao_idade[3]:,}")


# ============================================================
# 8. DISTRIBUIÇÃO DA SITUAÇÃO DO ANO-MODELO
# ============================================================

print("\n[8] Distribuição da situação do ano-modelo...")

distribuicao = con.execute(f"""
    SELECT
        situacao_ano_modelo,
        COUNT(*) AS quantidade
    FROM '{CAMINHO_SAIDA}'
    GROUP BY situacao_ano_modelo
    ORDER BY situacao_ano_modelo
""").fetchall()

for situacao, quantidade in distribuicao:
    print(f" - {situacao}: {quantidade:,}")


# ============================================================
# 9. VALIDANDO DATA DE REFERÊNCIA
# ============================================================

print("\n[9] Validando data_referencia...")

validacao_data = con.execute(f"""
    SELECT
        MIN(data_referencia),
        MAX(data_referencia),
        COUNT(*) FILTER (
            WHERE data_referencia IS NULL
        )
    FROM '{CAMINHO_SAIDA}'
""").fetchone()

print(f"Menor data: {validacao_data[0]}")
print(f"Maior data: {validacao_data[1]}")
print(f"Datas nulas: {validacao_data[2]:,}")

if validacao_data[2] > 0:
    raise ValueError(
        "ERRO: existem datas de referência nulas."
    )


# ============================================================
# 10. ESTRUTURA DA OURO
# ============================================================

print("\n[10] Estrutura da Ouro...")

estrutura = con.execute(f"""
    DESCRIBE SELECT *
    FROM '{CAMINHO_SAIDA}'
""").fetchall()

for coluna in estrutura:
    print(f" - {coluna[0]}: {coluna[1]}")


# ============================================================
# 11. VALIDANDO CONVERSÃO DO VALOR
# ============================================================

print("\n[11] Validando conversão de valor...")

conversao = con.execute(f"""
    SELECT
        COUNT(*) FILTER (
            WHERE valor_fipe != valor_centavos / 100.0
        ) AS divergencias,

        COUNT(*) FILTER (
            WHERE valor_centavos = 0
        ) AS valores_zero

    FROM '{CAMINHO_SAIDA}'
""").fetchone()

print(f"Divergências na conversão: {conversao[0]:,}")
print(f"Valores iguais a zero: {conversao[1]:,}")

if conversao[0] > 0:
    raise ValueError(
        "ERRO: existem divergências na conversão de valor."
    )


# ============================================================
# 12. AUDITORIA DOS VALORES FIPE IGUAIS A ZERO
# ============================================================

print("\n[12] Auditando valores FIPE iguais a zero...")

zeros = con.execute(f"""
    SELECT
        codigo_fipe,
        nome_modelo,
        nome_marca,
        nome_combustivel,
        ano_modelo,
        valor_centavos,
        valor_fipe,
        valor_formatado,
        mes_referencia,
        ano_referencia,
        data_referencia
    FROM '{CAMINHO_SAIDA}'
    WHERE valor_fipe = 0
    ORDER BY
        ano_referencia,
        mes_referencia,
        codigo_fipe
""").fetchall()

print(f"Registros encontrados: {len(zeros)}")

for registro in zeros:
    print(
        f" - FIPE: {registro[0]} | "
        f"Modelo: {registro[1]} | "
        f"Marca: {registro[2]} | "
        f"Combustível: {registro[3]} | "
        f"Ano modelo: {registro[4]} | "
        f"Valor: R$ {registro[6]:,.2f} | "
        f"Referência: {registro[9]}-{registro[8]:02d}"
    )


# ============================================================
# 13. ENCERRAMENTO
# ============================================================

con.close()

print("\n" + "=" * 70)
print("PREPARAÇÃO DA OURO FINALIZADA")
print("=" * 70)