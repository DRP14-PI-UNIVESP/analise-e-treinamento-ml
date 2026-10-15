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
print("DIAGNÓSTICO PARA PREPARAÇÃO DO DATASET DE MACHINE LEARNING")
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
# 1. QUANTIDADE DE REGISTROS
# ============================================================

print("\n" + "=" * 70)
print("[2] QUANTIDADE DE REGISTROS")
print("=" * 70)

total = con.execute("""
    SELECT COUNT(*)
    FROM ouro
""").fetchone()[0]

print(f"Total: {total:,}")


# ============================================================
# 2. VALORES NULOS POR COLUNA
# ============================================================

print("\n" + "=" * 70)
print("[3] VALORES NULOS")
print("=" * 70)

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
    "situacao_ano_modelo",
]

for coluna in colunas:
    resultado = con.execute(f"""
        SELECT COUNT(*)
        FROM ouro
        WHERE "{coluna}" IS NULL
    """).fetchone()[0]

    percentual = resultado / total * 100

    print(
        f"{coluna:25} "
        f"{resultado:12,} "
        f"({percentual:6.2f}%)"
    )


# ============================================================
# 3. VALORES VAZIOS EM TEXTO
# ============================================================

print("\n" + "=" * 70)
print("[4] TEXTOS VAZIOS OU SOMENTE ESPAÇOS")
print("=" * 70)

for coluna in [
    "codigo_fipe",
    "nome_modelo",
    "nome_marca",
    "nome_combustivel",
    "valor_formatado",
    "situacao_ano_modelo",
]:

    resultado = con.execute(f"""
        SELECT COUNT(*)
        FROM ouro
        WHERE "{coluna}" IS NOT NULL
          AND TRIM("{coluna}") = ''
    """).fetchone()[0]

    print(f"{coluna:25} {resultado:,}")


# ============================================================
# 4. TARGET DO MODELO
# ============================================================

print("\n" + "=" * 70)
print("[5] VARIÁVEL-ALVO — valor_fipe")
print("=" * 70)

target = con.execute("""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE valor_fipe IS NULL) AS nulos,
        COUNT(*) FILTER (WHERE valor_fipe <= 0) AS menores_iguais_zero,
        COUNT(*) FILTER (WHERE valor_fipe > 0) AS positivos
    FROM ouro
""").fetchone()

print(f"Total:                 {target[0]:,}")
print(f"Nulos:                 {target[1]:,}")
print(f"Menores ou iguais a 0: {target[2]:,}")
print(f"Positivos:             {target[3]:,}")


# ============================================================
# 5. ANO DO MODELO
# ============================================================

print("\n" + "=" * 70)
print("[6] ANO DO MODELO")
print("=" * 70)

ano = con.execute("""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE ano_modelo IS NULL) AS sem_ano,
        COUNT(*) FILTER (WHERE ano_modelo IS NOT NULL) AS com_ano,
        MIN(ano_modelo) AS minimo,
        MAX(ano_modelo) AS maximo
    FROM ouro
""").fetchone()

print(f"Total:       {ano[0]:,}")
print(f"Sem ano:     {ano[1]:,}")
print(f"Com ano:     {ano[2]:,}")
print(f"Mínimo:      {ano[3]}")
print(f"Máximo:      {ano[4]}")


# ============================================================
# 6. IDADE DO VEÍCULO
# ============================================================

print("\n" + "=" * 70)
print("[7] IDADE DO VEÍCULO")
print("=" * 70)

idade = con.execute("""
    SELECT
        COUNT(*) FILTER (WHERE idade_veiculo IS NULL),
        COUNT(*) FILTER (WHERE idade_veiculo < 0),
        COUNT(*) FILTER (WHERE idade_veiculo = 0),
        COUNT(*) FILTER (WHERE idade_veiculo >= 0)
    FROM ouro
""").fetchone()

print(f"Nula:                  {idade[0]:,}")
print(f"Negativa:              {idade[1]:,}")
print(f"Zero:                  {idade[2]:,}")
print(f"Maior ou igual a zero: {idade[3]:,}")


# ============================================================
# 7. SITUAÇÃO DO ANO
# ============================================================

print("\n" + "=" * 70)
print("[8] SITUAÇÃO DO ANO DO MODELO")
print("=" * 70)

situacoes = con.execute("""
    SELECT
        situacao_ano_modelo,
        COUNT(*) AS quantidade
    FROM ouro
    GROUP BY situacao_ano_modelo
    ORDER BY quantidade DESC
""").fetchall()

for situacao, quantidade in situacoes:
    percentual = quantidade / total * 100
    print(f"{situacao:30} {quantidade:12,} ({percentual:6.2f}%)")


# ============================================================
# 8. CATEGORIAS
# ============================================================

print("\n" + "=" * 70)
print("[9] CARDINALIDADE DAS VARIÁVEIS CATEGÓRICAS")
print("=" * 70)

for coluna in [
    "codigo_fipe",
    "nome_marca",
    "nome_modelo",
    "nome_combustivel",
]:

    quantidade = con.execute(f"""
        SELECT COUNT(DISTINCT "{coluna}")
        FROM ouro
    """).fetchone()[0]

    print(f"{coluna:25} {quantidade:,} valores distintos")


# ============================================================
# 9. CÓDIGO FIPE E TARGET
# ============================================================

print("\n" + "=" * 70)
print("[10] CÓDIGO FIPE × VARIAÇÃO DE PREÇO")
print("=" * 70)

resultado = con.execute("""
    SELECT
        COUNT(*) AS codigos,
        COUNT(*) FILTER (WHERE qtd_valores = 1) AS apenas_um_valor,
        COUNT(*) FILTER (WHERE qtd_valores > 1) AS varios_valores
    FROM (
        SELECT
            codigo_fipe,
            COUNT(DISTINCT valor_fipe) AS qtd_valores
        FROM ouro
        WHERE valor_fipe > 0
        GROUP BY codigo_fipe
    )
""").fetchone()

print(f"Códigos FIPE analisados: {resultado[0]:,}")
print(f"Com apenas um valor:     {resultado[1]:,}")
print(f"Com vários valores:      {resultado[2]:,}")


# ============================================================
# 10. REGISTROS UTILIZÁVEIS PARA ML
# ============================================================

print("\n" + "=" * 70)
print("[11] CANDIDATOS PARA DATASET DE ML")
print("=" * 70)

ml = con.execute("""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (
            WHERE valor_fipe > 0
        ) AS valor_positivo,
        COUNT(*) FILTER (
            WHERE valor_fipe > 0
              AND ano_modelo IS NOT NULL
        ) AS valor_e_ano,
        COUNT(*) FILTER (
            WHERE valor_fipe > 0
              AND ano_modelo IS NOT NULL
              AND TRIM(nome_marca) <> ''
              AND TRIM(nome_modelo) <> ''
              AND TRIM(nome_combustivel) <> ''
        ) AS candidato_ml
    FROM ouro
""").fetchone()

print(f"Total Ouro:                 {ml[0]:,}")
print(f"Com valor > 0:              {ml[1]:,}")
print(f"Com valor > 0 + ano:        {ml[2]:,}")
print(f"Candidato inicial para ML:  {ml[3]:,}")


# ============================================================
# 11. DISTRIBUIÇÃO DOS CANDIDATOS
# ============================================================

print("\n" + "=" * 70)
print("[12] DISTRIBUIÇÃO DOS CANDIDATOS POR COMBUSTÍVEL")
print("=" * 70)

combustiveis = con.execute("""
    SELECT
        nome_combustivel,
        COUNT(*) AS quantidade
    FROM ouro
    WHERE valor_fipe > 0
      AND ano_modelo IS NOT NULL
    GROUP BY nome_combustivel
    ORDER BY quantidade DESC
""").fetchall()

for combustivel, quantidade in combustiveis:
    print(f"{combustivel:20} {quantidade:,}")


# ============================================================
# 12. POSSÍVEIS PROBLEMAS PARA ML
# ============================================================

print("\n" + "=" * 70)
print("[13] POSSÍVEIS PROBLEMAS PARA MACHINE LEARNING")
print("=" * 70)

problemas = con.execute("""
    SELECT
        COUNT(*) FILTER (WHERE valor_fipe <= 0) AS valor_invalido,
        COUNT(*) FILTER (WHERE ano_modelo IS NULL) AS ano_ausente,
        COUNT(*) FILTER (WHERE idade_veiculo < 0) AS idade_negativa,
        COUNT(*) FILTER (WHERE TRIM(nome_marca) = '') AS marca_vazia,
        COUNT(*) FILTER (WHERE TRIM(nome_modelo) = '') AS modelo_vazio,
        COUNT(*) FILTER (WHERE TRIM(nome_combustivel) = '') AS combustivel_vazio
    FROM ouro
""").fetchone()

nomes = [
    "valor_fipe <= 0",
    "ano_modelo ausente",
    "idade_veiculo negativa",
    "marca vazia",
    "modelo vazio",
    "combustível vazio",
]

for nome, quantidade in zip(nomes, problemas):
    print(f"{nome:30} {quantidade:,}")


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("DIAGNÓSTICO DE ML CONCLUÍDO")
print("=" * 70)

con.close()