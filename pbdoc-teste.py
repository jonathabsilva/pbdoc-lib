import os
from dotenv import load_dotenv

from pbdoc_lib.client import PBDocClient
from pbdoc_lib.config import PBDocConfig
from pbdoc_lib.exceptions import LoginError


# Carrega o .env
load_dotenv()

def main():
    # Lê variáveis do ambiente
    usuario = os.getenv("PBDOC_USER")
    senha = os.getenv("PBDOC_PASSWORD")

    if not usuario or not senha:
        raise ValueError("Variáveis PBDOC_USER ou PBDOC_PASSWORD não definidas no .env")

    # Chrome visível (debug)
    config = PBDocConfig(headless=True)
    config.timeout_seconds = 60

    with PBDocClient(config=config) as client:
        try:
            resp = client.login(usuario, senha)
            print(resp.message)
            print("URL atual:", resp.data["current_url"])

            input("\nPressione ENTER para fechar o navegador...")

        except LoginError as e:
            print("Falha no login:", e)
            input("\nPressione ENTER para fechar o navegador...")


if __name__ == "__main__":
    main()