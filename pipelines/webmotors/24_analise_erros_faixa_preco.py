
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import KFold
from sklearn.preprocessing import OrdinalEncoder


# ============================================================
# CONFIGURACAO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_ENTRADA = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "03_webmotors_ouro.parquet"
)

DIR_SAIDA = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "auditoria"
)

ARQUIVO_PREVISOES = DIR_SAIDA / "24_previsoes_oof.csv"
ARQUIVO_FAIXAS = DIR_SAIDA / "24_metricas_faixa_preco.csv"
ARQUIVO_MAIORES_ERROS = DIR_SAIDA / "24_maiores_erros.csv"

ALVO = "valor_anuncio"

CATEGORICAS = [
    "nome_marca",
    "nome_modelo",
    "nome_combustivel",
    "cambio",
    "carroceria",
    "tipo_vendedor",
    "cidade",
    "bairro",
    "tracao",
]

NUMERICAS = [
    "ano_fabricacao",
    "ano_modelo",
    "idade_veiculo",
    "quilometragem",
    "potencia",
    "cilindrada",
]

N_PARTES = 5
SEMENTE = 42


# ============================================================
# PREPARACAO DAS FEATURES
# ============================================================

def preparar_categoricas(treino, teste):
    treino_cat_df = treino[CATEGORICAS].copy()
    teste_cat_df = teste[CATEGORICAS].copy()

    for coluna in CATEGORICAS:
        treino_cat_df[coluna] = (
            treino_cat_df[coluna]
            .fillna("__AUSENTE__")
            .astype(str)
        )
        teste_cat_df[coluna] = (
            teste_cat_df[coluna]
            .fillna("__AUSENTE__")
            .astype(str)
        )

    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        dtype=np.float64,
    )

    treino_cat = encoder.fit_transform(treino_cat_df)
    teste_cat = encoder.transform(teste_cat_df)

    return treino_cat, teste_cat


def preparar_numericas(treino, teste):
    treino_num = treino[NUMERICAS].copy()
    teste_num = teste[NUMERICAS].copy()

    treino_num = treino_num.apply(
        pd.to_numeric, errors="coerce"
    )
    teste_num = teste_num.apply(
        pd.to_numeric, errors="coerce"
    )

    # As medianas sao calculadas somente com o treino de cada parte.
    medianas = treino_num.median().fillna(0)

    treino_num = treino_num.fillna(medianas)
    teste_num = teste_num.fillna(medianas)

    return (
        treino_num.to_numpy(dtype=np.float64),
        teste_num.to_numpy(dtype=np.float64),
    )


def calcular_mape(real, previsto):
    real = np.asarray(real, dtype=float)
    previsto = np.asarray(previsto, dtype=float)

    mascara = real > 0

    if not mascara.any():
        return float("nan")

    return float(
        np.mean(
            np.abs(
                (real[mascara] - previsto[mascara])
                / real[mascara]
            )
        ) * 100
    )


# ============================================================
# EXECUCAO
# ============================================================

def main():
    print("=" * 70)
    print("ETAPA 24 - ANALISE DOS ERROS POR FAIXA DE PRECO")
    print("=" * 70)

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo Ouro nao encontrado: {ARQUIVO_ENTRADA}"
        )

    print("\n[1] Carregando dados...")
    df = pd.read_parquet(ARQUIVO_ENTRADA)

    colunas_necessarias = [ALVO] + CATEGORICAS + NUMERICAS
    ausentes = [
        coluna for coluna in colunas_necessarias
        if coluna not in df.columns
    ]

    if ausentes:
        raise ValueError(
            f"Colunas ausentes no arquivo Ouro: {ausentes}"
        )

    df[ALVO] = pd.to_numeric(df[ALVO], errors="coerce")
    df = df.loc[
        df[ALVO].notna() & (df[ALVO] > 0)
    ].reset_index(drop=True)

    print(f"Registros validos: {len(df)}")
    print("Validacao cruzada: 5 partes")
    print("Alvo: log1p(valor_anuncio)")

    # ========================================================
    # VALIDACAO CRUZADA E PREVISOES FORA DA AMOSTRA
    # ========================================================

    print("\n[2] Gerando previsoes fora da amostra...")

    kfold = KFold(
        n_splits=N_PARTES,
        shuffle=True,
        random_state=SEMENTE,
    )

    resultados = []

    colunas_identificacao = [
        coluna
        for coluna in [
            "nome_marca",
            "nome_modelo",
            "ano_fabricacao",
            "ano_modelo",
            "quilometragem",
            "nome_combustivel",
            "cidade",
        ]
        if coluna in df.columns
    ]

    for numero_parte, (idx_treino, idx_teste) in enumerate(
        kfold.split(df), start=1
    ):
        treino = df.iloc[idx_treino].copy()
        teste = df.iloc[idx_teste].copy()

        treino_cat, teste_cat = preparar_categoricas(
            treino, teste
        )
        treino_num, teste_num = preparar_numericas(
            treino, teste
        )

        X_treino = np.column_stack(
            [treino_cat, treino_num]
        )
        X_teste = np.column_stack(
            [teste_cat, teste_num]
        )

        y_treino = treino[ALVO].to_numpy(dtype=float)
        y_teste = teste[ALVO].to_numpy(dtype=float)

        modelo = HistGradientBoostingRegressor(
            max_iter=100,
            learning_rate=0.05,
            max_leaf_nodes=7,
            min_samples_leaf=15,
            loss="squared_error",
            random_state=42,
            early_stopping=False,
        )

        modelo.fit(X_treino, np.log1p(y_treino))

        previsoes = np.maximum(
            np.expm1(modelo.predict(X_teste)),
            0,
        )

        parte = teste[colunas_identificacao].copy()
        parte["indice_registro"] = teste.index.to_numpy()
        parte["parte_validacao"] = numero_parte
        parte["valor_real"] = y_teste
        parte["valor_previsto"] = previsoes
        parte["erro_absoluto"] = np.abs(y_teste - previsoes)
        parte["erro_percentual"] = (
            parte["erro_absoluto"] / parte["valor_real"] * 100
        )

        resultados.append(parte)

        print(
            f"Parte {numero_parte}/{N_PARTES}: "
            f"{len(teste)} previsoes geradas."
        )

    previsoes_df = pd.concat(
        resultados, ignore_index=True
    )

    # ========================================================
    # CLASSIFICACAO POR FAIXA DE PRECO REAL
    # ========================================================

    print("\n[3] Calculando metricas por faixa de preco...")

    limites = [0, 50000, 100000, 200000, 400000, np.inf]
    rotulos = [
        "Ate R$ 50 mil",
        "R$ 50 mil a R$ 100 mil",
        "R$ 100 mil a R$ 200 mil",
        "R$ 200 mil a R$ 400 mil",
        "Acima de R$ 400 mil",
    ]

    previsoes_df["faixa_preco_real"] = pd.cut(
        previsoes_df["valor_real"],
        bins=limites,
        labels=rotulos,
        include_lowest=True,
        right=True,
    )

    metricas_faixas = []

    for faixa in rotulos:
        grupo = previsoes_df.loc[
            previsoes_df["faixa_preco_real"] == faixa
        ]

        if grupo.empty:
            metricas_faixas.append({
                "faixa_preco_real": faixa,
                "quantidade": 0,
                "MAE": np.nan,
                "RMSE": np.nan,
                "MAPE_percentual": np.nan,
                "erro_absoluto_maximo": np.nan,
            })
            continue

        real = grupo["valor_real"].to_numpy(dtype=float)
        previsto = grupo["valor_previsto"].to_numpy(dtype=float)

        metricas_faixas.append({
            "faixa_preco_real": faixa,
            "quantidade": len(grupo),
            "MAE": mean_absolute_error(real, previsto),
            "RMSE": np.sqrt(
                mean_squared_error(real, previsto)
            ),
            "MAPE_percentual": calcular_mape(real, previsto),
            "erro_absoluto_maximo": grupo["erro_absoluto"].max(),
        })

    tabela_faixas = pd.DataFrame(metricas_faixas)

    # ========================================================
    # MAIORES ERROS
    # ========================================================

    maiores_erros = previsoes_df.sort_values(
        "erro_absoluto", ascending=False
    ).head(20)

    # ========================================================
    # SALVAMENTO
    # ========================================================

    print("\n[4] Salvando arquivos...")
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)

    previsoes_df.to_csv(
        ARQUIVO_PREVISOES,
        index=False,
        encoding="utf-8-sig",
        float_format="%.2f",
    )

    tabela_faixas.to_csv(
        ARQUIVO_FAIXAS,
        index=False,
        encoding="utf-8-sig",
        float_format="%.2f",
    )

    maiores_erros.to_csv(
        ARQUIVO_MAIORES_ERROS,
        index=False,
        encoding="utf-8-sig",
        float_format="%.2f",
    )

    print("\n[5] Metricas por faixa de preco real")
    print(
        tabela_faixas.to_string(
            index=False,
            float_format=lambda valor: f"{valor:,.2f}",
        )
    )

    print("\n[6] Dez maiores erros absolutos")
    colunas_erros = [
        coluna
        for coluna in [
            "nome_marca",
            "nome_modelo",
            "valor_real",
            "valor_previsto",
            "erro_absoluto",
            "erro_percentual",
            "faixa_preco_real",
            "parte_validacao",
        ]
        if coluna in maiores_erros.columns
    ]

    print(
        maiores_erros[colunas_erros]
        .head(10)
        .to_string(index=False)
    )

    print("\nArquivos gerados:")
    print(ARQUIVO_PREVISOES)
    print(ARQUIVO_FAIXAS)
    print(ARQUIVO_MAIORES_ERROS)

    print("\nEtapa 24 concluida.")


if __name__ == "__main__":
    main()
