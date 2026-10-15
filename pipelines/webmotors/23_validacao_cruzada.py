
from pathlib import Path
import json

import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingRegressor
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

ARQUIVO_METRICAS = DIR_SAIDA / "23_validacao_cruzada.csv"
ARQUIVO_RESUMO = DIR_SAIDA / "23_resumo_validacao_cruzada.json"

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
# PREPARACAO
# ============================================================

def preparar_categoricas(treino, teste):
    treino = treino.copy()
    teste = teste.copy()

    for coluna in CATEGORICAS:
        treino[coluna] = (
            treino[coluna]
            .fillna("__AUSENTE__")
            .astype(str)
        )
        teste[coluna] = (
            teste[coluna]
            .fillna("__AUSENTE__")
            .astype(str)
        )

    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        dtype=np.float64,
    )

    treino_cat = encoder.fit_transform(treino[CATEGORICAS])
    teste_cat = encoder.transform(teste[CATEGORICAS])

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

    mascara = real != 0

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
    print("ETAPA 23 - VALIDACAO CRUZADA DO MODELO WEBMOTORS")
    print("=" * 70)

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo Ouro nao encontrado: {ARQUIVO_ENTRADA}"
        )

    print("\n[1] Carregando dados Ouro...")
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
    print(f"Partes da validacao: {N_PARTES}")

    if len(df) < N_PARTES:
        raise ValueError("Dados insuficientes para validacao cruzada.")

    print("\n[2] Executando os cinco testes...")

    kfold = KFold(
        n_splits=N_PARTES,
        shuffle=True,
        random_state=SEMENTE,
    )

    resultados = []

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

        previsoes_log = modelo.predict(X_teste)
        previsoes = np.maximum(
            np.expm1(previsoes_log), 0
        )

        previsao_mediana = np.full(
            len(y_teste),
            np.median(y_treino),
            dtype=float,
        )

        mae = mean_absolute_error(y_teste, previsoes)
        rmse = np.sqrt(
            mean_squared_error(y_teste, previsoes)
        )
        r2 = r2_score(y_teste, previsoes)
        mape = calcular_mape(y_teste, previsoes)

        mae_mediana = mean_absolute_error(
            y_teste, previsao_mediana
        )

        resultados.append({
            "parte": numero_parte,
            "treino_registros": len(treino),
            "teste_registros": len(teste),
            "MAE": mae,
            "MAE_baseline_mediana": mae_mediana,
            "RMSE": rmse,
            "R2": r2,
            "MAPE_percentual": mape,
        })

        print(
            f"Parte {numero_parte}/{N_PARTES} | "
            f"MAE: R$ {mae:,.2f} | "
            f"RMSE: R$ {rmse:,.2f} | "
            f"R2: {r2:.4f} | "
            f"MAPE: {mape:.2f}%"
        )

    print("\n[3] Salvando resultados...")

    DIR_SAIDA.mkdir(parents=True, exist_ok=True)

    tabela = pd.DataFrame(resultados)
    tabela.to_csv(
        ARQUIVO_METRICAS,
        index=False,
        encoding="utf-8-sig",
        float_format="%.6f",
    )

    metricas = [
        "MAE",
        "MAE_baseline_mediana",
        "RMSE",
        "R2",
        "MAPE_percentual",
    ]

    resumo = {
        "registros_validos": int(len(df)),
        "partes": N_PARTES,
        "semente": SEMENTE,
        "metodo": "KFold com embaralhamento e alvo log1p",
        "media": {
            coluna: float(tabela[coluna].mean())
            for coluna in metricas
        },
        "desvio_padrao": {
            coluna: float(tabela[coluna].std(ddof=1))
            for coluna in metricas
        },
    }

    with open(ARQUIVO_RESUMO, "w", encoding="utf-8") as arquivo:
        json.dump(
            resumo,
            arquivo,
            ensure_ascii=False,
            indent=4,
        )

    print("\n[4] Resumo das cinco partes")
    print(
        tabela[metricas].mean().to_string(
            float_format=lambda valor: f"{valor:,.4f}"
        )
    )

    print("\n[5] Arquivos gerados:")
    print(ARQUIVO_METRICAS)
    print(ARQUIVO_RESUMO)

    print("\nValidacao cruzada concluida.")


if __name__ == "__main__":
    main()
