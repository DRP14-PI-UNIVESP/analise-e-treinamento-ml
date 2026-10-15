
from pathlib import Path

import duckdb
import pandas as pd
from sklearn.model_selection import train_test_split


# ============================================================
# CONFIGURACAO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_OURO = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "03_webmotors_ouro.parquet"
)

DIRETORIO_SAIDA = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "auditoria"
)

ARQUIVO_SAIDA = (
    DIRETORIO_SAIDA
    / "21_diagnostico_categorias.csv"
)

COLUNAS_CATEGORICAS = [
    "nome_marca",
    "nome_modelo",
]

TEST_SIZE = 0.20
RANDOM_STATE = 42


# ============================================================
# EXECUCAO
# ============================================================

def main():
    print("=" * 70)
    print("DIAGNOSTICO DE CATEGORIAS — WEBMOTORS")
    print("=" * 70)

    if not ARQUIVO_OURO.exists():
        raise FileNotFoundError(
            f"Arquivo Ouro nao encontrado: {ARQUIVO_OURO}"
        )

    # 1. Carregar os dados
    print("\n[1] Carregando tabela Ouro...")

    with duckdb.connect() as con:
        df = con.execute(
            """
            SELECT *
            FROM read_parquet(?)
            WHERE valor_anuncio IS NOT NULL
              AND valor_anuncio > 0
            """,
            [str(ARQUIVO_OURO)],
        ).df()

    print(f"Registros validos: {len(df)}")

    # 2. Conferir colunas necessarias
    necessarias = COLUNAS_CATEGORICAS + ["valor_anuncio"]
    ausentes = [c for c in necessarias if c not in df.columns]

    if ausentes:
        raise ValueError(
            f"Colunas ausentes na tabela Ouro: {ausentes}"
        )

    # 3. Reproduzir a divisao do Modelo 20
    print("\n[2] Reproduzindo divisao treino/teste...")

    indices = list(range(len(df)))
    indices_treino, indices_teste = train_test_split(
        indices,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    treino = df.iloc[indices_treino].copy()
    teste = df.iloc[indices_teste].copy()

    print(f"Treino: {len(treino)} registros")
    print(f"Teste:  {len(teste)} registros")

    # 4. Normalizar nomes apenas para contar categorias
    # Os dados originais nao sao modificados.
    def normalizar(serie):
        return (
            serie.astype("string")
            .fillna("NAO_INFORMADO")
            .str.strip()
            .str.upper()
        )

    for coluna in COLUNAS_CATEGORICAS:
        treino[coluna] = normalizar(treino[coluna])
        teste[coluna] = normalizar(teste[coluna])

    # 5. Contagens no treino
    print("\n[3] Calculando frequencias no treino...")

    contagens_marca = treino["nome_marca"].value_counts()
    contagens_modelo = treino["nome_modelo"].value_counts()

    # O modelo e identificado pela combinacao marca + modelo.
    contagens_combinacao = (
        treino.groupby(["nome_marca", "nome_modelo"])
        .size()
    )

    # 6. Diagnosticar cada categoria presente no teste
    print("\n[4] Analisando categorias do conjunto de teste...")

    linhas = []

    for _, registro in teste.iterrows():
        marca = registro["nome_marca"]
        modelo = registro["nome_modelo"]

        qtd_marca = int(contagens_marca.get(marca, 0))
        qtd_modelo = int(contagens_modelo.get(modelo, 0))
        qtd_combinacao = int(
            contagens_combinacao.get((marca, modelo), 0)
        )

        if qtd_combinacao == 0:
            situacao = "MARCA_MODELO_NAO_VISTOS"
        elif qtd_combinacao == 1:
            situacao = "APENAS_1_EXEMPLO_NO_TREINO"
        elif qtd_combinacao < 5:
            situacao = "POCOS_EXEMPLOS_NO_TREINO"
        else:
            situacao = "MAIOR_REPRESENTACAO"

        linhas.append(
            {
                "nome_marca": marca,
                "nome_modelo": modelo,
                "valor_anuncio": float(registro["valor_anuncio"]),
                "quantidade_marca_treino": qtd_marca,
                "quantidade_modelo_treino": qtd_modelo,
                "quantidade_marca_modelo_treino": qtd_combinacao,
                "diagnostico": situacao,
            }
        )

    resultado = pd.DataFrame(linhas)

    # 7. Resumo
    print("\n[5] Resumo das categorias no teste...")

    resumo = (
        resultado["diagnostico"]
        .value_counts()
        .rename_axis("diagnostico")
        .reset_index(name="quantidade")
    )

    print(resumo.to_string(index=False))

    sem_exemplos = resultado[
        resultado["quantidade_marca_modelo_treino"] == 0
    ]

    print(
        "\nVeiculos de teste cuja combinacao marca/modelo "
        f"nao aparece no treino: {len(sem_exemplos)}"
    )

    if not sem_exemplos.empty:
        print("\nCategorias ausentes no treino:")
        print(
            sem_exemplos[
                [
                    "nome_marca",
                    "nome_modelo",
                    "valor_anuncio",
                ]
            ]
            .sort_values("valor_anuncio", ascending=False)
            .to_string(index=False)
        )

    # 8. Salvar diagnostico
    DIRETORIO_SAIDA.mkdir(parents=True, exist_ok=True)

    resultado.to_csv(
        ARQUIVO_SAIDA,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[6] Diagnostico salvo:")
    print(ARQUIVO_SAIDA)
    print("\nDiagnostico concluido.")


if __name__ == "__main__":
    main()
