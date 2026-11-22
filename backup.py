"""Faz um backup do banco da clínica, seguro mesmo com o servidor rodando.

Uso (dentro da pasta do projeto):
    .venv/bin/python backup.py               # mantém os 14 mais recentes
    .venv/bin/python backup.py --manter 30

Por que não usar `cp clinica.db ...`? Se o servidor estiver gravando no exato
momento da cópia, o cp pode copiar metade antiga e metade nova, gerando um
arquivo corrompido. A API de backup do SQLite (Connection.backup) copia de
forma consistente, coordenando com as travas do próprio banco.
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import config
from banco import caminho_banco

config.carregar_env()

PASTA_PADRAO = Path(__file__).resolve().parent / "backups"
PREFIXO = "clinica_"          # só arquivos com este prefixo entram no rodízio
MANTER_PADRAO = 14


def copiar_banco(origem, destino):
    """Copia o banco `origem` para o arquivo `destino` usando a API de backup."""
    conexao_origem = sqlite3.connect(origem)
    try:
        conexao_destino = sqlite3.connect(destino)
        try:
            conexao_origem.backup(conexao_destino)
        finally:
            conexao_destino.close()
    finally:
        conexao_origem.close()


def banco_integro(caminho):
    """True se o SQLite considera o arquivo íntegro (PRAGMA integrity_check)."""
    try:
        conexao = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
        try:
            return conexao.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            conexao.close()
    except sqlite3.DatabaseError:
        return False


def listar_backups(pasta=PASTA_PADRAO):
    """Backups do rodízio, do mais antigo para o mais recente.

    O nome tem a data no formato AAAA-MM-DD_HHMM, então a ordem alfabética
    já é a ordem cronológica.
    """
    pasta = Path(pasta)
    if not pasta.exists():
        return []
    return sorted(pasta.glob(f"{PREFIXO}*.db"))


def apagar_antigos(pasta, manter):
    backups = listar_backups(pasta)
    excedentes = backups[:-manter] if len(backups) > manter else []
    for arquivo in excedentes:
        arquivo.unlink()
    return excedentes


def fazer_backup(origem=None, pasta=PASTA_PADRAO, manter=MANTER_PADRAO, agora=None):
    """Gera backups/clinica_AAAA-MM-DD_HHMM.db e apaga os mais antigos além de `manter`."""
    if manter < 1:
        raise ValueError("É preciso manter pelo menos 1 backup.")
    origem = origem or caminho_banco()
    if not Path(origem).exists():
        raise FileNotFoundError(f"Banco não encontrado: {origem}")

    pasta = Path(pasta)
    # 0o700: só o dono do arquivo acessa a pasta (os backups têm dados de pacientes)
    pasta.mkdir(mode=0o700, parents=True, exist_ok=True)

    nome = f"{PREFIXO}{(agora or datetime.now()).strftime('%Y-%m-%d_%H%M')}.db"
    destino = pasta / nome
    temporario = pasta / (nome + ".tmp")

    # Grava primeiro num arquivo temporário e só renomeia se estiver íntegro.
    # Assim um backup interrompido no meio nunca fica com cara de backup válido.
    temporario.unlink(missing_ok=True)
    try:
        copiar_banco(origem, temporario)
        if not banco_integro(temporario):
            raise RuntimeError("O backup gerado não passou na verificação de integridade.")
        os.chmod(temporario, 0o600)
        os.replace(temporario, destino)
    finally:
        temporario.unlink(missing_ok=True)

    apagados = apagar_antigos(pasta, manter)
    return destino, apagados


def main():
    manter_env = int(os.environ.get("CLINICA_BACKUPS_MANTER", MANTER_PADRAO))
    parser = argparse.ArgumentParser(description="Backup do banco da clínica.")
    parser.add_argument("--manter", type=int, default=manter_env,
                        help=f"quantos backups manter (padrão: {manter_env})")
    parser.add_argument("--pasta", default=str(PASTA_PADRAO), help="pasta dos backups")
    args = parser.parse_args()

    try:
        destino, apagados = fazer_backup(pasta=args.pasta, manter=args.manter)
    except Exception as erro:
        # Saída com código 1: o cron registra a falha (e manda e-mail, se configurado)
        print(f"[{datetime.now():%Y-%m-%d %H:%M}] ERRO no backup: {erro}", file=sys.stderr)
        sys.exit(1)

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Backup criado: {destino}")
    for arquivo in apagados:
        print(f"  backup antigo removido: {arquivo.name}")


if __name__ == "__main__":
    main()
