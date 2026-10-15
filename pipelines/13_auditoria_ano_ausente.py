from pathlib import Path
import duckdb


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ARQUIVO_OURO = BASE_DIR / "data" / "ouro" / "03_fipe_ouro.parquet"


# ============================================================
# CONEXÃO
# ============================================================

print("=" * 70)
print("AUDITORIA DE ANO_MODELO AUSENTE")
print("=" * 70)

print("\n[1] Conectando ao Parquet...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# TOTAL DE REGISTROS AUSENTES
# ============================================================

print("\n[2] Registros com ano_modelo ausente...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS registros_ausentes,
        COUNT(DISTINCT codigo_fipe) AS codigos_fipe,
        COUNT(DISTINCT nome_modelo) AS modelos,
        COUNT(DISTINCT nome_marca) AS marcas
    FROM read_parquet('{ARQUIVO_OURO}')
    WHERE ano_modelo IS NULL
""").fetchone()

print(f"Registros:     {resultado[0]:,}")
print(f"Códigos FIPE:  {resultado[1]:,}")
print(f"Modelos:       {resultado[2]:,}")
print(f"Marcas:        {resultado[3]:,}")


# ============================================================
# FIPE COM ANO CONHECIDO E AUSENTE
# ============================================================

print("\n[3] Códigos FIPE com anos conhecidos e ausentes...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) FILTER (
            WHERE total_ausentes > 0
              AND total_conhecidos > 0
        ) AS mistos,

        COUNT(*) FILTER (
            WHERE total_ausentes > 0
              AND total_conhecidos = 0
        ) AS somente_ausentes,

        COUNT(*) AS total_codigos
    FROM (
        SELECT
            codigo_fipe,

            COUNT(*) FILTER (
                WHERE ano_modelo IS NULL
            ) AS total_ausentes,

            COUNT(*) FILTER (
                WHERE ano_modelo IS NOT NULL
            ) AS total_conhecidos

        FROM read_parquet('{ARQUIVO_OURO}')
        GROUP BY codigo_fipe
    )
""").fetchone()

print(f"Total de códigos FIPE:              {resultado[2]:,}")
print(f"Códigos com conhecidos + ausentes:  {resultado[0]:,}")
print(f"Códigos somente com ano ausente:    {resultado[1]:,}")


# ============================================================
# DISTRIBUIÇÃO DOS ANOS CONHECIDOS
# ============================================================

print("\n[4] Distribuição dos anos conhecidos por código FIPE...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        MIN(ano_modelo) AS menor_ano,
        MAX(ano_modelo) AS maior_ano,
        COUNT(DISTINCT ano_modelo) AS quantidade_anos,
        COUNT(*) FILTER (
            WHERE ano_modelo IS NULL
        ) AS ausentes
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY codigo_fipe
    HAVING ausentes > 0
       AND COUNT(ano_modelo) > 0
    ORDER BY quantidade_anos DESC
    LIMIT 20
""").fetchall()

print("\nTop 20 códigos com maior variedade de anos conhecidos:")

for linha in resultado:
    print(
        f"FIPE {linha[0]} | "
        f"anos {linha[1]}-{linha[2]} | "
        f"{linha[3]} anos distintos | "
        f"{linha[4]:,} ausentes"
    )


# ============================================================
# CÓDIGOS COM APENAS UM ANO CONHECIDO
# ============================================================

print("\n[5] Códigos com apenas um ano conhecido...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS codigos,
        SUM(ausentes) AS registros_ausentes
    FROM (
        SELECT
            codigo_fipe,
            COUNT(DISTINCT ano_modelo) AS anos_conhecidos,
            COUNT(*) FILTER (
                WHERE ano_modelo IS NULL
            ) AS ausentes
        FROM read_parquet('{ARQUIVO_OURO}')
        GROUP BY codigo_fipe
        HAVING ausentes > 0
           AND anos_conhecidos = 1
    )
""").fetchone()

print(f"Códigos:             {resultado[0]:,}")
print(f"Registros ausentes:  {resultado[1]:,}")


# ============================================================
# CÓDIGOS COM MAIS DE UM ANO CONHECIDO
# ============================================================

print("\n[6] Códigos com múltiplos anos conhecidos...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS codigos,
        SUM(ausentes) AS registros_ausentes
    FROM (
        SELECT
            codigo_fipe,
            COUNT(DISTINCT ano_modelo) AS anos_conhecidos,
            COUNT(*) FILTER (
                WHERE ano_modelo IS NULL
            ) AS ausentes
        FROM read_parquet('{ARQUIVO_OURO}')
        GROUP BY codigo_fipe
        HAVING ausentes > 0
           AND anos_conhecidos > 1
    )
""").fetchone()

print(f"Códigos:             {resultado[0]:,}")
print(f"Registros ausentes:  {resultado[1]:,}")


# ============================================================
# DOMINÂNCIA DE UM ANO
# ============================================================

print("\n[7] Verificando ano dominante dentro de cada código FIPE...")

resultado = con.execute(f"""
    WITH anos AS (
        SELECT
            codigo_fipe,
            ano_modelo,
            COUNT(*) AS quantidade
        FROM read_parquet('{ARQUIVO_OURO}')
        WHERE ano_modelo IS NOT NULL
        GROUP BY
            codigo_fipe,
            ano_modelo
    ),

    ranking AS (
        SELECT
            codigo_fipe,
            ano_modelo,
            quantidade,
            ROW_NUMBER() OVER (
                PARTITION BY codigo_fipe
                ORDER BY quantidade DESC, ano_modelo
            ) AS posicao
        FROM anos
    ),

    totais AS (
        SELECT
            codigo_fipe,
            SUM(quantidade) AS total_conhecidos
        FROM anos
        GROUP BY codigo_fipe
    )

    SELECT
        COUNT(*) FILTER (
            WHERE r.quantidade = t.total_conhecidos
        ) AS ano_unico_dominante,

        COUNT(*) FILTER (
            WHERE r.quantidade * 1.0 / t.total_conhecidos >= 0.90
        ) AS dominante_90,

        COUNT(*) FILTER (
            WHERE r.quantidade * 1.0 / t.total_conhecidos >= 0.75
        ) AS dominante_75

    FROM ranking r
    JOIN totais t
      ON r.codigo_fipe = t.codigo_fipe

    WHERE r.posicao = 1
""").fetchone()

print(f"Ano único dominante:       {resultado[0]:,}")
print(f"Dominância >= 90%:         {resultado[1]:,}")
print(f"Dominância >= 75%:         {resultado[2]:,}")


# ============================================================
# EXEMPLOS DE CÓDIGOS COM ANO AUSENTE
# ============================================================

print("\n[8] Exemplos detalhados...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        nome_marca,
        nome_modelo,

        MIN(ano_modelo) AS menor_ano_conhecido,
        MAX(ano_modelo) AS maior_ano_conhecido,

        COUNT(DISTINCT ano_modelo) AS anos_conhecidos,

        COUNT(*) FILTER (
            WHERE ano_modelo IS NULL
        ) AS registros_ausentes,

        MIN(data_referencia) AS primeira_referencia,
        MAX(data_referencia) AS ultima_referencia

    FROM read_parquet('{ARQUIVO_OURO}')

    GROUP BY
        codigo_fipe,
        nome_marca,
        nome_modelo

    HAVING COUNT(*) FILTER (
        WHERE ano_modelo IS NULL
    ) > 0

    ORDER BY registros_ausentes DESC

    LIMIT 30
""").fetchall()

for linha in resultado:
    print(
        f"FIPE {linha[0]} | "
        f"{linha[1]} | "
        f"{linha[2]} | "
        f"anos: {linha[3]}-{linha[4]} | "
        f"distintos: {linha[5]} | "
        f"ausentes: {linha[6]:,} | "
        f"ref: {linha[7]} até {linha[8]}"
    )


# ============================================================
# AUSENTES POR ANO DE REFERÊNCIA
# ============================================================

print("\n[9] Registros sem ano_modelo por ano de referência...")

resultado = con.execute(f"""
    SELECT
        ano_referencia,
        COUNT(*) AS registros_ausentes
    FROM read_parquet('{ARQUIVO_OURO}')
    WHERE ano_modelo IS NULL
    GROUP BY ano_referencia
    ORDER BY ano_referencia
""").fetchall()

for ano, quantidade in resultado:
    print(f"{ano}: {quantidade:,}")


# ============================================================
# PREÇO DOS REGISTROS SEM ANO
# ============================================================

print("\n[10] Valores dos registros sem ano_modelo...")

resultado = con.execute(f"""
    SELECT
        MIN(valor_fipe),
        AVG(valor_fipe),
        MEDIAN(valor_fipe),
        MAX(valor_fipe)
    FROM read_parquet('{ARQUIVO_OURO}')
    WHERE ano_modelo IS NULL
""").fetchone()

print(f"Mínimo:  R$ {resultado[0]:,.2f}")
print(f"Média:   R$ {resultado[1]:,.2f}")
print(f"Mediana: R$ {resultado[2]:,.2f}")
print(f"Máximo:  R$ {resultado[3]:,.2f}")


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("AUDITORIA CONCLUÍDA")
print("=" * 70)

con.close()