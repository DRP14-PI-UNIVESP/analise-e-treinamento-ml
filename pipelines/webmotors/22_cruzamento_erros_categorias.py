
from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURACAO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_DIAGNOSTICO = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "auditoria"
    / "21_diagnostico_categorias.csv"
)

ARQUIVO_PREVISOES = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "modelagem"
    / "20_previsoes_teste_log.csv"
)

DIRETORIO_SAIDA = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "auditoria"
)

ARQUIVO_CRUZADO = (
    DIRETORIO_SAIDA
    / "22_cruzamento_erros_categorias.csv"
)

ARQUIVO_RESUMO = (
    DIRETORIO_SAIDA
    / "22_metricas_por_frequencia.csv"
)


def normalizar_texto(serie):
    return (
        serie.astype("string")
        .fillna("NAO_INFORMADO")
        .str.strip()
        .str.upper()
    )


def main():
    print("=" * 70)
    print("CRUZAMENTO DE ERROS E FREQUENCIA DAS CATEGORIAS")
    print("=" * 70)

    # 1. Validar arquivos
    for arquivo in [ARQUIVO_DIAGNOSTICO, ARQUIVO_PREVISOES]:
        if not arquivo.exists():
            raise FileNotFoundError(
                f"Arquivo nao encontrado: {arquivo}"
            )

    # 2. Carregar arquivos
    print("\n[1] Carregando arquivos...")

    diagnostico = pd.read_csv(
        ARQUIVO_DIAGNOSTICO,
        encoding="utf-8-sig",
    )

    previsoes = pd.read_csv(
        ARQUIVO_PREVISOES,
        encoding="utf-8-sig",
    )

    print(f"Linhas do diagnostico: {len(diagnostico)}")
    print(f"Linhas de previsoes: {len(previsoes)}")

    # 3. Validar colunas
    colunas_diag = [
        "nome_marca",
        "nome_modelo",
        "quantidade_marca_modelo_treino",
        "diagnostico",
    ]

    colunas_prev = [
        "nome_marca",
        "nome_modelo",
        "valor_real",
        "valor_previsto",
    ]

    for coluna in colunas_diag:
        if coluna not in diagnostico.columns:
            raise ValueError(
                f"Coluna ausente no diagnostico: {coluna}"
            )

    for coluna in colunas_prev:
        if coluna not in previsoes.columns:
            raise ValueError(
                f"Coluna ausente nas previsoes: {coluna}"
            )

    # 4. Normalizar chaves para o cruzamento
    print("\n[2] Normalizando marca e modelo...")

    for df in [diagnostico, previsoes]:
        df["nome_marca"] = normalizar_texto(df["nome_marca"])
        df["nome_modelo"] = normalizar_texto(df["nome_modelo"])

    diagnostico["quantidade_marca_modelo_treino"] = pd.to_numeric(
        diagnostico["quantidade_marca_modelo_treino"],
        errors="coerce",
    ).fillna(0).astype(int)

    previsoes["valor_real"] = pd.to_numeric(
        previsoes["valor_real"], errors="coerce"
    )

    previsoes["valor_previsto"] = pd.to_numeric(
        previsoes["valor_previsto"], errors="coerce"
    )

    # 5. Evitar duplicacao inesperada das previsoes
    # O diagnostico possui uma linha por veiculo de teste.
    # Se uma combinacao marca/modelo se repetir, mantemos
    # cada linha de teste usando a ordem das ocorrencias.
    diagnostico["_ocorrencia"] = (
        diagnostico.groupby(["nome_marca", "nome_modelo"])
        .cumcount()
    )

    previsoes["_ocorrencia"] = (
        previsoes.groupby(["nome_marca", "nome_modelo"])
        .cumcount()
    )

    chaves = ["nome_marca", "nome_modelo", "_ocorrencia"]

    colunas_info = chaves + [
        "quantidade_marca_modelo_treino",
        "diagnostico",
    ]

    cruzado = previsoes.merge(
        diagnostico[colunas_info],
        on=chaves,
        how="left",
        validate="one_to_one",
    )

    # 6. Calcular erros a partir das previsoes
    cruzado = cruzado.dropna(
        subset=["valor_real", "valor_previsto"]
    ).copy()

    cruzado["erro_absoluto"] = (
        cruzado["valor_real"] - cruzado["valor_previsto"]
    ).abs()

    cruzado["erro_percentual"] = (
        cruzado["erro_absoluto"]
        / cruzado["valor_real"].abs().replace(0, pd.NA)
        * 100
    )

    cruzado["grupo_frequencia"] = cruzado[
        "quantidade_marca_modelo_treino"
    ].apply(
        lambda n: (
            "0 - Modelo ausente no treino"
            if n == 0
            else "1 - Um exemplo no treino"
            if n == 1
            else "2-4 - Poucos exemplos"
            if n < 5
            else "5+ - Maior representacao"
        )
    )

    # 7. Verificar qualidade do cruzamento
    sem_correspondencia = cruzado["diagnostico"].isna().sum()

    print("\n[3] Validacao do cruzamento")
    print(f"Previsoes cruzadas: {len(cruzado)}")
    print(f"Linhas sem diagnostico correspondente: {sem_correspondencia}")

    if len(cruzado) != len(previsoes):
        print(
            "ATENCAO: a quantidade de linhas mudou. "
            "Verifique a correspondencia entre os arquivos."
        )

    if sem_correspondencia:
        print(
            "ATENCAO: algumas linhas nao foram associadas "
            "a uma categoria. Confira nomes e duplicidades."
        )

    # 8. Resumo por frequencia
    print("\n[4] Metricas por frequencia no treino")

    resumo = (
        cruzado.groupby("grupo_frequencia", dropna=False)
        .agg(
            quantidade=("valor_real", "size"),
            MAE=("erro_absoluto", "mean"),
            MAPE=("erro_percentual", "mean"),
            RMSE=(
                "erro_absoluto",
                lambda x: (
                    (x.pow(2).mean()) ** 0.5
                ),
            ),
        )
        .reset_index()
    )

    # RMSE correto utiliza o quadrado do erro assinado,
    # que e equivalente ao quadrado do erro absoluto.
    resumo[["MAE", "MAPE", "RMSE"]] = resumo[
        ["MAE", "MAPE", "RMSE"]
    ].round(2)

    print(resumo.to_string(index=False))

    # 9. Maiores erros
    print("\n[5] Dez maiores erros")

    colunas_exibir = [
        "nome_marca",
        "nome_modelo",
        "valor_real",
        "valor_previsto",
        "erro_absoluto",
        "erro_percentual",
        "quantidade_marca_modelo_treino",
        "grupo_frequencia",
    ]

    print(
        cruzado.sort_values(
            "erro_absoluto",
            ascending=False,
        )[colunas_exibir]
        .head(10)
        .round(2)
        .to_string(index=False)
    )

    # 10. Salvar resultados
    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    cruzado.drop(columns=["_ocorrencia"]).to_csv(
        ARQUIVO_CRUZADO,
        index=False,
        encoding="utf-8-sig",
    )

    resumo.to_csv(
        ARQUIVO_RESUMO,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[6] Arquivos gerados:")
    print(ARQUIVO_CRUZADO)
    print(ARQUIVO_RESUMO)
    print("\nCruzamento concluido.")


if __name__ == "__main__":
    main()
