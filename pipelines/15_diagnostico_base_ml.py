# ============================================================
# 15_diagnostico_base_ml.py
# DIAGNÓSTICO DA BASE PREPARADA PARA MACHINE LEARNING
# ============================================================

from pathlib import Path
import duckdb


# ============================================================
# BLOCO 1 — CONFIGURAÇÃO E CONEXÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_ML = BASE_DIR / "data" / "ouro" / "04_fipe_ml.parquet"

print("=" * 70)
print("DIAGNÓSTICO DA BASE PARA MACHINE LEARNING")
print("=" * 70)

print("\n[1] Conectando à base ML...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# BLOCO 2 — TOTAL DE REGISTROS
# ============================================================

print("\n[2] Quantidade de registros...")

resultado = con.execute(f"""
    SELECT COUNT(*)
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

print(f"Registros: {resultado[0]:,}")


# ============================================================
# BLOCO 3 — ESTRUTURA
# ============================================================

print("\n[3] Estrutura da tabela...")

resultado = con.execute(f"""
    DESCRIBE SELECT *
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchall()

print("\nColunas:")

for coluna in resultado:
    print(f" - {coluna[0]}: {coluna[1]}")


# ============================================================
# BLOCO 4 — VALORES NULOS
# ============================================================

print("\n[4] Valores nulos...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) FILTER (WHERE codigo_fipe IS NULL),
        COUNT(*) FILTER (WHERE nome_modelo IS NULL),
        COUNT(*) FILTER (WHERE nome_marca IS NULL),
        COUNT(*) FILTER (WHERE nome_combustivel IS NULL),
        COUNT(*) FILTER (WHERE ano_modelo IS NULL),
        COUNT(*) FILTER (WHERE valor_centavos IS NULL),
        COUNT(*) FILTER (WHERE valor_fipe IS NULL),
        COUNT(*) FILTER (WHERE mes_referencia IS NULL),
        COUNT(*) FILTER (WHERE ano_referencia IS NULL),
        COUNT(*) FILTER (WHERE data_referencia IS NULL),
        COUNT(*) FILTER (WHERE idade_veiculo IS NULL),
        COUNT(*) FILTER (WHERE situacao_ano_modelo IS NULL)
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

colunas = [
    "codigo_fipe",
    "nome_modelo",
    "nome_marca",
    "nome_combustivel",
    "ano_modelo",
    "valor_centavos",
    "valor_fipe",
    "mes_referencia",
    "ano_referencia",
    "data_referencia",
    "idade_veiculo",
    "situacao_ano_modelo"
]

for coluna, quantidade in zip(colunas, resultado):
    print(f"{coluna}: {quantidade:,}")


# ============================================================
# BLOCO 5 — TARGET: VALOR FIPE
# ============================================================

print("\n[5] Diagnóstico do target: valor_fipe...")

resultado = con.execute(f"""
    SELECT
        MIN(valor_fipe),
        AVG(valor_fipe),
        MEDIAN(valor_fipe),
        MAX(valor_fipe),
        STDDEV_SAMP(valor_fipe),
        QUANTILE_CONT(valor_fipe, 0.01),
        QUANTILE_CONT(valor_fipe, 0.05),
        QUANTILE_CONT(valor_fipe, 0.10),
        QUANTILE_CONT(valor_fipe, 0.25),
        QUANTILE_CONT(valor_fipe, 0.50),
        QUANTILE_CONT(valor_fipe, 0.75),
        QUANTILE_CONT(valor_fipe, 0.90),
        QUANTILE_CONT(valor_fipe, 0.95),
        QUANTILE_CONT(valor_fipe, 0.99)
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

nomes = [
    "Mínimo",
    "Média",
    "Mediana",
    "Máximo",
    "Desvio padrão",
    "Percentil 1%",
    "Percentil 5%",
    "Percentil 10%",
    "Percentil 25%",
    "Percentil 50%",
    "Percentil 75%",
    "Percentil 90%",
    "Percentil 95%",
    "Percentil 99%"
]

for nome, valor in zip(nomes, resultado):
    print(f"{nome}: R$ {valor:,.2f}")


# ============================================================
# BLOCO 6 — FAIXAS DE PREÇO
# ============================================================

print("\n[6] Distribuição do valor_fipe por faixa...")

resultado = con.execute(f"""
    SELECT
        CASE
            WHEN valor_fipe < 10000
                THEN '01 - Até R$ 9.999'

            WHEN valor_fipe < 20000
                THEN '02 - R$ 10.000 a R$ 19.999'

            WHEN valor_fipe < 30000
                THEN '03 - R$ 20.000 a R$ 29.999'

            WHEN valor_fipe < 50000
                THEN '04 - R$ 30.000 a R$ 49.999'

            WHEN valor_fipe < 75000
                THEN '05 - R$ 50.000 a R$ 74.999'

            WHEN valor_fipe < 100000
                THEN '06 - R$ 75.000 a R$ 99.999'

            WHEN valor_fipe < 150000
                THEN '07 - R$ 100.000 a R$ 149.999'

            WHEN valor_fipe < 250000
                THEN '08 - R$ 150.000 a R$ 249.999'

            WHEN valor_fipe < 500000
                THEN '09 - R$ 250.000 a R$ 499.999'

            WHEN valor_fipe < 1000000
                THEN '10 - R$ 500.000 a R$ 999.999'

            ELSE '11 - R$ 1 milhão ou mais'
        END AS faixa,

        COUNT(*) AS quantidade

    FROM read_parquet('{ARQUIVO_ML}')

    GROUP BY faixa

    ORDER BY faixa
""").fetchall()

for faixa, quantidade in resultado:
    print(f"{faixa}: {quantidade:,}")


# ============================================================
# BLOCO 7 — ANO DO MODELO
# ============================================================

print("\n[7] Distribuição por ano_modelo...")

resultado = con.execute(f"""
    SELECT
        ano_modelo,
        COUNT(*) AS quantidade

    FROM read_parquet('{ARQUIVO_ML}')

    GROUP BY ano_modelo

    ORDER BY ano_modelo
""").fetchall()

for ano, quantidade in resultado:
    print(f"{ano}: {quantidade:,}")


# ============================================================
# BLOCO 8 — IDADE DO VEÍCULO
# ============================================================

print("\n[8] Distribuição da idade_veiculo...")

resultado = con.execute(f"""
    SELECT
        idade_veiculo,
        COUNT(*) AS quantidade

    FROM read_parquet('{ARQUIVO_ML}')

    GROUP BY idade_veiculo

    ORDER BY idade_veiculo
""").fetchall()

for idade, quantidade in resultado:
    print(f"{idade}: {quantidade:,}")


# ============================================================
# BLOCO 9 — MARCAS
# ============================================================

print("\n[9] Marcas...")

resultado = con.execute(f"""
    SELECT COUNT(DISTINCT nome_marca)
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

print(f"Marcas distintas: {resultado[0]:,}")

print("\nTop 30 marcas por quantidade de registros:")

resultado = con.execute(f"""
    SELECT
        nome_marca,
        COUNT(*) AS quantidade

    FROM read_parquet('{ARQUIVO_ML}')

    GROUP BY nome_marca

    ORDER BY quantidade DESC

    LIMIT 30
""").fetchall()

for marca, quantidade in resultado:
    print(f"{marca}: {quantidade:,}")


# ============================================================
# BLOCO 10 — MODELOS
# ============================================================

print("\n[10] Modelos...")

resultado = con.execute(f"""
    SELECT COUNT(DISTINCT nome_modelo)
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

print(f"Modelos distintos: {resultado[0]:,}")

print("\nTop 30 modelos por quantidade de registros:")

resultado = con.execute(f"""
    SELECT
        nome_modelo,
        COUNT(*) AS quantidade

    FROM read_parquet('{ARQUIVO_ML}')

    GROUP BY nome_modelo

    ORDER BY quantidade DESC

    LIMIT 30
""").fetchall()

for modelo, quantidade in resultado:
    print(f"{modelo}: {quantidade:,}")


# ============================================================
# BLOCO 11 — COMBUSTÍVEL
# ============================================================

print("\n[11] Combustíveis...")

resultado = con.execute(f"""
    SELECT
        nome_combustivel,
        COUNT(*) AS quantidade,
        MIN(valor_fipe) AS minimo,
        MEDIAN(valor_fipe) AS mediana,
        AVG(valor_fipe) AS media,
        MAX(valor_fipe) AS maximo

    FROM read_parquet('{ARQUIVO_ML}')

    GROUP BY nome_combustivel

    ORDER BY quantidade DESC
""").fetchall()

for linha in resultado:
    print(
        f"{linha[0]} | "
        f"registros: {linha[1]:,} | "
        f"mín: R$ {linha[2]:,.2f} | "
        f"mediana: R$ {linha[3]:,.2f} | "
        f"média: R$ {linha[4]:,.2f} | "
        f"máx: R$ {linha[5]:,.2f}"
    )


# ============================================================
# BLOCO 12 — REFERÊNCIA TEMPORAL
# ============================================================

print("\n[12] Distribuição por ano de referência...")

resultado = con.execute(f"""
    SELECT
        ano_referencia,
        COUNT(*) AS quantidade

    FROM read_parquet('{ARQUIVO_ML}')

    GROUP BY ano_referencia

    ORDER BY ano_referencia
""").fetchall()

for ano, quantidade in resultado:
    print(f"{ano}: {quantidade:,}")


# ============================================================
# BLOCO 13 — CÓDIGOS FIPE
# ============================================================

print("\n[13] Códigos FIPE...")

resultado = con.execute(f"""
    SELECT
        COUNT(DISTINCT codigo_fipe),
        MIN(codigo_fipe),
        MAX(codigo_fipe)

    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

print(f"Códigos distintos: {resultado[0]:,}")
print(f"Menor código:      {resultado[1]}")
print(f"Maior código:      {resultado[2]}")


# ============================================================
# BLOCO 14 — REGISTROS POR CÓDIGO FIPE
# ============================================================

print("\n[14] Quantidade de registros por código FIPE...")

resultado = con.execute(f"""
    SELECT
        MIN(quantidade),
        MAX(quantidade),
        AVG(quantidade),
        MEDIAN(quantidade)

    FROM (
        SELECT
            codigo_fipe,
            COUNT(*) AS quantidade

        FROM read_parquet('{ARQUIVO_ML}')

        GROUP BY codigo_fipe
    )
""").fetchone()

print(f"Mínimo:  {resultado[0]:,.0f}")
print(f"Máximo:  {resultado[1]:,.0f}")
print(f"Média:   {resultado[2]:,.2f}")
print(f"Mediana: {resultado[3]:,.2f}")


# ============================================================
# BLOCO 15 — 20 MAIORES VALORES
# ============================================================

print("\n[15] 20 maiores valores...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        nome_marca,
        nome_modelo,
        nome_combustivel,
        ano_modelo,
        ano_referencia,
        valor_fipe

    FROM read_parquet('{ARQUIVO_ML}')

    ORDER BY valor_fipe DESC

    LIMIT 20
""").fetchall()

for linha in resultado:
    print(
        f"{linha[0]} | "
        f"{linha[1]} | "
        f"{linha[2]} | "
        f"{linha[3]} | "
        f"ano modelo: {linha[4]} | "
        f"ref: {linha[5]} | "
        f"R$ {linha[6]:,.2f}"
    )


# ============================================================
# BLOCO 16 — 20 MENORES VALORES POSITIVOS
# ============================================================

print("\n[16] 20 menores valores positivos...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        nome_marca,
        nome_modelo,
        nome_combustivel,
        ano_modelo,
        ano_referencia,
        valor_fipe

    FROM read_parquet('{ARQUIVO_ML}')

    WHERE valor_fipe > 0

    ORDER BY valor_fipe ASC

    LIMIT 20
""").fetchall()

for linha in resultado:
    print(
        f"{linha[0]} | "
        f"{linha[1]} | "
        f"{linha[2]} | "
        f"{linha[3]} | "
        f"ano modelo: {linha[4]} | "
        f"ref: {linha[5]} | "
        f"R$ {linha[6]:,.2f}"
    )


# ============================================================
# BLOCO 17 — DUPLICIDADES LÓGICAS
# ============================================================

print("\n[17] Verificando possíveis duplicidades lógicas...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS grupos,
        COALESCE(SUM(quantidade), 0) AS registros

    FROM (
        SELECT
            codigo_fipe,
            ano_modelo,
            ano_referencia,
            mes_referencia,
            COUNT(*) AS quantidade

        FROM read_parquet('{ARQUIVO_ML}')

        GROUP BY
            codigo_fipe,
            ano_modelo,
            ano_referencia,
            mes_referencia

        HAVING COUNT(*) > 1
    )
""").fetchone()

print(f"Grupos duplicados:    {resultado[0]:,}")
print(f"Registros envolvidos: {resultado[1]:,}")


# ============================================================
# BLOCO 18 — CORRELAÇÃO IDADE × VALOR
# ============================================================

print("\n[18] Relação entre idade e valor...")

resultado = con.execute(f"""
    SELECT
        CORR(idade_veiculo, valor_fipe)

    FROM read_parquet('{ARQUIVO_ML}')

    WHERE idade_veiculo >= 0
""").fetchone()

print(f"Correlação idade × valor: {resultado[0]:.6f}")


# ============================================================
# FINALIZAÇÃO
# ============================================================

print("\n" + "=" * 70)
print("DIAGNÓSTICO DA BASE ML CONCLUÍDO")
print("=" * 70)

con.close()