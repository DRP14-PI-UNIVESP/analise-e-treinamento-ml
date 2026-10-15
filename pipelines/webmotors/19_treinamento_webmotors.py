from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import OrdinalEncoder


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_DADOS = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "03_webmotors_ouro.parquet"
)

DIR_RESULTADOS = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "modelagem"
)

ARQUIVO_MODELO = (
    DIR_RESULTADOS / "19_modelo_webmotors.joblib"
)

ARQUIVO_ENCODER = (
    DIR_RESULTADOS / "19_encoder_webmotors.joblib"
)

ARQUIVO_METRICAS = (
    DIR_RESULTADOS / "19_metricas_webmotors.json"
)

ARQUIVO_PREVISOES = (
    DIR_RESULTADOS / "19_previsoes_teste.csv"
)


# ============================================================
# CONFIGURAÇÃO DO MODELO
# ============================================================

TEST_SIZE = 0.20
RANDOM_STATE = 42

MAX_ITER = 100
LEARNING_RATE = 0.05
MAX_LEAF_NODES = 7
MIN_SAMPLES_LEAF = 15


# ============================================================
# VARIÁVEL-ALVO E PREDITORAS
# ============================================================

TARGET = "valor_anuncio"

CATEGORICAS_CANDIDATAS = [
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

NUMERICAS_CANDIDATAS = [
    "ano_fabricacao",
    "ano_modelo",
    "idade_veiculo",
    "quilometragem",
    "potencia",
    "cilindrada",
    "valor_fipe",
]

# Não utilizar informações que identifiquem diretamente
# o anúncio ou que derivem do próprio preço-alvo.
COLUNAS_EXCLUIDAS = {
    TARGET,
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


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def formatar_reais(valor):
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


# ============================================================
# INÍCIO
# ============================================================

print("=" * 70)
print("TREINAMENTO — MODELO WEBMOTORS")
print("=" * 70)

DIR_RESULTADOS.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# LEITURA
# ============================================================

print("\n[1] Carregando Tabela Ouro...")

if not ARQUIVO_DADOS.exists():
    raise FileNotFoundError(
        f"Arquivo não encontrado: {ARQUIVO_DADOS}"
    )

df = pd.read_parquet(ARQUIVO_DADOS)

print(f"Arquivo: {ARQUIVO_DADOS}")
print(f"Registros: {len(df):,}".replace(",", "."))
print(f"Colunas: {len(df.columns)}")

if TARGET not in df.columns:
    raise ValueError(
        f"Variável-alvo '{TARGET}' não encontrada."
    )

# Índice estável para relacionar cada previsão
# ao anúncio original, mesmo após a divisão treino/teste.
df = df.reset_index(drop=True)


# ============================================================
# VALIDAÇÃO DO ALVO
# ============================================================

print("\n[2] Validando preços...")

df[TARGET] = pd.to_numeric(
    df[TARGET],
    errors="coerce",
)

df = df.loc[
    df[TARGET].notna()
    & (df[TARGET] > 0)
].copy()

if len(df) < 30:
    raise ValueError(
        "Poucos registros válidos para treino e teste."
    )

print(f"Registros com preço válido: {len(df)}")
print(f"Preço mínimo: {formatar_reais(df[TARGET].min())}")
print(f"Preço máximo: {formatar_reais(df[TARGET].max())}")


# ============================================================
# SELEÇÃO DAS FEATURES
# ============================================================

print("\n[3] Selecionando variáveis...")

features_categoricas = [
    coluna
    for coluna in CATEGORICAS_CANDIDATAS
    if coluna in df.columns
    and coluna not in COLUNAS_EXCLUIDAS
]

features_numericas = [
    coluna
    for coluna in NUMERICAS_CANDIDATAS
    if coluna in df.columns
    and coluna not in COLUNAS_EXCLUIDAS
]

features = (
    features_categoricas
    + features_numericas
)

if not features:
    raise ValueError(
        "Nenhuma variável preditora foi encontrada."
    )

if not features_numericas:
    raise ValueError(
        "Nenhuma variável numérica foi encontrada."
    )

print("\nVariáveis categóricas:")
for coluna in features_categoricas:
    print(f" - {coluna}")

print("\nVariáveis numéricas:")
for coluna in features_numericas:
    print(f" - {coluna}")

print(f"\nTotal de preditoras: {len(features)}")
print(f"Alvo: {TARGET}")


# ============================================================
# PREPARAÇÃO DOS DADOS
# ============================================================

print("\n[4] Preparando os dados...")

# Preserva todos os registros e índices originais.
X = df[features].copy()
y = df[TARGET].astype(np.float64).copy()

for coluna in features_categoricas:
    X[coluna] = (
        X[coluna]
        .astype("string")
        .fillna("Não informado")
        .astype(str)
    )

for coluna in features_numericas:
    X[coluna] = pd.to_numeric(
        X[coluna],
        errors="coerce",
    )

    X[coluna] = X[coluna].replace(
        [np.inf, -np.inf],
        np.nan,
    )

print(f"Registros utilizados: {len(X)}")
print(
    "Valores ausentes nas preditoras: "
    f"{int(X.isna().sum().sum())}"
)


# ============================================================
# DIVISÃO TREINO / TESTE
# ============================================================

print("\n[5] Separando treino e teste...")

X_treino, X_teste, y_treino, y_teste = (
    train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )
)

print(f"Treino: {len(X_treino)}")
print(f"Teste:  {len(X_teste)}")


# ============================================================
# CODIFICAÇÃO DAS CATEGORIAS
# ============================================================

print("\n[6] Codificando categorias...")

encoder = OrdinalEncoder(
    handle_unknown="use_encoded_value",
    unknown_value=-1,
    dtype=np.float64,
)

if features_categoricas:
    X_treino_cat = encoder.fit_transform(
        X_treino[features_categoricas]
    )

    X_teste_cat = encoder.transform(
        X_teste[features_categoricas]
    )

    for i, coluna in enumerate(features_categoricas):
        quantidade = len(
            encoder.categories_[i]
        )

        print(
            f" - {coluna}: {quantidade} categorias"
        )
else:
    X_treino_cat = np.empty(
        (len(X_treino), 0)
    )

    X_teste_cat = np.empty(
        (len(X_teste), 0)
    )


# ============================================================
# FEATURES NUMÉRICAS
# ============================================================

print("\n[7] Preparando variáveis numéricas...")

X_treino_num = X_treino[
    features_numericas
].to_numpy(dtype=np.float64)

X_teste_num = X_teste[
    features_numericas
].to_numpy(dtype=np.float64)


# ============================================================
# COMBINAÇÃO DAS MATRIZES
# ============================================================

print("\n[8] Montando matrizes...")

X_treino_final = np.column_stack(
    [
        X_treino_cat,
        X_treino_num,
    ]
)

X_teste_final = np.column_stack(
    [
        X_teste_cat,
        X_teste_num,
    ]
)

y_treino_array = y_treino.to_numpy()
y_teste_array = y_teste.to_numpy()

print(
    f"Matriz de treino: {X_treino_final.shape}"
)

print(
    f"Matriz de teste:  {X_teste_final.shape}"
)


# ============================================================
# MODELO
# ============================================================

print("\n[9] Criando modelo...")

modelo = HistGradientBoostingRegressor(
    max_iter=MAX_ITER,
    learning_rate=LEARNING_RATE,
    max_leaf_nodes=MAX_LEAF_NODES,
    min_samples_leaf=MIN_SAMPLES_LEAF,
    loss="squared_error",
    random_state=RANDOM_STATE,
    early_stopping=False,
)

print(f"max_iter: {MAX_ITER}")
print(f"learning_rate: {LEARNING_RATE}")
print(f"max_leaf_nodes: {MAX_LEAF_NODES}")
print(f"min_samples_leaf: {MIN_SAMPLES_LEAF}")


# ============================================================
# TREINAMENTO
# ============================================================

print("\n[10] Treinando modelo...")

modelo.fit(
    X_treino_final,
    y_treino_array,
)

print("Treinamento concluído.")
print(
    f"Iterações utilizadas: {modelo.n_iter_}"
)


# ============================================================
# PREVISÕES
# ============================================================

print("\n[11] Realizando previsões...")

previsoes = modelo.predict(
    X_teste_final
)

# Evita preços previstos negativos.
previsoes = np.maximum(
    previsoes,
    0,
)

print("Previsões concluídas.")


# ============================================================
# MÉTRICAS
# ============================================================

print("\n[12] Calculando métricas...")

mae = mean_absolute_error(
    y_teste_array,
    previsoes,
)

rmse = np.sqrt(
    mean_squared_error(
        y_teste_array,
        previsoes,
    )
)

r2 = r2_score(
    y_teste_array,
    previsoes,
)

mape = np.mean(
    np.abs(
        (y_teste_array - previsoes)
        / y_teste_array
    )
) * 100

# Referência: prever sempre a mediana dos preços de treino.
previsao_mediana = np.full(
    len(y_teste_array),
    np.median(y_treino_array := y_treino.to_numpy()),
)

mae_mediana = mean_absolute_error(
    y_teste_array,
    previsao_mediana,
)


# ============================================================
# RESULTADOS DAS MÉTRICAS
# ============================================================

print("\n" + "=" * 70)
print("RESULTADOS — MODELO WEBMOTORS")
print("=" * 70)

print(f"\nMAE do modelo:  {formatar_reais(mae)}")
print(f"MAE da mediana: {formatar_reais(mae_mediana)}")
print(f"RMSE:           {formatar_reais(rmse)}")
print(f"R²:             {r2:.4f}")
print(f"MAPE:           {mape:.2f}%")

print("\nReferência:")
print(
    "O modelo deve ser comparado com a previsão "
    "constante baseada na mediana do treino."
)


# ============================================================
# PREVISÕES COM IDENTIFICAÇÃO DOS ANÚNCIOS
# ============================================================

print("\n[13] Identificando anúncios com maiores erros...")

exemplos = pd.DataFrame(
    {
        "valor_real": y_teste_array,
        "valor_previsto": previsoes,
    },
    index=y_teste.index,
)

# Recupera características dos anúncios originais.
colunas_identificacao = [
    coluna
    for coluna in [
        "UniqueId",
        "nome_marca",
        "nome_modelo",
        "ano_fabricacao",
        "ano_modelo",
        "quilometragem",
        "nome_combustivel",
        "valor_fipe",
    ]
    if coluna in df.columns
]

for coluna in colunas_identificacao:
    exemplos[coluna] = df.loc[
        exemplos.index,
        coluna,
    ]

exemplos["erro_absoluto"] = (
    exemplos["valor_real"]
    - exemplos["valor_previsto"]
).abs()

exemplos["erro_percentual"] = (
    exemplos["erro_absoluto"]
    / exemplos["valor_real"]
) * 100

# Organiza as colunas para facilitar a leitura.
colunas_resultado = (
    colunas_identificacao
    + [
        "valor_real",
        "valor_previsto",
        "erro_absoluto",
        "erro_percentual",
    ]
)

exemplos = exemplos[
    colunas_resultado
]

print("\n15 maiores erros absolutos:")

print(
    exemplos.sort_values(
        "erro_absoluto",
        ascending=False,
    )
    .head(15)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# SALVAMENTO DOS ARQUIVOS
# ============================================================

print("\n[14] Salvando resultados...")

joblib.dump(
    modelo,
    ARQUIVO_MODELO,
)

joblib.dump(
    {
        "encoder": encoder,
        "features": features,
        "features_categoricas": features_categoricas,
        "features_numericas": features_numericas,
    },
    ARQUIVO_ENCODER,
)

exemplos.to_csv(
    ARQUIVO_PREVISOES,
    index=False,
    encoding="utf-8-sig",
)

metricas = {
    "modelo": "HistGradientBoostingRegressor",
    "variavel_alvo": TARGET,
    "quantidade_registros": int(len(df)),
    "quantidade_treino": int(len(X_treino)),
    "quantidade_teste": int(len(X_teste)),
    "features": features,
    "mae": float(mae),
    "mae_referencia_mediana": float(mae_mediana),
    "rmse": float(rmse),
    "r2": float(r2),
    "mape_percentual": float(mape),
    "iteracoes_utilizadas": int(modelo.n_iter_),
    "random_state": RANDOM_STATE,
    "max_iter": MAX_ITER,
    "learning_rate": LEARNING_RATE,
    "max_leaf_nodes": MAX_LEAF_NODES,
    "min_samples_leaf": MIN_SAMPLES_LEAF,
}

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

print(f"\nModelo:    {ARQUIVO_MODELO}")
print(f"Encoder:   {ARQUIVO_ENCODER}")
print(f"Métricas:  {ARQUIVO_METRICAS}")
print(f"Previsões: {ARQUIVO_PREVISOES}")

print("\n" + "=" * 70)
print("MODELAGEM WEBMOTORS FINALIZADA")
print("=" * 70)
