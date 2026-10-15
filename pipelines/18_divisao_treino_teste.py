from pathlib import Path
import duckdb


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ARQUIVO_ENTRADA = BASE_DIR / "data" / "ouro" / "05_fipe_features.parquet"

ARQUIVO_TREINO = BASE_DIR / "data" / "ouro" / "06_fipe_treino.parquet"
ARQUIVO_TESTE = BASE_DIR / "data" / "ouro" / "07_fipe_teste.parquet"


# ============================================================
# CONEXÃO
# ============================================================

print("=" * 70)
print("DIVISÃO TEMPORAL — TREINO E TESTE")
print("=" * 70)

con = duckdb.connect()

print("\n[1] Conectando ao dataset...")
print("Conexão estabelecida.")


# ============================================================
# PERÍODO DISPONÍVEL
# ============================================================

print("\n[2] Verificando período disponível...")

periodo = con.execute(f"""
    SELECT
        MIN(data_referencia),
        MAX(data_referencia),
        COUNT(DISTINCT data_referencia)
    FROM read_parquet('{ARQUIVO_ENTRADA}')
""").fetchone()

print(f"Primeira referência: {periodo[0]}")
print(f"Última referência:   {periodo[1]}")
print(f"Referências distintas: {periodo[2]}")


# ============================================================
# DIVISÃO TEMPORAL
# ============================================================

# Estratégia:
# Treino: até 2024-12-01
# Teste:  2025-01-01 em diante

DATA_CORTE = "2025-01-01"

print(f"\n[3] Dividindo os dados...")
print(f"Data de corte: {DATA_CORTE}")

con.execute(f"""
COPY (
    SELECT *
    FROM read_parquet('{ARQUIVO_ENTRADA}')
    WHERE data_referencia < DATE '{DATA_CORTE}'
)
TO '{ARQUIVO_TREINO}'
(FORMAT PARQUET, COMPRESSION ZSTD);
""")

con.execute(f"""
COPY (
    SELECT *
    FROM read_parquet('{ARQUIVO_ENTRADA}')
    WHERE data_referencia >= DATE '{DATA_CORTE}'
)
TO '{ARQUIVO_TESTE}'
(FORMAT PARQUET, COMPRESSION ZSTD);
""")


# ============================================================
# CONTAGEM
# ============================================================

print("\n[4] Contando registros...")

treino = con.execute(f"""
    SELECT COUNT(*)
    FROM read_parquet('{ARQUIVO_TREINO}')
""").fetchone()[0]

teste = con.execute(f"""
    SELECT COUNT(*)
    FROM read_parquet('{ARQUIVO_TESTE}')
""").fetchone()[0]

total = treino + teste

print(f"Treino: {treino:,}".replace(",", "."))
print(f"Teste:  {teste:,}".replace(",", "."))
print(f"Total:  {total:,}".replace(",", "."))


# ============================================================
# PERÍODO DE CADA CONJUNTO
# ============================================================

print("\n[5] Verificando períodos...")

periodo_treino = con.execute(f"""
    SELECT
        MIN(data_referencia),
        MAX(data_referencia)
    FROM read_parquet('{ARQUIVO_TREINO}')
""").fetchone()

periodo_teste = con.execute(f"""
    SELECT
        MIN(data_referencia),
        MAX(data_referencia)
    FROM read_parquet('{ARQUIVO_TESTE}')
""").fetchone()

print(
    f"Treino: {periodo_treino[0]} até {periodo_treino[1]}"
)

print(
    f"Teste:  {periodo_teste[0]} até {periodo_teste[1]}"
)


# ============================================================
# VERIFICAÇÃO DE VAZAMENTO TEMPORAL
# ============================================================

print("\n[6] Verificando vazamento temporal...")

vazamento = con.execute(f"""
    SELECT COUNT(*)
    FROM read_parquet('{ARQUIVO_TREINO}')
    WHERE data_referencia >= DATE '{DATA_CORTE}'
""").fetchone()[0]

print(f"Registros de teste dentro do treino: {vazamento}")


# ============================================================
# COMPARAÇÃO DE CATEGORIAS
# ============================================================

print("\n[7] Comparando categorias...")

categorias = con.execute(f"""
    SELECT
        'Treino' AS conjunto,
        COUNT(DISTINCT codigo_fipe),
        COUNT(DISTINCT marca_normalizada),
        COUNT(DISTINCT modelo_normalizado),
        COUNT(DISTINCT combustivel_normalizado)
    FROM read_parquet('{ARQUIVO_TREINO}')

    UNION ALL

    SELECT
        'Teste' AS conjunto,
        COUNT(DISTINCT codigo_fipe),
        COUNT(DISTINCT marca_normalizada),
        COUNT(DISTINCT modelo_normalizado),
        COUNT(DISTINCT combustivel_normalizado)
    FROM read_parquet('{ARQUIVO_TESTE}')
""").fetchall()

for linha in categorias:
    print(
        f"{linha[0]}:"
        f" FIPE={linha[1]:,}".replace(",", "."),
        f" marcas={linha[2]:,}".replace(",", "."),
        f" modelos={linha[3]:,}".replace(",", "."),
        f" combustíveis={linha[4]}"
    )


# ============================================================
# VALIDAÇÃO FINAL
# ============================================================

print("\n[8] Validação final...")

if total != 8_585_271:
    raise ValueError(
        f"Quantidade total inesperada: {total}"
    )

if vazamento != 0:
    raise ValueError(
        f"Foi detectado vazamento temporal: {vazamento}"
    )

if treino == 0 or teste == 0:
    raise ValueError("Treino ou teste ficou vazio.")


print("\n" + "=" * 70)
print("DIVISÃO TEMPORAL VALIDADA")
print("=" * 70)

print("\nArquivos criados:")
print(ARQUIVO_TREINO)
print(ARQUIVO_TESTE)

con.close()