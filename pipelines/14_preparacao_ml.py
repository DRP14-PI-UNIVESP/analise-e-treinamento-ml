from pathlib import Path
import duckdb


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ARQUIVO_OURO = BASE_DIR / "data" / "ouro" / "03_fipe_ouro.parquet"
ARQUIVO_ML = BASE_DIR / "data" / "ouro" / "04_fipe_ml.parquet"


# ============================================================
# INÍCIO
# ============================================================

print("=" * 70)
print("PREPARAÇÃO DA BASE PARA MACHINE LEARNING")
print("=" * 70)

print("\n[1] Conectando ao Ouro...")

con = duckdb.connect()

print("Conexão estabelecida.")


# ============================================================
# DIAGNÓSTICO ANTES DO FILTRO
# ============================================================

print("\n[2] Registros disponíveis no Ouro...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (
            WHERE valor_fipe > 0
        ) AS valor_positivo,
        COUNT(*) FILTER (
            WHERE ano_modelo IS NOT NULL
        ) AS ano_conhecido,
        COUNT(*) FILTER (
            WHERE valor_fipe > 0
              AND ano_modelo IS NOT NULL
        ) AS candidatos_ml
    FROM read_parquet('{ARQUIVO_OURO}')
""").fetchone()

print(f"Total no Ouro:                    {resultado[0]:,}")
print(f"Valor FIPE positivo:              {resultado[1]:,}")
print(f"Ano modelo conhecido:             {resultado[2]:,}")
print(f"Candidatos iniciais para ML:      {resultado[3]:,}")


# ============================================================
# CRIAÇÃO DA BASE ML
# ============================================================

print("\n[3] Criando base específica para ML...")

con.execute(f"""
    COPY (
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
            data_referencia,
            idade_veiculo,
            situacao_ano_modelo

        FROM read_parquet('{ARQUIVO_OURO}')

        WHERE valor_fipe > 0
          AND ano_modelo IS NOT NULL

    )
    TO '{ARQUIVO_ML}'
    (FORMAT PARQUET)
""")

print(f"Arquivo criado:")
print(ARQUIVO_ML)


# ============================================================
# VALIDAÇÃO
# ============================================================

print("\n[4] Validando a base ML...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS total,

        COUNT(*) FILTER (
            WHERE valor_fipe <= 0
        ) AS valores_invalidos,

        COUNT(*) FILTER (
            WHERE ano_modelo IS NULL
        ) AS anos_ausentes,

        COUNT(*) FILTER (
            WHERE nome_marca IS NULL
               OR nome_modelo IS NULL
               OR nome_combustivel IS NULL
        ) AS categorias_nulas,

        COUNT(DISTINCT codigo_fipe) AS codigos_fipe,

        COUNT(DISTINCT nome_marca) AS marcas,

        COUNT(DISTINCT nome_modelo) AS modelos,

        COUNT(DISTINCT nome_combustivel) AS combustiveis

    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

print(f"Registros:              {resultado[0]:,}")
print(f"Valores <= 0:           {resultado[1]:,}")
print(f"Ano modelo ausente:     {resultado[2]:,}")
print(f"Categorias nulas:       {resultado[3]:,}")
print(f"Códigos FIPE:           {resultado[4]:,}")
print(f"Marcas:                 {resultado[5]:,}")
print(f"Modelos:                {resultado[6]:,}")
print(f"Combustíveis:           {resultado[7]:,}")


# ============================================================
# DISTRIBUIÇÃO POR COMBUSTÍVEL
# ============================================================

print("\n[5] Distribuição por combustível...")

resultado = con.execute(f"""
    SELECT
        nome_combustivel,
        COUNT(*) AS quantidade
    FROM read_parquet('{ARQUIVO_ML}')
    GROUP BY nome_combustivel
    ORDER BY quantidade DESC
""").fetchall()

for combustivel, quantidade in resultado:
    print(f"{combustivel}: {quantidade:,}")


# ============================================================
# DISTRIBUIÇÃO POR SITUAÇÃO DO ANO
# ============================================================

print("\n[6] Situação do ano_modelo...")

resultado = con.execute(f"""
    SELECT
        situacao_ano_modelo,
        COUNT(*) AS quantidade
    FROM read_parquet('{ARQUIVO_ML}')
    GROUP BY situacao_ano_modelo
    ORDER BY quantidade DESC
""").fetchall()

for situacao, quantidade in resultado:
    print(f"{situacao}: {quantidade:,}")


# ============================================================
# ESTATÍSTICAS DO TARGET
# ============================================================

print("\n[7] Estatísticas do valor_fipe...")

resultado = con.execute(f"""
    SELECT
        MIN(valor_fipe),
        AVG(valor_fipe),
        MEDIAN(valor_fipe),
        MAX(valor_fipe)
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

print(f"Mínimo:  R$ {resultado[0]:,.2f}")
print(f"Média:   R$ {resultado[1]:,.2f}")
print(f"Mediana: R$ {resultado[2]:,.2f}")
print(f"Máximo:  R$ {resultado[3]:,.2f}")


# ============================================================
# DUPLICIDADES
# ============================================================

print("\n[8] Verificando duplicidades exatas...")

resultado = con.execute(f"""
    SELECT COUNT(*) - COUNT(DISTINCT md5(
        CONCAT_WS(
            '|',
            codigo_fipe,
            nome_modelo,
            nome_marca,
            nome_combustivel,
            CAST(ano_modelo AS VARCHAR),
            CAST(valor_centavos AS VARCHAR),
            CAST(mes_referencia AS VARCHAR),
            CAST(ano_referencia AS VARCHAR)
        )
    ))
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

print(f"Duplicidades exatas: {resultado[0]:,}")


# ============================================================
# VALIDAÇÃO FINAL
# ============================================================

print("\n[9] Validação final...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS total,

        COUNT(*) FILTER (
            WHERE valor_fipe <= 0
        ) AS erro_valor,

        COUNT(*) FILTER (
            WHERE ano_modelo IS NULL
        ) AS erro_ano,

        COUNT(*) FILTER (
            WHERE nome_marca IS NULL
               OR nome_modelo IS NULL
               OR nome_combustivel IS NULL
        ) AS erro_categoria

    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

if (
    resultado[0] > 0
    and resultado[1] == 0
    and resultado[2] == 0
    and resultado[3] == 0
):
    print("\nBASE ML CRIADA E VALIDADA SEM INCONSISTÊNCIAS.")
else:
    print("\nATENÇÃO: foram encontradas inconsistências.")


# ============================================================
# FINAL
# ============================================================

con.close()

print("\n" + "=" * 70)
print("PREPARAÇÃO DA BASE ML CONCLUÍDA")
print("=" * 70)