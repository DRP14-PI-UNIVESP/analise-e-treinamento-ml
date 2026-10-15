# ============================================================
# 16_auditoria_duplicidades_ml.py
# AUDITORIA DAS DUPLICIDADES LÓGICAS DA BASE ML
# ============================================================

from pathlib import Path
import duckdb


# ============================================================
# BLOCO 1 — CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_ML = BASE_DIR / "data" / "ouro" / "04_fipe_ml.parquet"

print("=" * 70)
print("AUDITORIA DE DUPLICIDADES DA BASE ML")
print("=" * 70)

con = duckdb.connect()

print("\n[1] Conectando à base ML...")
print("Conexão estabelecida.")


# ============================================================
# BLOCO 2 — CONFIRMAÇÃO DO TOTAL
# ============================================================

print("\n[2] Total de registros...")

resultado = con.execute(f"""
    SELECT COUNT(*)
    FROM read_parquet('{ARQUIVO_ML}')
""").fetchone()

print(f"Registros: {resultado[0]:,}")


# ============================================================
# BLOCO 3 — GRUPOS DUPLICADOS
# ============================================================

print("\n[3] Grupos com mesma combinação lógica...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS grupos,
        SUM(quantidade) AS registros
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
# BLOCO 4 — DUPLICATAS EXATAMENTE IGUAIS
# ============================================================

print("\n[4] Registros exatamente iguais...")

resultado = con.execute(f"""
    SELECT
        COUNT(*) AS grupos,
        COALESCE(SUM(quantidade), 0) AS registros
    FROM (
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
            situacao_ano_modelo,
            COUNT(*) AS quantidade
        FROM read_parquet('{ARQUIVO_ML}')
        GROUP BY
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
        HAVING COUNT(*) > 1
    )
""").fetchone()

print(f"Grupos exatamente iguais: {resultado[0]:,}")
print(f"Registros envolvidos:     {resultado[1]:,}")


# ============================================================
# BLOCO 5 — DIFERENÇAS DE VALOR FIPE
# ============================================================

print("\n[5] Duplicidades com valores FIPE diferentes...")

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
            COUNT(*) AS quantidade,
            COUNT(DISTINCT valor_fipe) AS valores
        FROM read_parquet('{ARQUIVO_ML}')
        GROUP BY
            codigo_fipe,
            ano_modelo,
            ano_referencia,
            mes_referencia
        HAVING
            COUNT(*) > 1
            AND COUNT(DISTINCT valor_fipe) > 1
    )
""").fetchone()

print(f"Grupos com valores diferentes: {resultado[0]:,}")
print(f"Registros envolvidos:          {resultado[1]:,}")


# ============================================================
# BLOCO 6 — DIFERENÇAS DE TEXTO
# ============================================================

print("\n[6] Duplicidades com diferenças de descrição...")

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
            COUNT(*) AS quantidade,
            COUNT(DISTINCT nome_modelo) AS modelos,
            COUNT(DISTINCT nome_marca) AS marcas,
            COUNT(DISTINCT nome_combustivel) AS combustiveis,
            COUNT(DISTINCT valor_formatado) AS formatos
        FROM read_parquet('{ARQUIVO_ML}')
        GROUP BY
            codigo_fipe,
            ano_modelo,
            ano_referencia,
            mes_referencia
        HAVING
            COUNT(*) > 1
            AND (
                COUNT(DISTINCT nome_modelo) > 1
                OR COUNT(DISTINCT nome_marca) > 1
                OR COUNT(DISTINCT nome_combustivel) > 1
                OR COUNT(DISTINCT valor_formatado) > 1
            )
    )
""").fetchone()

print(f"Grupos com diferenças de descrição: {resultado[0]:,}")
print(f"Registros envolvidos:                {resultado[1]:,}")


# ============================================================
# BLOCO 7 — DIFERENÇAS DE MARCA
# ============================================================

print("\n[7] Duplicidades com marcas diferentes...")

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
            COUNT(*) AS quantidade,
            COUNT(DISTINCT nome_marca) AS marcas
        FROM read_parquet('{ARQUIVO_ML}')
        GROUP BY
            codigo_fipe,
            ano_modelo,
            ano_referencia,
            mes_referencia
        HAVING
            COUNT(*) > 1
            AND COUNT(DISTINCT nome_marca) > 1
    )
""").fetchone()

print(f"Grupos com marcas diferentes: {resultado[0]:,}")
print(f"Registros envolvidos:           {resultado[1]:,}")


# ============================================================
# BLOCO 8 — DIFERENÇAS DE MODELO
# ============================================================

print("\n[8] Duplicidades com modelos diferentes...")

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
            COUNT(*) AS quantidade,
            COUNT(DISTINCT nome_modelo) AS modelos
        FROM read_parquet('{ARQUIVO_ML}')
        GROUP BY
            codigo_fipe,
            ano_modelo,
            ano_referencia,
            mes_referencia
        HAVING
            COUNT(*) > 1
            AND COUNT(DISTINCT nome_modelo) > 1
    )
""").fetchone()

print(f"Grupos com modelos diferentes: {resultado[0]:,}")
print(f"Registros envolvidos:           {resultado[1]:,}")


# ============================================================
# BLOCO 9 — DIFERENÇAS DE COMBUSTÍVEL
# ============================================================

print("\n[9] Duplicidades com combustíveis diferentes...")

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
            COUNT(*) AS quantidade,
            COUNT(DISTINCT nome_combustivel) AS combustiveis
        FROM read_parquet('{ARQUIVO_ML}')
        GROUP BY
            codigo_fipe,
            ano_modelo,
            ano_referencia,
            mes_referencia
        HAVING
            COUNT(*) > 1
            AND COUNT(DISTINCT nome_combustivel) > 1
    )
""").fetchone()

print(f"Grupos com combustíveis diferentes: {resultado[0]:,}")
print(f"Registros envolvidos:               {resultado[1]:,}")


# ============================================================
# BLOCO 10 — CÓDIGOS COM MAIS DUPLICIDADES
# ============================================================

print("\n[10] Códigos FIPE com mais duplicidades...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        COUNT(*) AS registros_duplicados
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
    GROUP BY codigo_fipe
    ORDER BY registros_duplicados DESC
    LIMIT 20
""").fetchall()

for codigo, quantidade in resultado:
    print(f"{codigo}: {quantidade:,}")


# ============================================================
# BLOCO 11 — EXEMPLOS DE DUPLICIDADES
# ============================================================

print("\n[11] Exemplos de duplicidades...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        nome_marca,
        nome_modelo,
        nome_combustivel,
        ano_modelo,
        ano_referencia,
        mes_referencia,
        valor_fipe,
        COUNT(*) AS quantidade
    FROM read_parquet('{ARQUIVO_ML}')
    GROUP BY
        codigo_fipe,
        nome_marca,
        nome_modelo,
        nome_combustivel,
        ano_modelo,
        ano_referencia,
        mes_referencia,
        valor_fipe
    HAVING COUNT(*) > 1
    ORDER BY quantidade DESC
    LIMIT 20
""").fetchall()

for linha in resultado:
    print(
        f"{linha[0]} | "
        f"{linha[1]} | "
        f"{linha[2]} | "
        f"{linha[3]} | "
        f"ano: {linha[4]} | "
        f"ref: {linha[5]}/{linha[6]} | "
        f"R$ {linha[7]:,.2f} | "
        f"ocorrências: {linha[8]}"
    )


# ============================================================
# BLOCO 12 — EXEMPLOS COM VALORES DIFERENTES
# ============================================================

print("\n[12] Exemplos de duplicidades com valores diferentes...")

resultado = con.execute(f"""
    SELECT
        codigo_fipe,
        ano_modelo,
        ano_referencia,
        mes_referencia,
        COUNT(*) AS quantidade,
        COUNT(DISTINCT valor_fipe) AS valores_diferentes,
        MIN(valor_fipe) AS menor_valor,
        MAX(valor_fipe) AS maior_valor
    FROM read_parquet('{ARQUIVO_ML}')
    GROUP BY
        codigo_fipe,
        ano_modelo,
        ano_referencia,
        mes_referencia
    HAVING
        COUNT(*) > 1
        AND COUNT(DISTINCT valor_fipe) > 1
    ORDER BY quantidade DESC
    LIMIT 20
""").fetchall()

for linha in resultado:
    print(
        f"{linha[0]} | "
        f"ano: {linha[1]} | "
        f"ref: {linha[2]}/{linha[3]} | "
        f"registros: {linha[4]:,} | "
        f"valores: {linha[5]:,} | "
        f"mín: R$ {linha[6]:,.2f} | "
        f"máx: R$ {linha[7]:,.2f}"
    )


# ============================================================
# BLOCO 13 — CONCLUSÃO AUTOMÁTICA
# ============================================================

print("\n" + "=" * 70)
print("AUDITORIA CONCLUÍDA")
print("=" * 70)

con.close()