
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
)
from sklearn.preprocessing import OrdinalEncoder


# ============================================================
# CONFIGURACAO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_ENTRADA = (
    BASE_DIR / "data" / "ouro" / "webmotors"
    / "03_webmotors_ouro.parquet"
)

DIR_SAIDA = (
    BASE_DIR / "data" / "ouro" / "webmotors"
    / "modelagem" / "final"
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
    print("ETAPA 26 - TREINAMENTO FINAL WEBMOTORS")
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

    if df.empty:
        raise ValueError("Nenhum registro valido para treinamento.")

    print(f"Registros validos: {len(df)}")
    print(f"Variaveis categoricas: {len(CATEGORICAS)}")
    print(f"Variaveis numericas: {len(NUMERICAS)}")

    # --------------------------------------------------------
    # Preparacao categorica
    # --------------------------------------------------------

    print("\n[2] Preparando variaveis...")

    dados_cat = df[CATEGORICAS].copy()

    for coluna in CATEGORICAS:
        dados_cat[coluna] = (
            dados_cat[coluna]
            .fillna("__AUSENTE__")
            .astype(str)
        )

    encoder = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        dtype=np.float64,
    )

    X_cat = encoder.fit_transform(dados_cat)

    # --------------------------------------------------------
    # Preparacao numerica
    # --------------------------------------------------------

    dados_num = df[NUMERICAS].apply(
        pd.to_numeric, errors="coerce"
    )

    medianas = dados_num.median().fillna(0)
    dados_num = dados_num.fillna(medianas)

    X_num = dados_num.to_numpy(dtype=np.float64)

    X = np.column_stack([X_cat, X_num])
    y = df[ALVO].to_numpy(dtype=float)
    y_log = np.log1p(y)

    print(f"Matriz final: {X.shape}")
    print("Alvo transformado com log1p.")

    DIR_SAIDA.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # Treinamento dos candidatos
    # --------------------------------------------------------

    print("\n[3] Treinando os modelos com todos os registros...")

    resumo = {
        "etapa": 26,
        "arquivo_fonte": str(ARQUIVO_ENTRADA),
        "registros_treinamento": int(len(df)),
        "alvo": ALVO,
        "transformacao_alvo": "log1p",
        "variaveis_categoricas": CATEGORICAS,
        "variaveis_numericas": NUMERICAS,
        "ordem_features": CATEGORICAS + NUMERICAS,
        "observacao": (
            "Treinamento com todos os registros validos. "
            "Metricas de treino nao representam desempenho "
            "em dados novos."
        ),
        "modelos": {},
    }

    for nome, modelo in criar_modelos().items():
        print(f"\nTreinando: {nome}")

        modelo.fit(X, y_log)

        caminho_modelo = (
            DIR_SAIDA / f"26_modelo_{nome.lower()}.joblib"
        )

        joblib.dump(
            {
                "modelo": modelo,
                "encoder": encoder,
                "medianas_numericas": medianas.to_dict(),
                "variaveis_categoricas": CATEGORICAS,
                "variaveis_numericas": NUMERICAS,
                "ordem_features": CATEGORICAS + NUMERICAS,
                "transformacao_alvo": "log1p",
                "registros_treinamento": int(len(df)),
            },
            caminho_modelo,
        )

        resumo["modelos"][nome] = {
            "arquivo": str(caminho_modelo),
            "algoritmo": type(modelo).__name__,
            "parametros": modelo.get_params(),
        }

        print(f"Modelo salvo: {caminho_modelo}")

    # --------------------------------------------------------
    # Registro da execucao
    # --------------------------------------------------------

    caminho_resumo = DIR_SAIDA / "26_resumo_treinamento.json"

    with open(caminho_resumo, "w", encoding="utf-8") as arquivo:
        json.dump(
            resumo,
            arquivo,
            ensure_ascii=False,
            indent=4,
            default=str,
        )

    print("\n[4] Arquivos finais gerados:")
    for arquivo in sorted(DIR_SAIDA.iterdir()):
        if arquivo.is_file():
            print(arquivo)

    print("\nTreinamento final concluido.")
    print(
        "Importante: os modelos foram treinados com todos os dados; "
        "nao use metricas calculadas nesses mesmos dados como "
        "estimativa de generalizacao."
    )


if __name__ == "__main__":
    main()
