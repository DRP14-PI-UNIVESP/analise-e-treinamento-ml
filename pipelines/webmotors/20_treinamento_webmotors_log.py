from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder

warnings.filterwarnings("ignore", category=UserWarning)


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

PASTA_SAIDA = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "modelagem"
)

ARQUIVO_MODELO = PASTA_SAIDA / "20_modelo_webmotors_log.joblib"
ARQUIVO_ENCODER = PASTA_SAIDA / "20_encoder_webmotors_log.joblib"
ARQUIVO_METRICAS = PASTA_SAIDA / "20_metricas_webmotors_log.json"
ARQUIVO_PREVISOES = PASTA_SAIDA / "20_previsoes_teste_log.csv"

ALVO = "valor_anuncio"
TEST_SIZE = 0.20
RANDOM_STATE = 42


# ============================================================
# FUNCOES AUXILIARES
# ============================================================

def calcular_mape(y_real, y_previsto):
    """Calcula o erro percentual absoluto medio."""
    y_real = np.asarray(y_real, dtype=float)
    y_previsto = np.asarray(y_previsto, dtype=float)

    mascara = y_real != 0

    if not mascara.any():
        return None

    return float(
        np.mean(
            np.abs(
                (y_real[mascara] - y_previsto[mascara])
                / y_real[mascara]
            )
        ) * 100
    )


# ============================================================
# EXECUCAO PRINCIPAL
# ============================================================

def main():

    print("=" * 70)
    print("MODELO 20 - WEBMOTORS COM TRANSFORMACAO LOGARITMICA")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Carregar dados
    # --------------------------------------------------------

    print("\n[1] Carregando tabela Ouro...")

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo nao encontrado: {ARQUIVO_ENTRADA}"
        )

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(ARQUIVO_ENTRADA)

    if ALVO not in df.columns:
        raise ValueError(
            f"A coluna-alvo '{ALVO}' nao existe na tabela Ouro."
        )

    df[ALVO] = pd.to_numeric(df[ALVO], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=[ALVO]).copy()
    df = df[df[ALVO] > 0].copy()

    print(f"Registros validos: {len(df):,}")
    print(f"Colunas disponiveis: {len(df.columns)}")

    if len(df) < 20:
        raise ValueError(
            "Quantidade insuficiente de registros para treinamento."
        )

    # --------------------------------------------------------
    # 2. Selecionar atributos
    # --------------------------------------------------------

    print("\n[2] Selecionando atributos...")

    candidatas_categoricas = [
        "nome_marca",
        "marca",
        "nome_modelo",
        "modelo",
        "nome_combustivel",
        "cambio",
        "carroceria",
        "tipo_vendedor",
        "cidade",
        "bairro",
        "tracao",
    ]

    candidatas_numericas = [
        "ano_fabricacao",
        "ano_modelo",
        "idade_veiculo",
        "quilometragem",
        "potencia",
        "cilindrada",
        "valor_fipe",
    ]

    colunas_excluidas = {
        ALVO,
        "faixa_preco",
        "fipe_percent",
        "preco_por_km",
        "good_deal",
        "UniqueId",
        "unique_id",
        "id",
        "url",
        "descricao",
        "atributos_veiculo",
        "data_coleta",
        "estado",
        "leilao",
    }

    categoricas = [
        c for c in candidatas_categoricas
        if c in df.columns and c not in colunas_excluidas
    ]

    numericas = [
        c for c in candidatas_numericas
        if c in df.columns and c not in colunas_excluidas
    ]

    atributos = categoricas + numericas

    if not atributos:
        raise ValueError("Nenhum atributo preditor foi encontrado.")

    print("Atributos categoricos:", categoricas)
    print("Atributos numericos:", numericas)
    print("Total de atributos:", len(atributos))

    # --------------------------------------------------------
    # 3. Preparar X e y
    # --------------------------------------------------------

    print("\n[3] Preparando os dados...")

    X = df[atributos].copy()
    y = df[ALVO].astype(float).copy()

    for coluna in numericas:
        X[coluna] = pd.to_numeric(
            X[coluna],
            errors="coerce",
        )

        X[coluna] = X[coluna].replace(
            [np.inf, -np.inf],
            np.nan,
        )

    for coluna in categoricas:
        X[coluna] = (
            X[coluna]
            .astype("string")
            .fillna("NAO_INFORMADO")
            .astype(str)
        )

    # --------------------------------------------------------
    # 4. Dividir treino e teste
    # --------------------------------------------------------

    print("\n[4] Dividindo treino e teste...")

    indices_treino, indices_teste = train_test_split(
        X.index,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    X_treino = X.loc[indices_treino].copy()
    X_teste = X.loc[indices_teste].copy()

    y_treino = y.loc[indices_treino].copy()
    y_teste = y.loc[indices_teste].copy()

    print(f"Treino: {len(X_treino):,} registros")
    print(f"Teste: {len(X_teste):,} registros")

    # --------------------------------------------------------
    # 5. Codificar atributos categoricos
    # --------------------------------------------------------

    print("\n[5] Codificando categorias...")

    encoder = None

    if categoricas:
        encoder = OrdinalEncoder(
            handle_unknown="use_encoded_value",
            unknown_value=-1,
            dtype=np.float64,
        )

        treino_cat = pd.DataFrame(
            encoder.fit_transform(X_treino[categoricas]),
            columns=categoricas,
            index=X_treino.index,
        )

        teste_cat = pd.DataFrame(
            encoder.transform(X_teste[categoricas]),
            columns=categoricas,
            index=X_teste.index,
        )

    else:
        treino_cat = pd.DataFrame(index=X_treino.index)
        teste_cat = pd.DataFrame(index=X_teste.index)

    # --------------------------------------------------------
    # 6. Tratar valores numericos ausentes
    # --------------------------------------------------------

    print("\n[6] Tratando valores ausentes...")

    treino_num = X_treino[numericas].copy()
    teste_num = X_teste[numericas].copy()

    # As medianas sao calculadas somente com os dados de treino.
    medianas = treino_num.median().fillna(0)

    treino_num = treino_num.fillna(medianas)
    teste_num = teste_num.fillna(medianas)

    X_treino_final = pd.concat(
        [treino_num, treino_cat],
        axis=1,
    )

    X_teste_final = pd.concat(
        [teste_num, teste_cat],
        axis=1,
    )

    X_teste_final = X_teste_final[X_treino_final.columns]

    # --------------------------------------------------------
    # 7. Transformacao logaritmica do alvo
    # --------------------------------------------------------

    print("\n[7] Aplicando log1p ao preco...")

    y_treino_log = np.log1p(y_treino)

    print("Alvo de treinamento: log1p(valor_anuncio)")

    # --------------------------------------------------------
    # 8. Treinar modelo
    # --------------------------------------------------------

    print("\n[8] Treinando o modelo...")

    modelo = HistGradientBoostingRegressor(
        max_iter=100,
        learning_rate=0.05,
        max_leaf_nodes=7,
        min_samples_leaf=15,
        loss="squared_error",
        random_state=RANDOM_STATE,
        early_stopping=False,
    )

    modelo.fit(
        X_treino_final,
        y_treino_log,
    )

    print("Treinamento concluido.")
    print(f"Iteracoes realizadas: {modelo.n_iter_}")

    # --------------------------------------------------------
    # 9. Prever e reverter o logaritmo
    # --------------------------------------------------------

    print("\n[9] Gerando previsoes...")

    previsoes_log = modelo.predict(X_teste_final)

    # Reverte log1p para obter valores em reais.
    y_previsto = np.expm1(previsoes_log)

    # Evita valores negativos previstos.
    y_previsto = np.maximum(y_previsto, 0)

    y_real = y_teste.to_numpy(dtype=float)

    # --------------------------------------------------------
    # 10. Calcular metricas
    # --------------------------------------------------------

    print("\n[10] Calculando metricas...")

    mae = float(
        mean_absolute_error(y_real, y_previsto)
    )

    rmse = float(
        np.sqrt(mean_squared_error(y_real, y_previsto))
    )

    r2 = float(
        r2_score(y_real, y_previsto)
    )

    mape = calcular_mape(y_real, y_previsto)

    # Baseline: prever sempre a mediana do treino.
    previsao_baseline = np.full(
        len(y_teste),
        float(y_treino.median()),
    )

    mae_baseline = float(
        mean_absolute_error(y_real, previsao_baseline)
    )

    metricas = {
        "experimento": "Modelo 20 - alvo logaritmico",
        "arquivo_entrada": str(ARQUIVO_ENTRADA),
        "variavel_alvo": ALVO,
        "transformacao_alvo": "log1p",
        "reversao_previsoes": "expm1",
        "registros_validos": int(len(df)),
        "registros_treino": int(len(X_treino)),
        "registros_teste": int(len(X_teste)),
        "quantidade_atributos": int(len(atributos)),
        "atributos_categoricos": categoricas,
        "atributos_numericos": numericas,
        "random_state": RANDOM_STATE,
        "mae": mae,
        "mae_baseline_mediana": mae_baseline,
        "rmse": rmse,
        "r2": r2,
        "mape_percentual": mape,
        "iteracoes_realizadas": int(modelo.n_iter_),
    }

    # --------------------------------------------------------
    # 11. Salvar previsoes
    # --------------------------------------------------------

    print("\n[11] Salvando previsoes...")

    previsoes = pd.DataFrame({
        "indice_original": X_teste.index,
        "valor_real": y_real,
        "valor_previsto": y_previsto,
    })

    previsoes["erro_absoluto"] = np.abs(
        previsoes["valor_real"]
        - previsoes["valor_previsto"]
    )

    previsoes["erro_percentual"] = np.where(
        previsoes["valor_real"] != 0,
        (
            previsoes["erro_absoluto"]
            / previsoes["valor_real"]
        ) * 100,
        np.nan,
    )

    colunas_identificacao = [
        c for c in [
            "nome_marca",
            "nome_modelo",
            "ano_fabricacao",
            "ano_modelo",
            "quilometragem",
            "cidade",
            "UniqueId",
            "unique_id",
            "id",
        ]
        if c in df.columns
    ]

    identificacao = df.loc[
        previsoes["indice_original"],
        colunas_identificacao,
    ].reset_index(drop=True)

    previsoes = pd.concat(
        [
            previsoes.reset_index(drop=True),
            identificacao,
        ],
        axis=1,
    )

    previsoes = previsoes.sort_values(
        "erro_absoluto",
        ascending=False,
    )

    previsoes.to_csv(
        ARQUIVO_PREVISOES,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # 12. Salvar modelo, encoder e metricas
    # --------------------------------------------------------

    print("\n[12] Salvando modelo, encoder e metricas...")

    joblib.dump(
        modelo,
        ARQUIVO_MODELO,
    )

    joblib.dump(
        {
            "encoder": encoder,
            "colunas_categoricas": categoricas,
            "colunas_numericas": numericas,
            "colunas_modelo": list(X_treino_final.columns),
            "medianas_numericas": medianas.to_dict(),
            "transformacao_alvo": "log1p",
        },
        ARQUIVO_ENCODER,
    )

    with open(
        ARQUIVO_METRICAS,
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            metricas,
            arquivo,
            ensure_ascii=False,
            indent=4,
        )

    # --------------------------------------------------------
    # 13. Resumo final
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("RESULTADO DO MODELO 20 - LOGARITMICO")
    print("=" * 70)

    print(f"MAE:                    R$ {mae:,.2f}")
    print(f"MAE baseline (mediana): R$ {mae_baseline:,.2f}")
    print(f"RMSE:                   R$ {rmse:,.2f}")
    print(f"R2:                     {r2:.4f}")

    if mape is not None:
        print(f"MAPE:                   {mape:.2f}%")
    else:
        print("MAPE: nao calculado")

    print("\nArquivos gerados:")
    print(f"Modelo:    {ARQUIVO_MODELO}")
    print(f"Encoder:   {ARQUIVO_ENCODER}")
    print(f"Metricas:  {ARQUIVO_METRICAS}")
    print(f"Previsoes: {ARQUIVO_PREVISOES}")

    print("\n15 maiores erros absolutos:")

    colunas_exibicao = [
        c for c in [
            "nome_marca",
            "nome_modelo",
            "ano_modelo",
            "valor_real",
            "valor_previsto",
            "erro_absoluto",
        ]
        if c in previsoes.columns
    ]

    print(
        previsoes[colunas_exibicao]
        .head(15)
        .to_string(index=False)
    )

    print("\nExperimento concluido.")


if __name__ == "__main__":
    main()