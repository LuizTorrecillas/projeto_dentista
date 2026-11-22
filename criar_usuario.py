"""Cria um usuário para entrar no sistema.

Uso (com o venv ativado, dentro da pasta do projeto):
    python criar_usuario.py
"""
import getpass
import sqlite3
import sys

from autenticacao import gerar_hash_senha
from banco import criar_tabelas, inserir_usuario

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
