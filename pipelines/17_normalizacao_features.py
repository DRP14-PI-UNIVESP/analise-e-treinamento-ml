from pathlib import Path
import duckdb


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ARQUIVO_ENTRADA = BASE_DIR / "data" / "ouro" / "04_fipe_ml.parquet"
ARQUIVO_SAIDA = BASE_DIR / "data" / "ouro" / "05_fipe_features.parquet"


# ============================================================
# CONEXÃO
# ============================================================

print("=" * 70)
print("NORMALIZAÇÃO E CRIAÇÃO DE FEATURES")
print("=" * 70)

print("\n[1] Conectando ao Parquet...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# CRIAÇÃO DA BASE DE FEATURES
# ============================================================

print("\n[2] Criando dataset de features...")

con.execute(f"""
COPY (
    SELECT
        codigo_fipe,

        -- Textos originais preservados
        nome_modelo,
        nome_marca,
        nome_combustivel,

        -- Textos normalizados
        UPPER(TRIM(nome_marca)) AS marca_normalizada,
        UPPER(TRIM(nome_modelo)) AS modelo_normalizado,
        UPPER(TRIM(nome_combustivel)) AS combustivel_normalizado,

        -- Variáveis originais
        ano_modelo,
        valor_centavos,
        valor_fipe,
        valor_formatado,
        mes_referencia,
        ano_referencia,
        data_referencia,
        idade_veiculo,
        situacao_ano_modelo

    FROM read_parquet('{ARQUIVO_ENTRADA}')
)
TO '{ARQUIVO_SAIDA}'
(FORMAT PARQUET, COMPRESSION ZSTD);
""")

print(f"Arquivo criado: {ARQUIVO_SAIDA}")


# ============================================================
# VALIDAÇÃO
# ============================================================

print("\n[3] Validando dataset...")

total = con.execute(f"""
    SELECT COUNT(*)
    FROM read_parquet('{ARQUIVO_SAIDA}')
""").fetchone()[0]

print(f"Registros: {total:,}".replace(",", "."))


print("\n[4] Verificando valores nulos...")

nulos = con.execute(f"""
    SELECT
        COUNT(*) FILTER (WHERE marca_normalizada IS NULL) AS marca_nula,
        COUNT(*) FILTER (WHERE modelo_normalizado IS NULL) AS modelo_nulo,
        COUNT(*) FILTER (WHERE combustivel_normalizado IS NULL) AS combustivel_nulo,
        COUNT(*) FILTER (WHERE valor_fipe IS NULL) AS valor_nulo
    FROM read_parquet('{ARQUIVO_SAIDA}')
""").fetchone()

print(f"Marca nula:        {nulos[0]:,}".replace(",", "."))
print(f"Modelo nulo:       {nulos[1]:,}".replace(",", "."))
print(f"Combustível nulo:  {nulos[2]:,}".replace(",", "."))
print(f"Valor FIPE nulo:   {nulos[3]:,}".replace(",", "."))


print("\n[5] Comparando cardinalidade das categorias...")

resultado = con.execute(f"""
    SELECT
        COUNT(DISTINCT nome_marca) AS marcas_originais,
        COUNT(DISTINCT marca_normalizada) AS marcas_normalizadas,

        COUNT(DISTINCT nome_modelo) AS modelos_originais,
        COUNT(DISTINCT modelo_normalizado) AS modelos_normalizados,

        COUNT(DISTINCT nome_combustivel) AS combustiveis_originais,
        COUNT(DISTINCT combustivel_normalizado) AS combustiveis_normalizados

    FROM read_parquet('{ARQUIVO_SAIDA}')
""").fetchone()

print(f"Marcas originais:       {resultado[0]}")
print(f"Marcas normalizadas:    {resultado[1]}")
print(f"Modelos originais:      {resultado[2]}")
print(f"Modelos normalizados:   {resultado[3]}")
print(f"Combustíveis originais: {resultado[4]}")
print(f"Combustíveis normalizados: {resultado[5]}")


print("\n[6] Exemplos de marcas normalizadas...")

exemplos = con.execute(f"""
    SELECT
        nome_marca,
        marca_normalizada,
        COUNT(*) AS registros
    FROM read_parquet('{ARQUIVO_SAIDA}')
    GROUP BY nome_marca, marca_normalizada
    ORDER BY marca_normalizada, registros DESC
    LIMIT 30
""").fetchall()

for linha in exemplos:
    print(
        f"{linha[0]} -> {linha[1]} "
        f"({linha[2]:,} registros)".replace(",", ".")
    )


print("\n[7] Verificando duplicidades exatas...")

duplicados = con.execute(f"""
    SELECT COUNT(*)
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY
                    codigo_fipe,
                    modelo_normalizado,
                    marca_normalizada,
                    combustivel_normalizado,
                    ano_modelo,
                    valor_fipe,
                    data_referencia
                ORDER BY codigo_fipe
            ) AS rn
        FROM read_parquet('{ARQUIVO_SAIDA}')
    )
    WHERE rn > 1
""").fetchone()[0]

print(f"Registros duplicados nas features: {duplicados:,}".replace(",", "."))


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("FEATURES CRIADAS E VALIDADAS")
print("=" * 70)

print(f"\nArquivo final:")
print(ARQUIVO_SAIDA)

con.close()