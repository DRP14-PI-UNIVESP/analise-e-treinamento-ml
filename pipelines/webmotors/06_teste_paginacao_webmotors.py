from pathlib import Path
from datetime import datetime
import json

from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parents[2]

URL = "https://www.webmotors.com.br/carros-usados/sp?page=3"

DIR = (
    BASE_DIR
    / "data"
    / "bronze"
    / "webmotors"
    / "diagnostico"
)


def main():
    pasta = DIR / (
        "teste_paginacao_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    pasta.mkdir(parents=True, exist_ok=True)

    respostas = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(locale="pt-BR")

        def capturar(response):
            if "/api/search/car" not in response.url:
                return

            item = {
                "url": response.url,
                "status": response.status,
            }

            try:
                data = response.json()
                item["data"] = data

                if isinstance(data, dict):
                    item["total"] = data.get("Count")
                    item["anuncios"] = len(
                        data.get("SearchResults", [])
                    )
                    item["paginacao"] = data.get("Pagination")

                    print(
                        "API:",
                        response.status,
                        "| anúncios:",
                        item["anuncios"],
                        "| paginação:",
                        item["paginacao"],
                    )

            except Exception as erro:
                item["erro_json"] = str(erro)

            respostas.append(item)

        page.on("response", capturar)

        try:
            print("=" * 60)
            print("TESTE DE PAGINAÇÃO — WEBMOTORS")
            print("=" * 60)
            print("Página solicitada: 3")
            print("URL configurada:", URL)

            page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=120000,
            )

            print("URL aberta:", page.url)

            page.wait_for_timeout(12000)

            print(
                "Respostas de API capturadas:",
                len(respostas),
            )

        except Exception as erro:
            print("Erro durante a coleta:", repr(erro))

        finally:
            arquivo = pasta / "teste_pagina_3.json"

            arquivo.write_text(
                json.dumps(
                    respostas,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            print("Diagnóstico salvo em:", arquivo)

            input("Pressione ENTER para fechar o navegador...")
            browser.close()


if __name__ == "__main__":
    main()