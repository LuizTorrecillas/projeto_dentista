"""Configurações lidas de variáveis de ambiente (ou do arquivo .env).

Segredos (como a chave da sessão) não ficam no código: o código vai para o GitHub,
o .env não (está no .gitignore). Veja .env.example para a lista de variáveis.
"""
import os
from pathlib import Path

_PASTA_DO_PROJETO = Path(__file__).resolve().parent


def carregar_env(caminho=_PASTA_DO_PROJETO / ".env"):
    """Lê linhas CHAVE=VALOR do .env para os.environ.

    Não sobrescreve variáveis que já existem no ambiente: assim dá para
    trocar um valor na hora, por exemplo CLINICA_COOKIE_SECURE=true uvicorn ...
    """
    arquivo = Path(caminho)
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def chave_secreta():
    chave = os.environ.get("CLINICA_CHAVE_SECRETA", "")
    if len(chave) < 32:
        raise RuntimeError(
            "CLINICA_CHAVE_SECRETA ausente ou curta demais (mínimo 32 caracteres).\n"
            "Copie .env.example para .env e gere uma chave com:\n"
            "  python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    return chave


def cookie_seguro():
    """True só quando o sistema é servido por HTTPS (senão o navegador não envia o cookie)."""
    valor = os.environ.get("CLINICA_COOKIE_SECURE", "false")
    return valor.strip().lower() in ("1", "true", "sim", "yes")


def duracao_sessao_segundos():
    horas = float(os.environ.get("CLINICA_SESSAO_HORAS", "8"))
    return int(horas * 3600)
