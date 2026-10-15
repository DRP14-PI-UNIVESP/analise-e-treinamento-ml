
from pathlib import Path
import json

import pandas as pd


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARQUIVO_ENTRADA = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "03_webmotors_ouro.parquet"
)

PASTA_RELATORIOS = (
    BASE_DIR
    / "data"
    / "ouro"
    / "webmotors"
    / "auditoria"
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def titulo(texto):
    print("\n" + "=" * 70)
    print(texto)
    print("=" * 70)


def salvar_csv(df, nome):
    caminho = PASTA_RELATORIOS / nome
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    print(f"Relatório salvo: {caminho}")


def mostrar_distribuicao(df, coluna, limite=15):
    if coluna not in df.columns:
        return

    print(f"\n{coluna} — valores mais frequentes:")
    print(
        df[coluna]
        .astype("string")
        .fillna("[AUSENTE]")
        .value_counts()
        .head(limite)
        .to_string()
    )


# ============================================================
# AUDITORIA
# ============================================================

def main():
    titulo("AUDITORIA EXPLORATÓRIA — TABELA OURO 2")

    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {ARQUIVO_ENTRADA}"
        )

    PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(ARQUIVO_ENTRADA)

    print(f"Arquivo: {ARQUIVO_ENTRADA}")
    print(f"Linhas: {len(df):,}")
    print(f"Colunas: {len(df.columns)}")
    print(f"Tamanho: {ARQUIVO_ENTRADA.stat().st_size / 1024:.2f} KB")

    if df.empty:
        raise ValueError("A tabela está vazia.")

    # --------------------------------------------------------
    # 1. INTEGRIDADE E ESTRUTURA
    # --------------------------------------------------------

    titulo("[1] INTEGRIDADE E ESTRUTURA")

    print(f"Linhas duplicadas integralmente: {df.duplicated().sum():,}")

    if "webmotors_id" in df.columns:
        print(
            "IDs ausentes:",
            int(df["webmotors_id"].isna().sum()),
        )
        print(
            "IDs duplicados:",
            int(df["webmotors_id"].duplicated().sum()),
        )
        print(
            "IDs únicos:",
            int(df["webmotors_id"].nunique()),
        )

    estrutura = pd.DataFrame({
        "coluna": df.columns,
        "tipo": [str(df[c].dtype) for c in df.columns],
        "valores_ausentes": [
            int(df[c].isna().sum()) for c in df.columns
        ],
        "percentual_ausente": [
            round(df[c].isna().mean() * 100, 2)
            for c in df.columns
        ],
        "valores_unicos": [
            int(df[c].nunique(dropna=True))
            for c in df.columns
        ],
    })

    estrutura = estrutura.sort_values(
        "percentual_ausente",
        ascending=False,
    )

    print("\nColunas com mais valores ausentes:")
    print(estrutura.head(15).to_string(index=False))

    salvar_csv(estrutura, "01_estrutura_e_ausentes.csv")

    constantes = estrutura[
        estrutura["valores_unicos"] <= 1
    ].copy()

    print("\nColunas com zero ou um valor distinto:")
    if constantes.empty:
        print("Nenhuma.")
    else:
        print(constantes.to_string(index=False))

    salvar_csv(constantes, "02_colunas_constantes.csv")

    # --------------------------------------------------------
    # 2. VALIDAÇÕES DE CONSISTÊNCIA
    # --------------------------------------------------------

    titulo("[2] CONSISTÊNCIA DOS DADOS")

    verificacoes = []

    def registrar(nome, quantidade, observacao=""):
        verificacoes.append({
            "verificacao": nome,
            "quantidade": int(quantidade),
            "observacao": observacao,
        })
        print(f"{nome}: {int(quantidade):,}")

    if "valor_anuncio" in df.columns:
        preco = pd.to_numeric(
            df["valor_anuncio"], errors="coerce"
        )
        registrar(
            "Preço ausente ou não numérico",
            preco.isna().sum(),
        )
        registrar(
            "Preço menor ou igual a zero",
            (preco.notna() & (preco <= 0)).sum(),
        )

    if "quilometragem" in df.columns:
        km = pd.to_numeric(
            df["quilometragem"], errors="coerce"
        )
        registrar(
            "Quilometragem negativa",
            (km.notna() & (km < 0)).sum(),
        )
        registrar(
            "Quilometragem ausente",
            km.isna().sum(),
        )

    if "ano_fabricacao" in df.columns:
        fabricacao = pd.to_numeric(
            df["ano_fabricacao"], errors="coerce"
        )
        registrar(
            "Ano de fabricação ausente",
            fabricacao.isna().sum(),
        )

    if {"ano_fabricacao", "ano_modelo"}.issubset(df.columns):
        fabricacao = pd.to_numeric(
            df["ano_fabricacao"], errors="coerce"
        )
        modelo = pd.to_numeric(
            df["ano_modelo"], errors="coerce"
        )
        registrar(
            "Ano-modelo anterior ao ano de fabricação",
            (modelo.notna() & fabricacao.notna()
             & (modelo < fabricacao)).sum(),
        )

    if {"idade_veiculo", "ano_modelo", "data_coleta"}.issubset(df.columns):
        ano_coleta = pd.to_datetime(
            df["data_coleta"], errors="coerce"
        ).dt.year
        ano_modelo = pd.to_numeric(
            df["ano_modelo"], errors="coerce"
        )
        idade_esperada = ano_coleta - ano_modelo
        idade = pd.to_numeric(
            df["idade_veiculo"], errors="coerce"
        )

        divergencia = (
            idade.notna()
            & idade_esperada.notna()
            & (idade != idade_esperada)
            & (idade_esperada >= 0)
        )
        registrar(
            "Idade divergente do cálculo esperado",
            divergencia.sum(),
        )

    salvar_csv(
        pd.DataFrame(verificacoes),
        "03_verificacoes_consistencia.csv",
    )

    # --------------------------------------------------------
    # 3. DISTRIBUIÇÃO DOS PREÇOS E QUILOMETRAGEM
    # --------------------------------------------------------

    titulo("[3] PREÇOS E QUILOMETRAGEM")

    numericas = [
        "valor_anuncio",
        "quilometragem",
        "ano_fabricacao",
        "ano_modelo",
        "idade_veiculo",
        "preco_por_km",
        "cilindrada",
        "potencia",
        "fipe_percent",
    ]

    disponiveis = [c for c in numericas if c in df.columns]

    resumo = df[disponiveis].describe(
        percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
    ).T

    print(resumo.round(2).to_string())
    salvar_csv(resumo.reset_index(names="variavel"), "04_resumo_numerico.csv")

    # Sinalizar extremos pelo intervalo interquartil.
    # É um alerta estatístico, não uma regra para excluir anúncios.
    alertas = []

    for coluna in [
        "valor_anuncio",
        "quilometragem",
        "preco_por_km",
    ]:
        if coluna not in df.columns:
            continue

        valores = pd.to_numeric(df[coluna], errors="coerce").dropna()

        if valores.empty:
            continue

        q1 = valores.quantile(0.25)
        q3 = valores.quantile(0.75)
        iqr = q3 - q1
        limite_inferior = q1 - 1.5 * iqr
        limite_superior = q3 + 1.5 * iqr

        mask = (
            pd.to_numeric(df[coluna], errors="coerce").lt(limite_inferior)
            | pd.to_numeric(df[coluna], errors="coerce").gt(limite_superior)
        )

        alertas.append({
            "variavel": coluna,
            "q1": q1,
            "q3": q3,
            "limite_inferior": limite_inferior,
            "limite_superior": limite_superior,
            "quantidade_alertas": int(mask.sum()),
        })

        print(
            f"\n{coluna}: {int(mask.sum())} valores fora "
            "dos limites de 1,5 × IQR."
        )
        if coluna == "valor_anuncio":
            colunas_exibicao = [
                c for c in [
                    "webmotors_id",
                    "nome_marca",
                    "nome_modelo",
                    "nome_versao",
                    "ano_modelo",
                    "quilometragem",
                    "valor_anuncio",
                    "cidade",
                ]
                if c in df.columns
            ]

            print(
                df.loc[mask, colunas_exibicao]
                .sort_values("valor_anuncio", ascending=False)
                .head(15)
                .to_string(index=False)
            )

    salvar_csv(
        pd.DataFrame(alertas),
        "05_alertas_valores_atipicos.csv",
    )

    # --------------------------------------------------------
    # 4. DISTRIBUIÇÕES CATEGÓRICAS
    # --------------------------------------------------------

    titulo("[4] DISTRIBUIÇÕES CATEGÓRICAS")

    categoricas = [
        "nome_marca",
        "nome_modelo",
        "nome_combustivel",
        "cambio",
        "carroceria",
        "estado",
        "cidade",
        "tipo_vendedor",
        "faixa_preco",
        "faixa_quilometragem",
    ]

    distribuicoes = []

    for coluna in categoricas:
        if coluna not in df.columns:
            continue

        mostrar_distribuicao(df, coluna)

        contagem = (
            df[coluna]
            .astype("string")
            .fillna("[AUSENTE]")
            .value_counts(dropna=False)
        )

        for categoria, quantidade in contagem.items():
            distribuicoes.append({
                "coluna": coluna,
                "categoria": str(categoria),
                "quantidade": int(quantidade),
                "percentual": round(
                    quantidade / len(df) * 100, 2
                ),
            })

    salvar_csv(
        pd.DataFrame(distribuicoes),
        "06_distribuicoes_categoricas.csv",
    )

    # --------------------------------------------------------
    # 5. DUPLICIDADES DE VEÍCULOS SEM ID
    # --------------------------------------------------------

    titulo("[5] POSSÍVEIS ANÚNCIOS SEMELHANTES")

    chaves = [
        "nome_marca",
        "nome_modelo",
        "ano_modelo",
        "quilometragem",
        "valor_anuncio",
        "cidade",
    ]

    chaves_disponiveis = [c for c in chaves if c in df.columns]

    if len(chaves_disponiveis) >= 4:
        candidatos = df[
            df.duplicated(
                subset=chaves_disponiveis,
                keep=False,
            )
        ].sort_values(chaves_disponiveis)

        print(
            "Linhas em grupos com características coincidentes:",
            len(candidatos),
        )

        if not candidatos.empty:
            print(candidatos.head(30).to_string(index=False))

        salvar_csv(
            candidatos,
            "07_possiveis_anuncios_semelhantes.csv",
        )
    else:
        print("Colunas insuficientes para essa verificação.")

    # --------------------------------------------------------
    # 6. RESUMO FINAL
    # --------------------------------------------------------

    titulo("[6] RESUMO FINAL")

    resumo_final = {
        "arquivo": str(ARQUIVO_ENTRADA),
        "linhas": int(len(df)),
        "colunas": int(len(df.columns)),
        "ids_unicos": (
            int(df["webmotors_id"].nunique())
            if "webmotors_id" in df.columns
            else None
        ),
        "linhas_duplicadas_integralmente": int(df.duplicated().sum()),
        "preco_minimo": (
            float(df["valor_anuncio"].min())
            if "valor_anuncio" in df.columns
            else None
        ),
        "preco_mediano": (
            float(df["valor_anuncio"].median())
            if "valor_anuncio" in df.columns
            else None
        ),
        "preco_maximo": (
            float(df["valor_anuncio"].max())
            if "valor_anuncio" in df.columns
            else None
        ),
        "relatorios": str(PASTA_RELATORIOS),
    }

    caminho_resumo = PASTA_RELATORIOS / "00_resumo_auditoria.json"

    with open(caminho_resumo, "w", encoding="utf-8") as arquivo:
        json.dump(
            resumo_final,
            arquivo,
            ensure_ascii=False,
            indent=4,
        )

    print(json.dumps(resumo_final, ensure_ascii=False, indent=4))
    print(f"\nRelatórios salvos em: {PASTA_RELATORIOS}")
    print("\nAUDITORIA CONCLUÍDA!")


if __name__ == "__main__":
    main()
