# Network Survey 2026

Aplicação em **Streamlit** para recolha de dados do questionário *Network Survey 2026*, com persistência em **Supabase**.

## Requisitos

- Python 3.10+
- Dependências em `requirements.txt`

## Instalação

1. Criar e ativar um ambiente virtual.
2. Instalar dependências:

```bash
pip install -r requirements.txt
```

## Configuração

A aplicação lê credenciais do Supabase via `st.secrets`.

Crie o ficheiro `.streamlit/secrets.toml` com:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_KEY = "SUA_CHAVE_SUPABASE"
```

## Executar localmente

```bash
streamlit run main.py
```

## Testes

```bash
pytest
```

## Estrutura do projeto

- `main.py` — aplicação principal Streamlit
- `requirements.txt` — dependências Python
- `tests/test_survey.py` — testes automáticos
