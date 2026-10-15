import duckdb


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ARQUIVO_OURO = "data/ouro/03_fipe_ouro.parquet"


# ============================================================
# CONEXÃO
# ============================================================

print("=" * 70)
print("AUDITORIA DAS CATEGORIAS DA CAMADA OURO")
print("=" * 70)

print("\n[1] Conectando ao DuckDB...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# TOTAL
# ============================================================

print("\n[2] Quantidade total de registros...")

total = con.execute(f"""
    SELECT COUNT(*)
    FROM read_parquet('{ARQUIVO_OURO}')
""").fetchone()[0]

print(f"Total: {total:,}".replace(",", "."))


# ============================================================
# MARCAS
# ============================================================

print("\n[3] Marcas...")

resultado = con.execute(f"""
    SELECT
        COUNT(DISTINCT nome_marca) AS marcas_distintas,
        COUNT(*) FILTER (
            WHERE nome_marca IS NULL OR TRIM(nome_marca) = ''
        ) AS marcas_vazias
    FROM read_parquet('{ARQUIVO_OURO}')
""").fetchone()

print(f"Marcas distintas: {resultado[0]:,}".replace(",", "."))
print(f"Marcas vazias:    {resultado[1]:,}".replace(",", "."))


# ============================================================
# MARCAS NORMALIZADAS
# ============================================================

print("\n[4] Possíveis marcas duplicadas por capitalização...")

resultado = con.execute(f"""
    SELECT
        LOWER(TRIM(nome_marca)) AS marca_normalizada,
        COUNT(DISTINCT nome_marca) AS variacoes,
        STRING_AGG(
            DISTINCT nome_marca,
            ' | '
            ORDER BY nome_marca
        ) AS nomes_encontrados
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY LOWER(TRIM(nome_marca))
    HAVING COUNT(DISTINCT nome_marca) > 1
    ORDER BY variacoes DESC, marca_normalizada
""").fetchall()

if resultado:
    for linha in resultado:
        print(
            f" - {linha[0]} | "
            f"{linha[1]} variações | "
            f"{linha[2]}"
        )
else:
    print("Nenhuma duplicidade encontrada.")


# ============================================================
# TOP MARCAS
# ============================================================

print("\n[5] Marcas com maior quantidade de registros...")

resultado = con.execute(f"""
    SELECT
        nome_marca,
        COUNT(*) AS quantidade
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY nome_marca
    ORDER BY quantidade DESC
    LIMIT 30
""").fetchall()

for marca, quantidade in resultado:
    print(
        f" - {marca}: "
        f"{quantidade:,}".replace(",", ".")
    )


# ============================================================
# COMBUSTÍVEIS
# ============================================================

print("\n[6] Combustíveis...")

resultado = con.execute(f"""
    SELECT
        nome_combustivel,
        COUNT(*) AS quantidade
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY nome_combustivel
    ORDER BY quantidade DESC
""").fetchall()

for combustivel, quantidade in resultado:
    print(
        f" - {combustivel}: "
        f"{quantidade:,}".replace(",", ".")
    )


# ============================================================
# MODELOS
# ============================================================

print("\n[7] Modelos...")

resultado = con.execute(f"""
    SELECT
        COUNT(DISTINCT nome_modelo) AS modelos_distintos,
        COUNT(*) FILTER (
            WHERE nome_modelo IS NULL OR TRIM(nome_modelo) = ''
        ) AS modelos_vazios
    FROM read_parquet('{ARQUIVO_OURO}')
""").fetchone()

print(f"Modelos distintos: {resultado[0]:,}".replace(",", "."))
print(f"Modelos vazios:    {resultado[1]:,}".replace(",", "."))


# ============================================================
# MODELOS NORMALIZADOS
# ============================================================

print("\n[8] Possíveis modelos duplicados por capitalização...")

resultado = con.execute(f"""
    SELECT
        LOWER(TRIM(nome_modelo)) AS modelo_normalizado,
        COUNT(DISTINCT nome_modelo) AS variacoes,
        STRING_AGG(
            DISTINCT nome_modelo,
            ' | '
            ORDER BY nome_modelo
        ) AS nomes_encontrados
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY LOWER(TRIM(nome_modelo))
    HAVING COUNT(DISTINCT nome_modelo) > 1
    ORDER BY variacoes DESC, modelo_normalizado
    LIMIT 100
""").fetchall()

if resultado:
    for linha in resultado:
        print(
            f" - {linha[0]} | "
            f"{linha[1]} variações | "
            f"{linha[2]}"
        )
else:
    print("Nenhuma duplicidade encontrada.")


# ============================================================
# CÓDIGO FIPE x MARCA
# ============================================================

print("\n[9] Códigos FIPE associados a mais de uma marca...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        COUNT(DISTINCT nome_marca) AS marcas,
        STRING_AGG(
            DISTINCT nome_marca,
            ' | '
            ORDER BY nome_marca
        ) AS marcas_encontradas
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY codigo_fipe
    HAVING COUNT(DISTINCT nome_marca) > 1
    ORDER BY marcas DESC, codigo_fipe
    LIMIT 50
""").fetchall()

if resultado:
    for linha in resultado:
        print(
            f" - FIPE {linha[0]} | "
            f"{linha[1]} marcas | "
            f"{linha[2]}"
        )
else:
    print("Nenhum código com múltiplas marcas.")


# ============================================================
# CÓDIGO FIPE x MODELO
# ============================================================

print("\n[10] Códigos FIPE associados a mais de um modelo...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        COUNT(DISTINCT nome_modelo) AS modelos,
        STRING_AGG(
            DISTINCT nome_modelo,
            ' | '
            ORDER BY nome_modelo
        ) AS modelos_encontrados
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY codigo_fipe
    HAVING COUNT(DISTINCT nome_modelo) > 1
    ORDER BY modelos DESC, codigo_fipe
    LIMIT 50
""").fetchall()

if resultado:
    for linha in resultado:
        print(
            f" - FIPE {linha[0]} | "
            f"{linha[1]} modelos | "
            f"{linha[2]}"
        )
else:
    print("Nenhum código com múltiplos modelos.")


# ============================================================
# MARCA x MODELO
# ============================================================

print("\n[11] Combinações marca/modelo mais frequentes...")

resultado = con.execute(f"""
    SELECT
        nome_marca,
        nome_modelo,
        COUNT(*) AS quantidade
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY nome_marca, nome_modelo
    ORDER BY quantidade DESC
    LIMIT 30
""").fetchall()

for marca, modelo, quantidade in resultado:
    print(
        f" - {marca} | {modelo} | "
        f"{quantidade:,}".replace(",", ".")
    )


# ============================================================
# COMBUSTÍVEL x MARCA
# ============================================================

print("\n[12] Combinações combustível/marca...")

resultado = con.execute(f"""
    SELECT
        nome_combustivel,
        COUNT(DISTINCT nome_marca) AS marcas
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY nome_combustivel
    ORDER BY marcas DESC
""").fetchall()

for combustivel, marcas in resultado:
    print(
        f" - {combustivel}: "
        f"{marcas:,} marcas".replace(",", ".")
    )


# ============================================================
# COMBUSTÍVEL x MODELO
# ============================================================

print("\n[13] Modelos associados a múltiplos combustíveis...")

resultado = con.execute(f"""
    SELECT
        nome_modelo,
        COUNT(DISTINCT nome_combustivel) AS combustiveis,
        STRING_AGG(
            DISTINCT nome_combustivel,
            ' | '
            ORDER BY nome_combustivel
        ) AS combustiveis_encontrados
    FROM read_parquet('{ARQUIVO_OURO}')
    GROUP BY nome_modelo
    HAVING COUNT(DISTINCT nome_combustivel) > 1
    ORDER BY combustiveis DESC, nome_modelo
    LIMIT 50
""").fetchall()

if resultado:
    for linha in resultado:
        print(
            f" - {linha[0]} | "
            f"{linha[1]} combustíveis | "
            f"{linha[2]}"
        )
else:
    print("Nenhum modelo associado a múltiplos combustíveis.")


# ============================================================
# FINALIZAÇÃO
# ============================================================

con.close()

print("\n" + "=" * 70)
print("AUDITORIA DAS CATEGORIAS FINALIZADA")
print("=" * 70)