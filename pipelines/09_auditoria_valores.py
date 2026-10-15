import duckdb


# ============================================================
# CONFIGURAÇÕES
# ============================================================

CAMINHO_ENTRADA = "data/ouro/03_fipe_ouro.parquet"


print("=" * 70)
print("AUDITORIA DOS VALORES DA CAMADA OURO")
print("=" * 70)


# ============================================================
# 1. CONECTANDO AO DUCKDB
# ============================================================

print("\n[1] Conectando ao DuckDB...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# 2. QUANTIDADE TOTAL DE REGISTROS
# ============================================================

print("\n[2] Quantidade total de registros...")

total = con.execute(f"""
    SELECT COUNT(*)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()[0]

print(f"Total: {total:,}")


# ============================================================
# 3. ESTATÍSTICAS GERAIS DOS VALORES
# ============================================================

print("\n[3] Estatísticas gerais dos valores...")

estatisticas = con.execute(f"""
    SELECT
        MIN(valor_fipe),
        MAX(valor_fipe),
        AVG(valor_fipe),
        MEDIAN(valor_fipe),
        QUANTILE_CONT(valor_fipe, 0.01),
        QUANTILE_CONT(valor_fipe, 0.05),
        QUANTILE_CONT(valor_fipe, 0.10),
        QUANTILE_CONT(valor_fipe, 0.25),
        QUANTILE_CONT(valor_fipe, 0.50),
        QUANTILE_CONT(valor_fipe, 0.75),
        QUANTILE_CONT(valor_fipe, 0.90),
        QUANTILE_CONT(valor_fipe, 0.95),
        QUANTILE_CONT(valor_fipe, 0.99)
    FROM '{CAMINHO_ENTRADA}'
""").fetchone()

print(f"Menor valor:       R$ {estatisticas[0]:,.2f}")
print(f"Maior valor:       R$ {estatisticas[1]:,.2f}")
print(f"Média:             R$ {estatisticas[2]:,.2f}")
print(f"Mediana:           R$ {estatisticas[3]:,.2f}")
print(f"Percentil 1%:      R$ {estatisticas[4]:,.2f}")
print(f"Percentil 5%:      R$ {estatisticas[5]:,.2f}")
print(f"Percentil 10%:     R$ {estatisticas[6]:,.2f}")
print(f"Percentil 25%:     R$ {estatisticas[7]:,.2f}")
print(f"Percentil 50%:     R$ {estatisticas[8]:,.2f}")
print(f"Percentil 75%:     R$ {estatisticas[9]:,.2f}")
print(f"Percentil 90%:     R$ {estatisticas[10]:,.2f}")
print(f"Percentil 95%:     R$ {estatisticas[11]:,.2f}")
print(f"Percentil 99%:     R$ {estatisticas[12]:,.2f}")


# ============================================================
# 4. FAIXAS DE VALOR
# ============================================================

print("\n[4] Distribuição por faixa de valor...")

faixas = con.execute(f"""
    SELECT
        CASE
            WHEN valor_fipe = 0
                THEN 'R$ 0'

            WHEN valor_fipe > 0
                 AND valor_fipe < 10000
                THEN 'R$ 1 - R$ 9.999'

            WHEN valor_fipe < 20000
                THEN 'R$ 10.000 - R$ 19.999'

            WHEN valor_fipe < 30000
                THEN 'R$ 20.000 - R$ 29.999'

            WHEN valor_fipe < 50000
                THEN 'R$ 30.000 - R$ 49.999'

            WHEN valor_fipe < 75000
                THEN 'R$ 50.000 - R$ 74.999'

            WHEN valor_fipe < 100000
                THEN 'R$ 75.000 - R$ 99.999'

            WHEN valor_fipe < 150000
                THEN 'R$ 100.000 - R$ 149.999'

            WHEN valor_fipe < 250000
                THEN 'R$ 150.000 - R$ 249.999'

            WHEN valor_fipe < 500000
                THEN 'R$ 250.000 - R$ 499.999'

            WHEN valor_fipe < 1000000
                THEN 'R$ 500.000 - R$ 999.999'

            ELSE 'R$ 1.000.000 ou mais'
        END AS faixa_valor,

        COUNT(*) AS quantidade

    FROM '{CAMINHO_ENTRADA}'

    GROUP BY faixa_valor

    ORDER BY
        MIN(valor_fipe)
""").fetchall()

for faixa, quantidade in faixas:
    percentual = (quantidade / total) * 100

    print(
        f" - {faixa}: "
        f"{quantidade:,} "
        f"({percentual:.2f}%)"
    )


# ============================================================
# 5. VALORES IGUAIS A ZERO
# ============================================================

print("\n[5] Valores iguais a zero...")

zeros = con.execute(f"""
    SELECT COUNT(*)
    FROM '{CAMINHO_ENTRADA}'
    WHERE valor_fipe = 0
""").fetchone()[0]

print(f"Quantidade: {zeros:,}")

print(f"Percentual: {(zeros / total) * 100:.6f}%")


# ============================================================
# 6. VALORES MUITO BAIXOS
# ============================================================

print("\n[6] Valores abaixo de R$ 1.000...")

baixos = con.execute(f"""
    SELECT COUNT(*)
    FROM '{CAMINHO_ENTRADA}'
    WHERE valor_fipe > 0
      AND valor_fipe < 1000
""").fetchone()[0]

print(f"Quantidade: {baixos:,}")
print(f"Percentual: {(baixos / total) * 100:.4f}%")


# ============================================================
# 7. VALORES MUITO ALTOS
# ============================================================

print("\n[7] Valores acima de R$ 1.000.000...")

altos = con.execute(f"""
    SELECT COUNT(*)
    FROM '{CAMINHO_ENTRADA}'
    WHERE valor_fipe > 1000000
""").fetchone()[0]

print(f"Quantidade: {altos:,}")
print(f"Percentual: {(altos / total) * 100:.4f}%")


# ============================================================
# 8. TOP 20 MAIORES VALORES
# ============================================================

print("\n[8] 20 maiores valores FIPE...")

maiores = con.execute(f"""
    SELECT
        codigo_fipe,
        nome_modelo,
        nome_marca,
        nome_combustivel,
        ano_modelo,
        valor_fipe,
        ano_referencia,
        mes_referencia
    FROM '{CAMINHO_ENTRADA}'
    ORDER BY valor_fipe DESC
    LIMIT 20
""").fetchall()

for registro in maiores:
    print(
        f" - R$ {registro[5]:,.2f} | "
        f"FIPE: {registro[0]} | "
        f"Marca: {registro[2]} | "
        f"Modelo: {registro[1]} | "
        f"Combustível: {registro[3]} | "
        f"Ano: {registro[4]} | "
        f"Referência: {registro[7]:02d}/{registro[6]}"
    )


# ============================================================
# 9. TOP 20 MENORES VALORES POSITIVOS
# ============================================================

print("\n[9] 20 menores valores FIPE positivos...")

menores = con.execute(f"""
    SELECT
        codigo_fipe,
        nome_modelo,
        nome_marca,
        nome_combustivel,
        ano_modelo,
        valor_fipe,
        ano_referencia,
        mes_referencia
    FROM '{CAMINHO_ENTRADA}'
    WHERE valor_fipe > 0
    ORDER BY valor_fipe ASC
    LIMIT 20
""").fetchall()

for registro in menores:
    print(
        f" - R$ {registro[5]:,.2f} | "
        f"FIPE: {registro[0]} | "
        f"Marca: {registro[2]} | "
        f"Modelo: {registro[1]} | "
        f"Combustível: {registro[3]} | "
        f"Ano: {registro[4]} | "
        f"Referência: {registro[7]:02d}/{registro[6]}"
    )


# ============================================================
# 10. VALORES EXTREMOS POR MARCA
# ============================================================

print("\n[10] Marcas com maiores valores máximos...")

marcas = con.execute(f"""
    SELECT
        nome_marca,
        MAX(valor_fipe) AS maior_valor,
        COUNT(*) AS quantidade
    FROM '{CAMINHO_ENTRADA}'
    GROUP BY nome_marca
    ORDER BY maior_valor DESC
    LIMIT 20
""").fetchall()

for marca, maior_valor, quantidade in marcas:
    print(
        f" - {marca}: "
        f"máximo R$ {maior_valor:,.2f} | "
        f"registros: {quantidade:,}"
    )


# ============================================================
# 11. DISTRIBUIÇÃO DOS VALORES POR COMBUSTÍVEL
# ============================================================

print("\n[11] Estatísticas por combustível...")

combustiveis = con.execute(f"""
    SELECT
        nome_combustivel,
        COUNT(*) AS quantidade,
        MIN(valor_fipe) AS minimo,
        MEDIAN(valor_fipe) AS mediana,
        AVG(valor_fipe) AS media,
        MAX(valor_fipe) AS maximo
    FROM '{CAMINHO_ENTRADA}'
    GROUP BY nome_combustivel
    ORDER BY quantidade DESC
""").fetchall()

for combustivel, quantidade, minimo, mediana, media, maximo in combustiveis:
    print(
        f" - {combustivel}: "
        f"{quantidade:,} registros | "
        f"mínimo R$ {minimo:,.2f} | "
        f"mediana R$ {mediana:,.2f} | "
        f"média R$ {media:,.2f} | "
        f"máximo R$ {maximo:,.2f}"
    )


# ============================================================
# 12. FINAL
# ============================================================

con.close()

print("\n" + "=" * 70)
print("AUDITORIA DOS VALORES FINALIZADA")
print("=" * 70)
