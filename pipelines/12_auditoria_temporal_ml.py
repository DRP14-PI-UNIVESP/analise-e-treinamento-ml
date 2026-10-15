from pathlib import Path
import duckdb


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

ARQUIVO_OURO = BASE_DIR / "data" / "ouro" / "03_fipe_ouro.parquet"


# ============================================================
# CONEXÃO
# ============================================================

print("=" * 70)
print("AUDITORIA TEMPORAL PARA MACHINE LEARNING")
print("=" * 70)

con = duckdb.connect()

print("\n[1] Conectando ao Parquet...")

con.execute(f"""
    CREATE OR REPLACE VIEW ouro AS
    SELECT *
    FROM read_parquet('{ARQUIVO_OURO}')
""")

print("Conexão estabelecida.")


# ============================================================
# 2. REFERÊNCIAS POR CÓDIGO FIPE
# ============================================================

print("\n" + "=" * 70)
print("[2] QUANTIDADE DE REFERÊNCIAS POR CÓDIGO FIPE")
print("=" * 70)

resultado = con.execute("""
    SELECT
        MIN(qtd_referencias),
        MAX(qtd_referencias),
        AVG(qtd_referencias),
        MEDIAN(qtd_referencias)
    FROM (
        SELECT
            codigo_fipe,
            COUNT(DISTINCT data_referencia) AS qtd_referencias
        FROM ouro
        GROUP BY codigo_fipe
    )
""").fetchone()

print(f"Mínimo:  {resultado[0]}")
print(f"Máximo:  {resultado[1]}")
print(f"Média:   {resultado[2]:.2f}")
print(f"Mediana: {resultado[3]}")


# ============================================================
# 3. DISTRIBUIÇÃO DA QUANTIDADE DE REFERÊNCIAS
# ============================================================

print("\n" + "=" * 70)
print("[3] DISTRIBUIÇÃO DE REFERÊNCIAS")
print("=" * 70)

distribuicao = con.execute("""
    SELECT
        qtd_referencias,
        COUNT(*) AS quantidade_codigos
    FROM (
        SELECT
            codigo_fipe,
            COUNT(DISTINCT data_referencia) AS qtd_referencias
        FROM ouro
        GROUP BY codigo_fipe
    )
    GROUP BY qtd_referencias
    ORDER BY qtd_referencias
""").fetchall()

for qtd, quantidade in distribuicao:
    print(
        f"{qtd:5} referências -> "
        f"{quantidade:6,} códigos FIPE"
    )


# ============================================================
# 4. INTERVALO TEMPORAL POR CÓDIGO FIPE
# ============================================================

print("\n" + "=" * 70)
print("[4] INTERVALO TEMPORAL DOS CÓDIGOS FIPE")
print("=" * 70)

resultado = con.execute("""
    SELECT
        MIN(primeira_referencia),
        MAX(ultima_referencia),
        AVG(anos_historico),
        MEDIAN(anos_historico)
    FROM (
        SELECT
            codigo_fipe,
            MIN(data_referencia) AS primeira_referencia,
            MAX(data_referencia) AS ultima_referencia,
            DATE_DIFF(
                'year',
                MIN(data_referencia),
                MAX(data_referencia)
            ) AS anos_historico
        FROM ouro
        GROUP BY codigo_fipe
    )
""").fetchone()

print(f"Primeira referência: {resultado[0]}")
print(f"Última referência:   {resultado[1]}")
print(f"Média de anos:       {resultado[2]:.2f}")
print(f"Mediana de anos:     {resultado[3]}")


# ============================================================
# 5. DISTRIBUIÇÃO DO ANO DE REFERÊNCIA
# ============================================================

print("\n" + "=" * 70)
print("[5] REGISTROS POR ANO DE REFERÊNCIA")
print("=" * 70)

anos = con.execute("""
    SELECT
        ano_referencia,
        COUNT(*) AS quantidade
    FROM ouro
    GROUP BY ano_referencia
    ORDER BY ano_referencia
""").fetchall()

for ano, quantidade in anos:
    print(f"{ano}: {quantidade:,}")


# ============================================================
# 6. ANO DO MODELO POSTERIOR À REFERÊNCIA
# ============================================================

print("\n" + "=" * 70)
print("[6] ANO DO MODELO POSTERIOR À REFERÊNCIA")
print("=" * 70)

resultado = con.execute("""
    SELECT
        COUNT(*) AS quantidade,
        COUNT(DISTINCT codigo_fipe) AS codigos
    FROM ouro
    WHERE ano_modelo > ano_referencia
""").fetchone()

print(f"Registros:       {resultado[0]:,}")
print(f"Códigos FIPE:    {resultado[1]:,}")


# ============================================================
# 7. DIFERENÇA ENTRE ANO DO MODELO E REFERÊNCIA
# ============================================================

print("\n" + "=" * 70)
print("[7] DIFERENÇA ENTRE ANO DO MODELO E REFERÊNCIA")
print("=" * 70)

diferencas = con.execute("""
    SELECT
        ano_modelo - ano_referencia AS diferenca,
        COUNT(*) AS quantidade
    FROM ouro
    WHERE ano_modelo IS NOT NULL
    GROUP BY diferenca
    ORDER BY diferenca
""").fetchall()

for diferenca, quantidade in diferencas:
    print(
        f"Diferença {diferenca:3}: "
        f"{quantidade:,} registros"
    )


# ============================================================
# 8. CASOS POSTERIORES POR DIFERENÇA
# ============================================================

print("\n" + "=" * 70)
print("[8] CASOS COM ANO POSTERIOR")
print("=" * 70)

posteriores = con.execute("""
    SELECT
        ano_modelo - ano_referencia AS diferenca,
        COUNT(*) AS quantidade
    FROM ouro
    WHERE ano_modelo > ano_referencia
    GROUP BY diferenca
    ORDER BY diferenca
""").fetchall()

for diferenca, quantidade in posteriores:
    print(
        f"Modelo {diferenca} ano(s) à frente: "
        f"{quantidade:,}"
    )


# ============================================================
# 9. EXEMPLOS DOS CASOS POSTERIORES
# ============================================================

print("\n" + "=" * 70)
print("[9] EXEMPLOS DE ANO DO MODELO POSTERIOR")
print("=" * 70)

exemplos = con.execute("""
    SELECT
        codigo_fipe,
        nome_modelo,
        nome_marca,
        ano_modelo,
        ano_referencia,
        valor_fipe,
        idade_veiculo
    FROM ouro
    WHERE ano_modelo > ano_referencia
    ORDER BY
        (ano_modelo - ano_referencia) DESC,
        codigo_fipe,
        ano_referencia
    LIMIT 30
""").fetchall()

for linha in exemplos:
    print(
        f"FIPE={linha[0]} | "
        f"Marca={linha[2]} | "
        f"Modelo={linha[1]} | "
        f"Modelo={linha[3]} | "
        f"Ref={linha[4]} | "
        f"Valor=R${linha[5]:,.2f} | "
        f"Idade={linha[6]}"
    )


# ============================================================
# 10. VARIAÇÃO DE PREÇO POR CÓDIGO FIPE
# ============================================================

print("\n" + "=" * 70)
print("[10] VARIAÇÃO DE PREÇO POR CÓDIGO FIPE")
print("=" * 70)

variacao = con.execute("""
    SELECT
        MIN(valor_fipe),
        MAX(valor_fipe),
        AVG(valor_fipe),
        MEDIAN(valor_fipe)
    FROM ouro
    WHERE valor_fipe > 0
""").fetchone()

print(f"Menor preço:  R${variacao[0]:,.2f}")
print(f"Maior preço:  R${variacao[1]:,.2f}")
print(f"Média:        R${variacao[2]:,.2f}")
print(f"Mediana:      R${variacao[3]:,.2f}")


# ============================================================
# 11. CÓDIGOS COM MAIOR VARIAÇÃO ABSOLUTA
# ============================================================

print("\n" + "=" * 70)
print("[11] CÓDIGOS COM MAIOR VARIAÇÃO ABSOLUTA")
print("=" * 70)

maiores = con.execute("""
    SELECT
        codigo_fipe,
        ANY_VALUE(nome_marca),
        ANY_VALUE(nome_modelo),
        MIN(valor_fipe) AS minimo,
        MAX(valor_fipe) AS maximo,
        MAX(valor_fipe) - MIN(valor_fipe) AS variacao,
        COUNT(DISTINCT data_referencia) AS referencias
    FROM ouro
    WHERE valor_fipe > 0
    GROUP BY codigo_fipe
    ORDER BY variacao DESC
    LIMIT 20
""").fetchall()

for linha in maiores:
    print(
        f"FIPE={linha[0]} | "
        f"Marca={linha[1]} | "
        f"Modelo={linha[2]} | "
        f"Mín=R${linha[3]:,.2f} | "
        f"Máx=R${linha[4]:,.2f} | "
        f"Variação=R${linha[5]:,.2f} | "
        f"Refs={linha[6]}"
    )


# ============================================================
# 12. CÓDIGOS COM MENOR QUANTIDADE DE REFERÊNCIAS
# ============================================================

print("\n" + "=" * 70)
print("[12] CÓDIGOS COM MENOR HISTÓRICO")
print("=" * 70)

menores = con.execute("""
    SELECT
        codigo_fipe,
        ANY_VALUE(nome_marca),
        ANY_VALUE(nome_modelo),
        COUNT(DISTINCT data_referencia) AS referencias,
        MIN(data_referencia) AS primeira,
        MAX(data_referencia) AS ultima
    FROM ouro
    GROUP BY codigo_fipe
    ORDER BY referencias, codigo_fipe
    LIMIT 20
""").fetchall()

for linha in menores:
    print(
        f"FIPE={linha[0]} | "
        f"Marca={linha[1]} | "
        f"Modelo={linha[2]} | "
        f"Refs={linha[3]} | "
        f"Primeira={linha[4]} | "
        f"Última={linha[5]}"
    )


# ============================================================
# 13. REGISTROS SEM ANO DO MODELO
# ============================================================

print("\n" + "=" * 70)
print("[13] REGISTROS SEM ANO DO MODELO")
print("=" * 70)

resultado = con.execute("""
    SELECT
        COUNT(*) AS registros,
        COUNT(DISTINCT codigo_fipe) AS codigos,
        COUNT(DISTINCT nome_modelo) AS modelos,
        COUNT(DISTINCT nome_marca) AS marcas
    FROM ouro
    WHERE ano_modelo IS NULL
""").fetchone()

print(f"Registros:  {resultado[0]:,}")
print(f"Códigos:    {resultado[1]:,}")
print(f"Modelos:    {resultado[2]:,}")
print(f"Marcas:     {resultado[3]:,}")


# ============================================================
# 14. VALOR DOS REGISTROS SEM ANO
# ============================================================

print("\n" + "=" * 70)
print("[14] PREÇOS DOS REGISTROS SEM ANO")
print("=" * 70)

resultado = con.execute("""
    SELECT
        MIN(valor_fipe),
        MAX(valor_fipe),
        AVG(valor_fipe),
        MEDIAN(valor_fipe)
    FROM ouro
    WHERE ano_modelo IS NULL
      AND valor_fipe > 0
""").fetchone()

print(f"Mínimo:  R${resultado[0]:,.2f}")
print(f"Máximo:  R${resultado[1]:,.2f}")
print(f"Média:   R${resultado[2]:,.2f}")
print(f"Mediana: R${resultado[3]:,.2f}")


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("AUDITORIA TEMPORAL CONCLUÍDA")
print("=" * 70)

con.close()