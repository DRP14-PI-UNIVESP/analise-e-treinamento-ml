# PI4 — Avaliador Inteligente de Veículos Usados

Projeto acadêmico que explora dados e aprendizado de máquina para estimar o
preço de veículos usados, combinando a **Tabela FIPE** (referência histórica)
com **anúncios da Webmotors** (preços anunciados).

> **Estado atual:** as pipelines de dados da FIPE e da Webmotors foram
> desenvolvidas em etapas separadas. Para a Webmotors há dados Bronze, Prata e
> Ouro, análises exploratórias e modelos experimentais treinados. A aplicação
> integrada (API, Back-end e Front-end) ainda precisa ser implementada.

## Relação com o restante do repositório

Esta pasta é **independente** de `backend/` e `frontend/`: tem seu próprio `README`,
`requirements.txt` e `.gitignore` e não altera nenhum arquivo do restante do projeto.
A integração dos modelos com a API é uma etapa futura, a combinar com o time: o formato dos
modelos e as variáveis usadas aqui são diferentes dos de `backend/app` e `backend/ml`.

## Objetivos

- Organizar e preparar dados de veículos para análise (arquitetura em camadas Bronze, Prata e Ouro).
- Explorar os dados históricos de referência da FIPE.
- Preparar anúncios da Webmotors e analisar os preços anunciados.
- Treinar e comparar modelos de regressão para estimar preços.
- Deixar uma base técnica para a futura integração com uma API e uma interface web.

## Fontes de dados

### FIPE

Base de referência de preços, usada em formato CSV (separado por tabulação).
O arquivo **não está neste repositório** por ser de terceiros e muito grande (~780 MB).

- **Origem:** `<LINK DO REPOSITÓRIO DE ORIGEM>` (preencher), baixado em `<DATA>`.
- **Licença da fonte:** `<CONFERIR NO REPOSITÓRIO DE ORIGEM>`.
- **Como usar:** baixe o arquivo `fipex-prices-latest.csv` e salve em `data/bronze/`.
- **Amostras incluídas (uma por camada):** 24.941 linhas, 30 códigos FIPE com histórico completo,
  sorteados com semente fixa (42). As camadas Prata e Ouro foram obtidas filtrando os mesmos 30
  códigos dos arquivos gerados pelo pipeline completo, então têm o mesmo esquema das originais.

  | Camada | Arquivo |
  |---|---|
  | Bronze | `data/bronze/fipex-prices-sample.csv` |
  | Prata | `data/prata/02_fipe_limpo_amostra.parquet` |
  | Ouro | `data/ouro/03_fipe_ouro_amostra.parquet` |

  As amostras servem para conhecer a estrutura dos dados e testar os scripts. Os resultados
  dos modelos da FIPE só são reproduzíveis com o CSV completo.

### Webmotors

Anúncios coletados por automação de navegador. São **preços anunciados, não preços
finais de venda**. A amostra atual tem **235 anúncios válidos**, concentrados em São Paulo
e em um único recorte de coleta, portanto é experimental e não representa todo o mercado.
Confira os termos de uso da Webmotors antes de redistribuir ou reutilizar esses dados.

## Estrutura do projeto

```text
analise_e_treinamento_de_machine_learning/
├── data/
│   ├── bronze/
│   │   ├── fipex-prices-sample.csv        # FIPE: amostra (o CSV completo fica fora do Git)
│   │   └── webmotors/01_anuncios_brutos.parquet
│   ├── prata/
│   │   ├── 02_fipe_limpo_amostra.parquet  # FIPE: amostra
│   │   └── webmotors/02_webmotors_limpo.parquet
│   ├── ouro/
│   │   ├── 03_fipe_ouro_amostra.parquet   # FIPE: amostra
│   │   └── webmotors/
│   │       ├── 03_webmotors_ouro.parquet
│   │       ├── auditoria/                 # diagnósticos e análises de erro
│   │       └── modelagem/                 # métricas, previsões e comparações
│   │           └── final/                 # modelos treinados na etapa 26
│   └── auditorias/                        # saídas de auditoria da FIPE (geradas, fora do Git)
├── pipelines/                             # etapas 01 a 18 (FIPE)
│   └── webmotors/                         # etapas 01 a 06 e 19 a 26 (Webmotors)
├── .gitignore
├── README.md
└── requirements.txt
```

## Pipelines

### FIPE (`pipelines/`)

| Etapas | Responsabilidade |
|---|---|
| `01` a `06` | Diagnóstico do CSV, preparação da camada Prata e auditorias (código FIPE, temporal, distância temporal, validação final) |
| `07` a `10` | Preparação da camada Ouro e auditorias de idade, valores e categorias |
| `11` a `18` | Diagnóstico e preparação para ML: auditorias temporais e de duplicidade, normalização de features e divisão treino/teste |

Observações: vários scripts usam caminhos relativos (`data/...`), então **execute-os a
partir da raiz do projeto**. Os scripts `04` e `05` gravam seus CSVs de auditoria em
`data/prata/`; esses arquivos são grandes e ficam fora do Git.

### Webmotors (`pipelines/webmotors/`)

| Script | Responsabilidade |
|---|---|
| `01_coleta_webmotors.py` | Coleta e diagnóstico da fonte |
| `02_validacao_brutos_webmotors.py` | Validação dos dados brutos |
| `03_preparacao_prata_webmotors.py` | Limpeza e padronização (Prata) |
| `04_preparacao_ouro_webmotors.py` | Preparação para análise e modelagem (Ouro) |
| `05_auditoria_ouro_webmotors.py` | Auditoria dos dados Ouro |
| `06_teste_paginacao_webmotors.py` | Teste de paginação da coleta |
| `19_treinamento_webmotors.py` | Modelo inicial |
| `20_treinamento_webmotors_log.py` | Treinamento com transformação logarítmica do alvo |
| `21_diagnostico_categorias.py` | Diagnóstico da representação de categorias |
| `22_cruzamento_erros_categorias.py` | Cruzamento entre erros e frequência das categorias |
| `23_validacao_cruzada.py` | Validação cruzada |
| `24_analise_erros_faixa_preco.py` | Análise dos erros por faixa de preço |
| `25_comparacao_algoritmos.py` | Comparação de algoritmos |
| `26_treinamento_final.py` | Treinamento final dos candidatos |

Exemplo (PowerShell, a partir desta pasta, com o ambiente ativado):

```powershell
python -u .\pipelines\webmotors\25_comparacao_algoritmos.py
python -u .\pipelines\webmotors\26_treinamento_final.py
```

Cada script depende dos arquivos de saída dos anteriores. A coleta (`01`) pode falhar por
mecanismos antirrobô do site: as tentativas de diagnóstico retornaram páginas bloqueadas.
Por isso o repositório inclui os dados já coletados.

## Modelos de aprendizado de máquina

Três algoritmos comparados com validação cruzada de cinco partes:

- HistGradientBoostingRegressor
- RandomForestRegressor
- ExtraTreesRegressor

O alvo `valor_anuncio` foi transformado com `log1p` nos experimentos com transformação logarítmica.

### Resultados médios da validação cruzada

| Algoritmo | MAE médio | RMSE médio | R² médio | MAPE médio |
|---|---:|---:|---:|---:|
| ExtraTrees | R$ 61.568,58 | R$ 182.575,11 | 0,5277 | 23,19% |
| HistGradientBoosting | R$ 63.017,31 | R$ 193.505,95 | 0,5449 | 23,28% |
| RandomForest | R$ 63.753,27 | R$ 193.292,48 | 0,5229 | 28,55% |

São resultados experimentais da amostra atual. O ExtraTrees teve menor MAE e RMSE médios;
o HistGradientBoosting teve maior R² médio. As diferenças não permitem afirmar que um modelo
será sempre superior em dados futuros.

### Modelos da etapa 26

Gravados em `data/ouro/webmotors/modelagem/final/`:

- `26_modelo_histgradientboosting.joblib`
- `26_modelo_extratrees.joblib`
- `26_resumo_treinamento.json`

Cada `.joblib` contém o estimador, o codificador categórico, as medianas usadas para
preencher valores numéricos ausentes e a ordem das variáveis. **Carregue arquivos
serializados apenas de fontes confiáveis.**

## Como preparar o ambiente

No PowerShell, a partir desta pasta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt
```

Para executar a coleta, instale também o navegador do Playwright:
`python -m playwright install chromium`.

## Próximas etapas

- [ ] Fixar no `requirements.txt` as versões de scikit-learn, joblib, duckdb e playwright.
- [ ] Testar a instalação e os comandos em um ambiente limpo.
- [ ] Criar a etapa de inferência (características do veículo → estimativa de preço).
- [ ] Definir o contrato da API com o Back-end: entrada, resposta e tratamento de erros.
- [ ] Integrar a API ao Front-end.
- [ ] Validar os modelos com anúncios novos, que não participaram do treinamento.
- [ ] Definir como a referência FIPE será apresentada junto aos preços anunciados.
- [ ] Criar testes de integração e documentar as limitações do sistema.

## Limitações conhecidas

- A amostra da Webmotors tem apenas 235 anúncios válidos, de um único recorte, concentrados em São Paulo.
- Preço anunciado não é necessariamente preço efetivo de venda.
- Há poucos exemplos para algumas combinações de marca e modelo.
- Os erros são maiores em algumas faixas de preço, especialmente entre veículos de luxo.
- O treinamento final usa todos os registros disponíveis; métricas calculadas nesses mesmos
  registros não estimam a generalização.
- O sistema ainda precisa de validação externa e de integração com a aplicação.

---

Projeto acadêmico — PI4: Avaliador Inteligente de Veículos Usados.
