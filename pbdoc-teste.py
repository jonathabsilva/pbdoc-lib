import os
from dotenv import load_dotenv

from pbdoc_lib.client import PBDocClient
from pbdoc_lib.config import PBDocConfig
from pbdoc_lib.exceptions import LoginError


# Carrega o .env
load_dotenv()


def main():
    usuario = os.getenv("PBDOC_USER")
    senha = os.getenv("PBDOC_PASSWORD")

    if not usuario or not senha:
        raise ValueError("Variáveis PBDOC_USER ou PBDOC_PASSWORD não definidas no .env")

    processo = "CBMOFN202602317A"

    config = PBDocConfig(headless=True)
    config.timeout_seconds = 60

    with PBDocClient(config=config) as client:
        try:
            # 1️⃣ Login
            resp_login = client.login(usuario, senha)
            print(resp_login.message)
            print("URL após login:", resp_login.data["current_url"])

            # 2️⃣ Consulta estruturada do processo
            resp = client.consult_process(processo)

            print("\n=== Consulta do Processo ===")
            print("Processo:", processo)
            print("URL:", resp.data["url"])
            print("Título:", resp.data["title"])

            dados = resp.data["parsed"]

            print("\n--- Dados Estruturados ---")
            print("Sigla:", dados.get("sigla"))
            print("ID Interno:", dados.get("id_interno"))
            print("Situação:", dados.get("situacao"))

            doc = dados.get("documento_interno_normalizado", {})
            print("\n--- Documento Interno ---")
            print("Data:", doc.get("data"))
            print("De:", doc.get("de"))
            print("Para:", doc.get("para"))
            print("Assunto:", doc.get("assunto"))

            print("\n--- Movimentações ---")
            for mov in dados.get("movimentacoes", []):
                print(
                    f"{mov.get('tempo_absoluto')} | "
                    f"{mov.get('lotacao_sigla')} | "
                    f"{mov.get('evento')}"
                )

            input("\nPressione ENTER para fechar o navegador...")

        except LoginError as e:
            print("Falha no login:", e)
            input("\nPressione ENTER para fechar o navegador...")


if __name__ == "__main__":
    main()