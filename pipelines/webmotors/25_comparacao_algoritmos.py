
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
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
    / "modelagem"
)

ARQUIVO_RESULTADOS = (
    DIR_SAIDA / "25_comparacao_algoritmos.csv"
)

ARQUIVO_RESUMO = (
    DIR_SAIDA / "25_resumo_algoritmos.csv"
)

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
# PREPARACAO DOS DADOS
# ============================================================

def preparar_dados(treino, teste):
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

    treino_num_df = treino[NUMERICAS].apply(
        pd.to_numeric, errors="coerce"
    )
    teste_num_df = teste[NUMERICAS].apply(
        pd.to_numeric, errors="coerce"
    )

    medianas = treino_num_df.median().fillna(0)

    treino_num = treino_num_df.fillna(medianas).to_numpy(
        dtype=np.float64
    )
    teste_num = teste_num_df.fillna(medianas).to_numpy(
        dtype=np.float64
    )

    X_treino = np.column_stack([treino_cat, treino_num])
    X_teste = np.column_stack([teste_cat, teste_num])

    return X_treino, X_teste


# ============================================================
# METRICAS
# ============================================================

def calcular_metricas(real, previsto):
    real = np.asarray(real, dtype=float)
    previsto = np.asarray(previsto, dtype=float)

    return {
        "MAE": mean_absolute_error(real, previsto),
        "RMSE": np.sqrt(
            mean_squared_error(real, previsto)
        ),
        "R2": r2_score(real, previsto),
        "MAPE_percentual": np.mean(
            np.abs((real - previsto) / real)
        ) * 100,
    }


# ============================================================
# MODELOS
# ============================================================

def criar_modelos():
    return {
        "HistGradientBoosting": HistGradientBoostingRegressor(
            max_iter=100,
            learning_rate=0.05,
            max_leaf_nodes=7,
            min_samples_leaf=15,
            loss="squared_error",
            random_state=42,
            early_stopping=False,
        ),

        "RandomForest": RandomForestRegressor(
            n_estimators=300,
            max_features=1.0,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),

        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=300,
            max_features=1.0,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
    }


# ============================================================
# EXECUCAO
# ============================================================

def main():
    print("=" * 70)
    print("ETAPA 25 - COMPARACAO DE ALGORITMOS")
    print("=" * 70)

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo Ouro nao encontrado: {ARQUIVO_ENTRADA}"
        )

    print("\n[1] Carregando dados Ouro...")
    df = pd.read_parquet(ARQUIVO_ENTRADA)

    colunas = [ALVO] + CATEGORICAS + NUMERICAS
    ausentes = [
        coluna for coluna in colunas
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
    print(f"Validacao cruzada: {N_PARTES} partes")
    print("Transformacao do alvo: log1p")
    print("Modelos: HistGradientBoosting, RandomForest, ExtraTrees")

    kfold = KFold(
        n_splits=N_PARTES,
        shuffle=True,
        random_state=SEMENTE,
    )

    resultados = []

    print("\n[2] Treinando e avaliando modelos...")

    for numero_parte, (idx_treino, idx_teste) in enumerate(
        kfold.split(df), start=1
    ):
        treino = df.iloc[idx_treino].copy()
        teste = df.iloc[idx_teste].copy()

        X_treino, X_teste = preparar_dados(treino, teste)

        y_treino = treino[ALVO].to_numpy(dtype=float)
        y_teste = teste[ALVO].to_numpy(dtype=float)

        y_treino_log = np.log1p(y_treino)

        for nome_modelo, modelo in criar_modelos().items():
            modelo.fit(X_treino, y_treino_log)

            previsoes_log = modelo.predict(X_teste)
            previsoes = np.maximum(
                np.expm1(previsoes_log), 0
            )

            metricas = calcular_metricas(y_teste, previsoes)

            baseline = np.full(
                len(y_teste),
                np.median(y_treino),
                dtype=float,
            )

            mae_baseline = mean_absolute_error(
                y_teste, baseline
            )

            resultados.append({
                "parte": numero_parte,
                "modelo": nome_modelo,
                "treino_registros": len(treino),
                "teste_registros": len(teste),
                **metricas,
                "MAE_baseline_mediana": mae_baseline,
            })

            print(
                f"Parte {numero_parte}/{N_PARTES} | "
                f"{nome_modelo:<22} | "
                f"MAE: R$ {metricas['MAE']:,.2f} | "
                f"R2: {metricas['R2']:.4f} | "
                f"MAPE: {metricas['MAPE_percentual']:.2f}%"
            )

    tabela = pd.DataFrame(resultados)

    print("\n[3] Calculando medias e desvios-padrao...")
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)

    tabela.to_csv(
        ARQUIVO_RESULTADOS,
        index=False,
        encoding="utf-8-sig",
        float_format="%.6f",
    )

    metricas = [
        "MAE",
        "RMSE",
        "R2",
        "MAPE_percentual",
        "MAE_baseline_mediana",
    ]

    resumo = (
        tabela.groupby("modelo")[metricas]
        .agg(["mean", "std"])
    )

    resumo.columns = [
        f"{metrica}_{estatistica}"
        for metrica, estatistica in resumo.columns
    ]

    resumo = resumo.reset_index()

    resumo.to_csv(
        ARQUIVO_RESUMO,
        index=False,
        encoding="utf-8-sig",
        float_format="%.6f",
    )

    print("\n[4] Resumo por algoritmo")
    colunas_exibicao = [
        "modelo",
        "MAE_mean",
        "RMSE_mean",
        "R2_mean",
        "MAPE_percentual_mean",
        "MAE_baseline_mediana_mean",
    ]

    print(
        resumo[colunas_exibicao].to_string(
            index=False,
            float_format=lambda valor: f"{valor:,.4f}",
        )
    )

    print("\n[5] Arquivos gerados:")
    print(ARQUIVO_RESULTADOS)
    print(ARQUIVO_RESUMO)

    print("\nComparacao de algoritmos concluida.")


if __name__ == "__main__":
    main()

