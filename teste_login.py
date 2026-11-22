"""Testes provisórios do item 3 (serão convertidos para pytest no item 4).
Usam um banco temporário: o clinica.db real NÃO é tocado."""
import os, sqlite3, tempfile

import banco
_caminho = os.path.join(tempfile.mkdtemp(), "teste.db")
_original = sqlite3.connect
banco.sqlite3 = type("S", (), {"connect": staticmethod(lambda _: _original(_caminho)),
                                "IntegrityError": sqlite3.IntegrityError})
banco.criar_tabelas()

import autenticacao as a

# hash: com sal, verificável, e nunca contém a senha
h1, h2 = a.gerar_hash_senha("senha-secreta-1"), a.gerar_hash_senha("senha-secreta-1")
assert h1 != h2, "sal diferente a cada hash"
assert "senha-secreta-1" not in h1
assert a.verificar_senha("senha-secreta-1", h1)
assert not a.verificar_senha("senha-errada", h1)
assert not a.verificar_senha("x", "lixo"), "hash malformado não quebra"
adulterado = h1[:-2] + ("00" if h1[-2:] != "00" else "11")
assert not a.verificar_senha("senha-secreta-1", adulterado)

# usuário no banco
banco.inserir_usuario("Recepcao", a.gerar_hash_senha("senha-secreta-1"))
try:
    banco.inserir_usuario("recepcao", "x"); raise SystemExit("duplicado deveria falhar")
except sqlite3.IntegrityError:
    pass  # COLLATE NOCASE: maiúsculas não criam outro usuário
assert a.autenticar("recepcao", "senha-secreta-1")["nome_usuario"] == "Recepcao"
assert a.autenticar("Recepcao", "errada") is None
assert a.autenticar("ninguem", "senha-secreta-1") is None
assert "senha_hash" not in a.autenticar("Recepcao", "senha-secreta-1"), "hash não sai do módulo"

# limitador, com relógio falso
agora = [0.0]
lim = a.LimitadorDeTentativas(max_falhas=3, janela=60, bloqueio=300, relogio=lambda: agora[0])
for _ in range(2): lim.registrar_falha("u")
assert not lim.esta_bloqueado("u")
lim.registrar_falha("u")
assert lim.esta_bloqueado("u"), "3a falha bloqueia"
agora[0] = 299; assert lim.esta_bloqueado("u")
agora[0] = 301; assert not lim.esta_bloqueado("u"), "bloqueio expira"
lim.registrar_falha("v"); agora[0] = 400; lim.registrar_falha("v"); lim.registrar_falha("v")
assert not lim.esta_bloqueado("v"), "falha antiga fora da janela não conta"

# fazer_login: 5 falhas por usuário bloqueiam até a senha certa
for _ in range(5): assert a.fazer_login("recepcao", "errada", "1.1.1.1") is None
try:
    a.fazer_login("Recepcao", "senha-secreta-1", "2.2.2.2"); raise SystemExit("deveria bloquear")
except a.MuitasTentativasError:
    pass
print("TODOS OS TESTES DE LOGIN PASSARAM")
