"""Restaura um backup do banco da clínica.

Uso (dentro da pasta do projeto, com o SERVIDOR PARADO):
    .venv/bin/python restaurar_backup.py                 # lista os backups disponíveis
    .venv/bin/python restaurar_backup.py backups/clinica_2026-11-22_2230.db

Antes de sobrescrever, o banco atual é copiado para
backups/antes_de_restaurar_AAAA-MM-DD_HHMMSS.db (fora do rodízio automático),
para que dê para desfazer a restauração.
"""
import sys
from datetime import datetime
from pathlib import Path

from backup import PASTA_PADRAO, banco_integro, copiar_banco, listar_backups
from banco import caminho_banco


def restaurar(arquivo_backup, destino=None, pasta=PASTA_PADRAO, agora=None):
    """Copia o backup sobre o banco atual. Devolve o caminho da cópia de segurança (ou None)."""
    arquivo_backup = Path(arquivo_backup)
    destino = Path(destino or caminho_banco())
    if not arquivo_backup.exists():
        raise FileNotFoundError(f"Backup não encontrado: {arquivo_backup}")
    if not banco_integro(arquivo_backup):
        raise RuntimeError(f"O arquivo {arquivo_backup} está corrompido ou não é um banco SQLite.")

    copia_seguranca = None
    if destino.exists():
        pasta = Path(pasta)
        pasta.mkdir(mode=0o700, parents=True, exist_ok=True)
        copia_seguranca = pasta / f"antes_de_restaurar_{(agora or datetime.now()):%Y-%m-%d_%H%M%S}.db"
        copiar_banco(destino, copia_seguranca)

    # A API de backup também serve para restaurar: copia o backup PARA o banco atual.
    copiar_banco(arquivo_backup, destino)
    return copia_seguranca


def main():
    if len(sys.argv) != 2:
        backups = listar_backups()
        if not backups:
            print("Nenhum backup encontrado na pasta backups/.")
        else:
            print("Backups disponíveis (do mais antigo para o mais recente):")
            for arquivo in backups:
                print(f"  {arquivo.relative_to(Path.cwd()) if arquivo.is_relative_to(Path.cwd()) else arquivo}")
        print("\nUso: python restaurar_backup.py CAMINHO_DO_BACKUP")
        sys.exit(1)

    arquivo_backup = Path(sys.argv[1])
    destino = caminho_banco()
    print(f"Backup a restaurar: {arquivo_backup}")
    print(f"Banco que será SOBRESCRITO: {destino}")
    print("Pare o servidor (uvicorn) antes de continuar.")
    print("O banco atual será guardado em backups/antes_de_restaurar_*.db.")
    resposta = input('Digite RESTAURAR para confirmar: ')
    if resposta.strip() != "RESTAURAR":
        print("Cancelado. Nada foi alterado.")
        sys.exit(1)

    try:
        copia = restaurar(arquivo_backup, destino)
    except Exception as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        sys.exit(1)
    if copia:
        print(f"Banco anterior guardado em: {copia}")
    print("Backup restaurado com sucesso. Pode subir o servidor de novo.")


if __name__ == "__main__":
    main()
