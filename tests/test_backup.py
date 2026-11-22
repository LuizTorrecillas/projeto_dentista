import sqlite3
from datetime import datetime, timedelta

import pytest

from app.persistencia import banco
from scripts import backup, restaurar_backup


def nomes_pacientes(caminho):
    conexao = sqlite3.connect(caminho)
    try:
        return [linha[0] for linha in conexao.execute("SELECT nome FROM pacientes ORDER BY nome")]
    finally:
        conexao.close()


def test_backup_gera_arquivo_integro_com_os_dados(banco_temporario, tmp_path):
    banco.inserir_paciente("Ana", "11111111111", "61")
    pasta = tmp_path / "backups"

    destino, apagados = backup.fazer_backup(pasta=pasta, agora=datetime(2026, 11, 22, 22, 30))

    assert destino == pasta / "clinica_2026-11-22_2230.db"
    assert destino.exists()
    assert apagados == []
    assert backup.banco_integro(destino)
    assert nomes_pacientes(destino) == ["Ana"]
    assert not list(pasta.glob("*.tmp"))          # nada de arquivo temporário sobrando
    assert oct(destino.stat().st_mode & 0o777) == oct(0o600)


def test_backup_respeita_o_limite_de_arquivos(banco_temporario, tmp_path):
    pasta = tmp_path / "backups"
    pasta.mkdir()
    (pasta / "antes_de_restaurar_2026-01-01_000000.db").write_text("fora do rodízio")
    (pasta / "backup.log").write_text("log")
    inicio = datetime(2026, 11, 1, 22, 30)

    for dia in range(5):
        backup.fazer_backup(pasta=pasta, manter=3, agora=inicio + timedelta(days=dia))

    restantes = [arquivo.name for arquivo in backup.listar_backups(pasta)]
    assert restantes == ["clinica_2026-11-03_2230.db",
                         "clinica_2026-11-04_2230.db",
                         "clinica_2026-11-05_2230.db"]
    # arquivos que não são do rodízio ficam intocados
    assert (pasta / "antes_de_restaurar_2026-01-01_000000.db").exists()
    assert (pasta / "backup.log").exists()


def test_backup_com_escrita_em_andamento_copia_so_o_que_foi_confirmado(banco_temporario, tmp_path):
    banco.inserir_paciente("Confirmado", "11111111111", "61")
    conexao = sqlite3.connect(banco_temporario)
    conexao.execute("BEGIN IMMEDIATE")      # simula o servidor no meio de uma gravação
    conexao.execute("INSERT INTO pacientes (nome, cpf) VALUES ('Pela Metade', '2')")
    try:
        destino, _ = backup.fazer_backup(pasta=tmp_path / "backups")
    finally:
        conexao.rollback()
        conexao.close()
    assert backup.banco_integro(destino)
    assert nomes_pacientes(destino) == ["Confirmado"]


def test_backup_recusa_manter_zero(tmp_path):
    with pytest.raises(ValueError):
        backup.fazer_backup(pasta=tmp_path / "b", manter=0)


def test_backup_de_banco_inexistente_falha(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup.fazer_backup(origem=tmp_path / "nao_existe.db", pasta=tmp_path / "b")


def test_restaurar_volta_os_dados_e_guarda_o_banco_atual(banco_temporario, tmp_path):
    pasta = tmp_path / "backups"
    banco.inserir_paciente("Ana", "11111111111", "61")
    arquivo_backup, _ = backup.fazer_backup(pasta=pasta)
    banco.inserir_paciente("Depois Do Backup", "22222222222", "61")

    copia = restaurar_backup.restaurar(arquivo_backup, pasta=pasta)

    assert nomes_pacientes(banco_temporario) == ["Ana"]
    assert copia.name.startswith("antes_de_restaurar_")
    assert nomes_pacientes(copia) == ["Ana", "Depois Do Backup"]


def test_restaurar_arquivo_corrompido_nao_mexe_no_banco(banco_temporario, tmp_path):
    banco.inserir_paciente("Ana", "11111111111", "61")
    corrompido = tmp_path / "corrompido.db"
    corrompido.write_bytes(b"isto nao e um banco sqlite" * 100)

    with pytest.raises(RuntimeError):
        restaurar_backup.restaurar(corrompido, pasta=tmp_path / "backups")
    assert nomes_pacientes(banco_temporario) == ["Ana"]
