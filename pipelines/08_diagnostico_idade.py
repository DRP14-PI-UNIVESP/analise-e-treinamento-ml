import duckdb


# ============================================================
# CONFIGURAÇÕES
# ============================================================

CAMINHO_ENTRADA = "data/ouro/03_fipe_ouro.parquet"


print("=" * 70)
print("DIAGNÓSTICO DA CAMADA OURO")
print("=" * 70)


# ============================================================
# 1. CONECTANDO AO DUCKDB
# ============================================================

print("\n[1] Conectando ao DuckDB...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# 2. QUANTIDADE DE REGISTROS
# ============================================================

print("\n[2] Quantidade de registros...")

quantidade = con.execute(f"""
    SELECT COUNT(*)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()[0]

print(f"Registros: {quantidade:,}")


# ============================================================
# 3. ESTRUTURA DA OURO
# ============================================================

print("\n[3] Estrutura da Ouro...")

estrutura = con.execute(f"""
    DESCRIBE SELECT *
    FROM '{CAMINHO_ENTRADA}'
""").fetchall()

for coluna in estrutura:
    print(f" - {coluna[0]}: {coluna[1]}")


# ============================================================
# 4. VALORES NULOS
# ============================================================

print("\n[4] Valores nulos por coluna...")

nulos = con.execute(f"""
    SELECT
        COUNT(*) FILTER (WHERE codigo_fipe IS NULL),
        COUNT(*) FILTER (WHERE nome_modelo IS NULL),
        COUNT(*) FILTER (WHERE nome_marca IS NULL),
        COUNT(*) FILTER (WHERE nome_combustivel IS NULL),
        COUNT(*) FILTER (WHERE ano_modelo IS NULL),
        COUNT(*) FILTER (WHERE valor_centavos IS NULL),
        COUNT(*) FILTER (WHERE valor_fipe IS NULL),
        COUNT(*) FILTER (WHERE valor_formatado IS NULL),
        COUNT(*) FILTER (WHERE mes_referencia IS NULL),
        COUNT(*) FILTER (WHERE ano_referencia IS NULL),
        COUNT(*) FILTER (WHERE data_referencia IS NULL),
        COUNT(*) FILTER (WHERE idade_veiculo IS NULL),
        COUNT(*) FILTER (WHERE situacao_ano_modelo IS NULL)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

colunas = [
    "codigo_fipe",
    "nome_modelo",
    "nome_marca",
    "nome_combustivel",
    "ano_modelo",
    "valor_centavos",
    "valor_fipe",
    "valor_formatado",
    "mes_referencia",
    "ano_referencia",
    "data_referencia",
    "idade_veiculo",
    "situacao_ano_modelo"
]

for coluna, quantidade_nulos in zip(colunas, nulos):
    print(f" - {coluna}: {quantidade_nulos:,}")


# ============================================================
# 5. DUPLICIDADES EXATAS
# ============================================================

print("\n[5] Verificando duplicidades exatas...")

duplicidades = con.execute(f"""
    SELECT COUNT(*)
    FROM (
        SELECT
            *,
            COUNT(*) OVER (
                PARTITION BY
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
                    data_referencia,
                    idade_veiculo,
                    situacao_ano_modelo
            ) AS quantidade
        FROM '{CAMINHO_ENTRADA}'
    )
    WHERE quantidade > 1
""").fetchone()[0]

print(f"Registros envolvidos em duplicidades: {duplicidades:,}")


# ============================================================
# 6. MARCAS
# ============================================================

print("\n[6] Diagnóstico de marcas...")

marcas = con.execute(f"""
    SELECT
        COUNT(DISTINCT nome_marca),
        COUNT(*) FILTER (WHERE nome_marca = ''),
        MIN(nome_marca),
        MAX(nome_marca)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Marcas distintas: {marcas[0]:,}")
print(f"Marcas vazias: {marcas[1]:,}")
print(f"Primeira marca em ordem: {marcas[2]}")
print(f"Última marca em ordem: {marcas[3]}")


# ============================================================
# 7. MODELOS
# ============================================================

print("\n[7] Diagnóstico de modelos...")

modelos = con.execute(f"""
    SELECT
        COUNT(DISTINCT nome_modelo),
        COUNT(*) FILTER (WHERE nome_modelo = '')
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Modelos distintos: {modelos[0]:,}")
print(f"Modelos vazios: {modelos[1]:,}")


# ============================================================
# 8. COMBUSTÍVEIS
# ============================================================

print("\n[8] Distribuição de combustíveis...")

combustiveis = con.execute(f"""
    SELECT
        COALESCE(nome_combustivel, 'NULO') AS combustivel,
        COUNT(*) AS quantidade
    FROM '{CAMINHO_ENTRADA}'
    GROUP BY nome_combustivel
    ORDER BY quantidade DESC
""").fetchall()

for combustivel, quantidade in combustiveis:
    print(f" - {combustivel}: {quantidade:,}")


# ============================================================
# 9. ANOS DE REFERÊNCIA
# ============================================================

print("\n[9] Distribuição dos anos de referência...")

anos_referencia = con.execute(f"""
    SELECT
        ano_referencia,
        COUNT(*) AS quantidade
    FROM '{CAMINHO_ENTRADA}'
    GROUP BY ano_referencia
    ORDER BY ano_referencia
""").fetchall()

for ano, quantidade in anos_referencia:
    print(f" - {ano}: {quantidade:,}")


# ============================================================
# 10. ANOS-MODELO
# ============================================================

print("\n[10] Distribuição dos anos-modelo...")

anos_modelo = con.execute(f"""
    SELECT
        MIN(ano_modelo),
        MAX(ano_modelo),
        COUNT(DISTINCT ano_modelo),
        COUNT(*) FILTER (WHERE ano_modelo IS NULL)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Menor ano-modelo: {anos_modelo[0]}")
print(f"Maior ano-modelo: {anos_modelo[1]}")
print(f"Anos-modelo distintos: {anos_modelo[2]:,}")
print(f"Anos-modelo nulos: {anos_modelo[3]:,}")


# ============================================================
# 11. IDADE DO VEÍCULO
# ============================================================

print("\n[11] Distribuição da idade do veículo...")

idades = con.execute(f"""
    SELECT
        idade_veiculo,
        COUNT(*) AS quantidade
    FROM '{CAMINHO_ENTRADA}'
    WHERE idade_veiculo IS NOT NULL
    GROUP BY idade_veiculo
    ORDER BY idade_veiculo
""").fetchall()

for idade, quantidade in idades:
    print(f" - {idade} anos: {quantidade:,}")


# ============================================================
# 12. VALORES FIPE
# ============================================================

print("\n[12] Estatísticas dos valores FIPE...")

valores = con.execute(f"""
    SELECT
        MIN(valor_fipe),
        MAX(valor_fipe),
        AVG(valor_fipe),
        MEDIAN(valor_fipe),
        QUANTILE_CONT(valor_fipe, 0.25),
        QUANTILE_CONT(valor_fipe, 0.75)
    FROM '{CAMINHO_ENTRADA}'
    WHERE valor_fipe IS NOT NULL
""").fetchone()

print(f"Menor valor: R$ {valores[0]:,.2f}")
print(f"Maior valor: R$ {valores[1]:,.2f}")
print(f"Média: R$ {valores[2]:,.2f}")
print(f"Mediana: R$ {valores[3]:,.2f}")
print(f"1º quartil: R$ {valores[4]:,.2f}")
print(f"3º quartil: R$ {valores[5]:,.2f}")


# ============================================================
# 13. DISTRIBUIÇÃO DA SITUAÇÃO DO ANO-MODELO
# ============================================================

print("\n[13] Situação do ano-modelo...")

situacoes = con.execute(f"""
    SELECT
        situacao_ano_modelo,
        COUNT(*) AS quantidade
    FROM '{CAMINHO_ENTRADA}'
    GROUP BY situacao_ano_modelo
    ORDER BY quantidade DESC
""").fetchall()

for situacao, quantidade in situacoes:
    print(f" - {situacao}: {quantidade:,}")


# ============================================================
# 14. CÓDIGOS FIPE
# ============================================================

print("\n[14] Diagnóstico dos códigos FIPE...")

fipe = con.execute(f"""
    SELECT
        COUNT(DISTINCT codigo_fipe),
        COUNT(*) FILTER (WHERE codigo_fipe = ''),
        MIN(codigo_fipe),
        MAX(codigo_fipe)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Códigos FIPE distintos: {fipe[0]:,}")
print(f"Códigos FIPE vazios: {fipe[1]:,}")
print(f"Menor código em ordem: {fipe[2]}")
print(f"Maior código em ordem: {fipe[3]}")


# ============================================================
# 15. FINAL
# ============================================================

con.close()

print("\n" + "=" * 70)
print("DIAGNÓSTICO DA OURO FINALIZADO")
print("=" * 70)