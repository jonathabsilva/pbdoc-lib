# pbdoc-lib

Biblioteca Python reutilizável para automação do **PBDoc** com Selenium em modo headless, desenhada para ser usada como se fosse uma API (retornos padronizados e fluxo encapsulado).

## O que já está pronto

- Cliente `PBDocClient` com ciclo de vida controlado (`start`, `close`, `with`)
- Login inicial no endereço:
  - `https://pbdoc.pb.gov.br/siga/public/app/login`
- Respostas padronizadas no formato `ApiLikeResponse`
- Configuração centralizada de URL, timeout e seletores (`PBDocConfig`)
- Base para adicionar novas funcionalidades com `run_step` e `get_authenticated_page`
- Consulta de processo com leitura de local atual, tramitações e dados do documento

## Estrutura

```text
pbdoc-lib/
├── pyproject.toml
├── README.md
├── src/
│   └── pbdoc_lib/
│       ├── __init__.py
│       ├── client.py
│       ├── config.py
│       ├── exceptions.py
│       └── models.py
└── tests/
    └── test_config.py
```

## Instalação local

```bash
pip install -e .
```

## Uso básico

```python
from pbdoc_lib import PBDocClient, LoginError

USUARIO = "USUARIO"
SENHA = "Senha"
NUMPROCESSO = "NUM"

with PBDocClient() as client:
    try:
        # 1️⃣ Login
        login_response = client.login(USUARIO, SENHA)
        print("Login:", login_response.message)

        # 2️⃣ Teste básico de página autenticada
        painel = client.get_authenticated_page("siga/public/app/principal")
        print("Painel:", painel.status_code, painel.message)

        # 3️⃣ Consulta processo (exemplo real)
        processo = client.consult_process(NUMPROCESSO)

        parsed = processo.data["parsed"]

        print("\n=== Processo ===")
        print("Sigla:", parsed.get("sigla"))
        print("Situação:", parsed.get("situacao"))

        print("\nMovimentações:")
        for mov in parsed.get("movimentacoes", []):
            print(
                f"{mov.get('tempo_absoluto')} | "
                f"{mov.get('lotacao_sigla')} | "
                f"{mov.get('evento')}"
            )

    except LoginError as exc:
        print(f"Falha no login: {exc}")
```

## Como integrar em outros sistemas 

A ideia é tratar a automação como um adaptador externo:

```python
from pbdoc_lib import PBDocClient


def buscar_dados_pbdoc(user: str, password: str) -> dict:
    with PBDocClient() as client:
        client.login(user, password)
        resposta = client.get_authenticated_page("siga/public/app/principal")
        return resposta.data
```

Depois você pode chamar essa função dentro do seu serviço sem duplicar lógica de Selenium.

## Próximos passos

1. Mapear os fluxos como “endpoints internos” (ex.: listar documentos, aprovar, anexar).
2. Ajustar seletores em `PBDocSelectors` se o layout do PBDoc mudar.
3. Adicionar testes com mocks de Selenium para cada novo fluxo.

## Observação importante

Para rodar o Selenium com Chrome, você precisa ter:

- Google Chrome (ou Chromium) instalado.
- ChromeDriver compatível (ou Selenium Manager resolvendo automaticamente).
