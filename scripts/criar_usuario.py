"""Cria um usuário para entrar no sistema.

Uso (com o venv ativado, na raiz do projeto):
    python -m scripts.criar_usuario
"""
import getpass
import sqlite3
import sys
from pathlib import Path

# Permite rodar tanto "python -m scripts.X" quanto "python scripts/X.py":
# no segundo caso o Python não enxerga a pasta app/, então a adicionamos.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.persistencia.banco import criar_tabelas, inserir_usuario  # noqa: E402
from app.seguranca.autenticacao import gerar_hash_senha  # noqa: E402

TAMANHO_MINIMO_SENHA = 10


def main():
    criar_tabelas()

    nome = input("Nome de usuário: ").strip()
    if not nome:
        sys.exit("O nome de usuário não pode ser vazio.")

    # getpass não mostra o que é digitado (nem guarda no histórico do terminal)
    senha = getpass.getpass("Senha (não aparece enquanto digita): ")
    if len(senha) < TAMANHO_MINIMO_SENHA:
        sys.exit(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.")
    if getpass.getpass("Repita a senha: ") != senha:
        sys.exit("As senhas não conferem. Nada foi criado.")

    try:
        inserir_usuario(nome, gerar_hash_senha(senha))
    except sqlite3.IntegrityError:
        sys.exit(f"Já existe um usuário chamado '{nome}'.")
    print(f"Usuário '{nome}' criado com sucesso.")


if __name__ == "__main__":
    main()
