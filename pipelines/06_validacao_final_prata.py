import duckdb


CAMINHO_ENTRADA = "data/prata/02_fipe_limpo.parquet"


print("=" * 70)
print("VALIDAÇÃO FINAL DA CAMADA PRATA")
print("=" * 70)


# ============================================================
# 1. CONEXÃO
# ============================================================

print("\n[1] Conectando ao Parquet...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# 2. QUANTIDADE DE REGISTROS
# ============================================================

print("\n[2] Quantidade de registros...")

resultado = con.execute(f"""
    SELECT COUNT(*) AS quantidade
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

quantidade_registros = resultado[0]

print(f"Registros: {quantidade_registros:,}")


# ============================================================
# 3. ESTRUTURA DAS COLUNAS
# ============================================================

print("\n[3] Estrutura da tabela...")

estrutura = con.execute(f"""
    DESCRIBE SELECT *
    FROM '{CAMINHO_ENTRADA}'
""").fetchall()

print("\nColunas:")

for coluna in estrutura:
    nome = coluna[0]
    tipo = coluna[1]

    print(f" - {nome}: {tipo}")


# ============================================================
# 4. VALORES NULOS
# ============================================================

print("\n[4] Valores nulos...")

nulos = con.execute(f"""
    SELECT
        COUNT(*) AS total,

        COUNT(*) - COUNT(codigo_fipe) AS codigo_fipe_nulos,
        COUNT(*) - COUNT(nome_modelo) AS nome_modelo_nulos,
        COUNT(*) - COUNT(nome_marca) AS nome_marca_nulos,
        COUNT(*) - COUNT(nome_combustivel) AS nome_combustivel_nulos,
        COUNT(*) - COUNT(ano_modelo) AS ano_modelo_nulos,
        COUNT(*) - COUNT(valor_centavos) AS valor_centavos_nulos,
        COUNT(*) - COUNT(valor_formatado) AS valor_formatado_nulos,
        COUNT(*) - COUNT(mes_referencia) AS mes_referencia_nulos,
        COUNT(*) - COUNT(ano_referencia) AS ano_referencia_nulos

    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

colunas = [
    "total",
    "codigo_fipe_nulos",
    "nome_modelo_nulos",
    "nome_marca_nulos",
    "nome_combustivel_nulos",
    "ano_modelo_nulos",
    "valor_centavos_nulos",
    "valor_formatado_nulos",
    "mes_referencia_nulos",
    "ano_referencia_nulos"
]

for nome, valor in zip(colunas, nulos):
    print(f" - {nome}: {valor:,}")


# ============================================================
# 5. DUPLICIDADES EXATAS
# ============================================================

print("\n[5] Verificando duplicidades exatas...")

duplicidades = con.execute(f"""
    SELECT
        COUNT(*) - COUNT(DISTINCT (
            codigo_fipe,
            nome_modelo,
            nome_marca,
            nome_combustivel,
            ano_modelo,
            valor_centavos,
            valor_formatado,
            mes_referencia,
            ano_referencia
        )) AS duplicidades
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()[0]

print(f"Duplicidades exatas: {duplicidades:,}")


# ============================================================
# 6. ANO_MODELO
# ============================================================

print("\n[6] Validando ano_modelo...")

ano_modelo = con.execute(f"""
    SELECT
        MIN(ano_modelo),
        MAX(ano_modelo),
        COUNT(*) FILTER (WHERE ano_modelo < 1900),
        COUNT(*) FILTER (WHERE ano_modelo > 2030)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Menor ano_modelo: {ano_modelo[0]}")
print(f"Maior ano_modelo: {ano_modelo[1]}")
print(f"Anos menores que 1900: {ano_modelo[2]:,}")
print(f"Anos maiores que 2030: {ano_modelo[3]:,}")


# ============================================================
# 7. VALOR
# ============================================================

print("\n[7] Validando valor_centavos...")

valores = con.execute(f"""
    SELECT
        MIN(valor_centavos),
        MAX(valor_centavos),
        COUNT(*) FILTER (WHERE valor_centavos = 0),
        COUNT(*) FILTER (WHERE valor_centavos < 0)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Menor valor_centavos: {valores[0]:,}")
print(f"Maior valor_centavos: {valores[1]:,}")
print(f"Valores iguais a zero: {valores[2]:,}")
print(f"Valores negativos: {valores[3]:,}")


# ============================================================
# 8. MÊS DE REFERÊNCIA
# ============================================================

print("\n[8] Validando mes_referencia...")

meses = con.execute(f"""
    SELECT
        MIN(mes_referencia),
        MAX(mes_referencia),
        COUNT(*) FILTER (
            WHERE mes_referencia < 1
               OR mes_referencia > 12
        )
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Menor mês: {meses[0]}")
print(f"Maior mês: {meses[1]}")
print(f"Meses inválidos: {meses[2]:,}")


# ============================================================
# 9. ANO DE REFERÊNCIA
# ============================================================

print("\n[9] Validando ano_referencia...")

anos_referencia = con.execute(f"""
    SELECT
        MIN(ano_referencia),
        MAX(ano_referencia),
        COUNT(*) FILTER (WHERE ano_referencia < 2001),
        COUNT(*) FILTER (WHERE ano_referencia > 2025)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Menor ano_referencia: {anos_referencia[0]}")
print(f"Maior ano_referencia: {anos_referencia[1]}")
print(f"Anos anteriores a 2001: {anos_referencia[2]:,}")
print(f"Anos posteriores a 2025: {anos_referencia[3]:,}")


# ============================================================
# 10. CÓDIGOS FIPE
# ============================================================

print("\n[10] Validando codigo_fipe...")

codigos = con.execute(f"""
    SELECT
        COUNT(DISTINCT codigo_fipe),
        COUNT(*) FILTER (
            WHERE codigo_fipe IS NULL
               OR TRIM(codigo_fipe) = ''
        )
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Códigos FIPE distintos: {codigos[0]:,}")
print(f"Registros com codigo_fipe vazio/nulo: {codigos[1]:,}")


# ============================================================
# 11. MODELO / MARCA
# ============================================================

print("\n[11] Validando campos textuais...")

textuais = con.execute(f"""
    SELECT
        COUNT(*) FILTER (
            WHERE nome_modelo IS NULL
               OR TRIM(nome_modelo) = ''
        ),
        COUNT(*) FILTER (
            WHERE nome_marca IS NULL
               OR TRIM(nome_marca) = ''
        ),
        COUNT(*) FILTER (
            WHERE nome_combustivel IS NULL
               OR TRIM(nome_combustivel) = ''
        )
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Modelo vazio/nulo: {textuais[0]:,}")
print(f"Marca vazia/nula: {textuais[1]:,}")
print(f"Combustível vazio/nulo: {textuais[2]:,}")


# ============================================================
# 12. RESUMO FINAL
# ============================================================

print("\n" + "=" * 70)
print("RESUMO DA VALIDAÇÃO")
print("=" * 70)

problemas = 0

if quantidade_registros == 0:
    problemas += 1

if duplicidades > 0:
    problemas += 1

if ano_modelo[2] > 0 or ano_modelo[3] > 0:
    problemas += 1

if valores[3] > 0:
    problemas += 1

if meses[2] > 0:
    problemas += 1

if anos_referencia[2] > 0 or anos_referencia[3] > 0:
    problemas += 1

if codigos[1] > 0:
    problemas += 1

if textuais[0] > 0 or textuais[1] > 0 or textuais[2] > 0:
    problemas += 1


if problemas == 0:
    print("\nPRATA VALIDADA SEM INCONSISTENCIAS ESTRUTURAIS.")
else:
    print(f"\nForam identificados {problemas} pontos para análise.")


print("\n" + "=" * 70)
print("VALIDAÇÃO FINALIZADA")
print("=" * 70)


con.close()