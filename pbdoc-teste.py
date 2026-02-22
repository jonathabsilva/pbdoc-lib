from pbdoc_lib import PBDocClient, LoginError

# Substitua pelas suas credenciais
USUARIO = "seu_usuario"
SENHA = "sua_senha"

def main():
    # Inicializa o cliente com contexto (abre e fecha automaticamente)
    with PBDocClient() as client:
        try:
            # Realiza login
            login_response = client.login(USUARIO, SENHA)
            print("Login:", login_response)

            # Acessa uma página autenticada
            # Exemplo de rota interna do PBDoc
            resposta_painel = client.get_authenticated_page("siga/public/app/principal")
            print("Status:", resposta_painel.status_code)
            print("Mensagem:", resposta_painel.message)
            print("Dados:", resposta_painel.data)

        except LoginError as exc:
            print(f"Falha no login: {exc}")
        except Exception as e:
            print("Erro inesperado:", e)

if __name__ == "__main__":
    main()