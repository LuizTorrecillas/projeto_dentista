"""Login: hash de senha, verificação e proteção contra tentativas em excesso.

Por que não guardar a senha? Se o banco vazar (backup esquecido, notebook roubado),
quem pegar o arquivo leria todas as senhas — e muita gente repete a mesma senha
no e-mail e no banco. Guardamos só um "hash": uma impressão digital da senha que
não dá para desfazer. No login, calculamos o hash do que foi digitado e comparamos.

- "Sal" (salt): bytes aleatórios diferentes para cada usuário, misturados à senha.
  Assim duas pessoas com a mesma senha têm hashes diferentes, e tabelas prontas
  de hashes de senhas comuns não servem para nada.
- scrypt: algoritmo de propósito LENTO e que gasta memória. Para o login isso não
  importa (uma vez só), mas para quem tenta adivinhar bilhões de senhas, sim.
"""
import hashlib
import hmac
import secrets
import threading
import time

from app.persistencia.banco import buscar_usuario_por_nome, buscar_usuario_por_id

# Parâmetros do scrypt: n = custo (potência de 2), r = tamanho do bloco, p = paralelismo.
# Com n=2**14 e r=8, cada verificação usa ~16 MB e leva algumas dezenas de milissegundos.
_N, _R, _P = 2 ** 14, 8, 1
_TAMANHO_SAL = 16
_TAMANHO_HASH = 64


def gerar_hash_senha(senha):
    """Devolve um texto no formato scrypt$n$r$p$sal$hash (tudo que é preciso para verificar)."""
    sal = secrets.token_bytes(_TAMANHO_SAL)
    resultado = hashlib.scrypt(senha.encode("utf-8"), salt=sal,
                               n=_N, r=_R, p=_P, dklen=_TAMANHO_HASH)
    return f"scrypt${_N}${_R}${_P}${sal.hex()}${resultado.hex()}"


def verificar_senha(senha, senha_hash):
    try:
        algoritmo, n, r, p, sal_hex, hash_hex = senha_hash.split("$")
        if algoritmo != "scrypt":
            return False
        esperado = bytes.fromhex(hash_hex)
        calculado = hashlib.scrypt(senha.encode("utf-8"), salt=bytes.fromhex(sal_hex),
                                   n=int(n), r=int(r), p=int(p), dklen=len(esperado))
    except (ValueError, TypeError):
        return False
    # compare_digest leva o mesmo tempo acerte ou erre; um "==" comum para no primeiro
    # byte diferente, e medir esse tempo poderia dar pistas a um atacante.
    return hmac.compare_digest(calculado, esperado)


# Hash de uma senha aleatória qualquer, usado quando o usuário NÃO existe: verificamos
# contra ele mesmo assim, para que "usuário inexistente" demore o mesmo que "senha errada".
_HASH_FALSO = gerar_hash_senha(secrets.token_urlsafe(16))


def _linha_para_usuario(linha):
    if linha is None:
        return None
    usuario_id, nome_usuario, _senha_hash, criado_em = linha
    return {"id": usuario_id, "nome_usuario": nome_usuario}


def obter_usuario(usuario_id):
    if usuario_id is None:
        return None
    return _linha_para_usuario(buscar_usuario_por_id(usuario_id))


def autenticar(nome_usuario, senha):
    """Devolve o usuário se nome e senha conferem; senão, None (sem dizer qual errou)."""
    linha = buscar_usuario_por_nome(nome_usuario.strip())
    if linha is None:
        verificar_senha(senha, _HASH_FALSO)
        return None
    if verificar_senha(senha, linha[2]):
        return _linha_para_usuario(linha)
    return None


# ---------- Proteção contra tentativas em excesso ----------

class MuitasTentativasError(Exception):
    pass


class LimitadorDeTentativas:
    """Conta falhas por chave (usuário ou IP), em memória.

    Com `max_falhas` falhas dentro de `janela` segundos, a chave fica bloqueada por
    `bloqueio` segundos. Fica em memória: reiniciar o servidor zera a contagem.
    `relogio` pode ser trocado nos testes para simular a passagem do tempo.
    """

    def __init__(self, max_falhas, janela=15 * 60, bloqueio=15 * 60, relogio=time.monotonic):
        self.max_falhas = max_falhas
        self.janela = janela
        self.bloqueio = bloqueio
        self._relogio = relogio
        self._falhas = {}          # chave -> lista de instantes das falhas
        self._bloqueado_ate = {}   # chave -> instante em que o bloqueio acaba
        # O FastAPI atende várias requisições ao mesmo tempo (em threads);
        # a trava impede duas de mexerem nos dicionários juntas.
        self._trava = threading.Lock()

    def _descartar_antigos(self, agora):
        for chave in list(self._falhas):
            recentes = [t for t in self._falhas[chave] if agora - t < self.janela]
            if recentes:
                self._falhas[chave] = recentes
            else:
                del self._falhas[chave]
        for chave, ate in list(self._bloqueado_ate.items()):
            if ate <= agora:
                del self._bloqueado_ate[chave]

    def esta_bloqueado(self, chave):
        with self._trava:
            self._descartar_antigos(self._relogio())
            return chave in self._bloqueado_ate

    def registrar_falha(self, chave):
        with self._trava:
            agora = self._relogio()
            self._descartar_antigos(agora)
            self._falhas.setdefault(chave, []).append(agora)
            if len(self._falhas[chave]) >= self.max_falhas:
                self._bloqueado_ate[chave] = agora + self.bloqueio
                del self._falhas[chave]

    def zerar(self, chave):
        with self._trava:
            self._falhas.pop(chave, None)
            self._bloqueado_ate.pop(chave, None)


# Por usuário o limite é baixo. Por IP é maior, porque numa clínica todos os
# computadores costumam sair pelo mesmo IP do roteador: um limite baixo por IP
# bloquearia a recepção inteira por causa de uma pessoa que errou a senha.
limitador_por_usuario = LimitadorDeTentativas(max_falhas=5)
limitador_por_ip = LimitadorDeTentativas(max_falhas=20)


def fazer_login(nome_usuario, senha, ip):
    """Autentica respeitando os limites. Levanta MuitasTentativasError se bloqueado."""
    chave_usuario = nome_usuario.strip().casefold()
    if limitador_por_usuario.esta_bloqueado(chave_usuario) or limitador_por_ip.esta_bloqueado(ip):
        # Bloqueado até mesmo com a senha certa; senão o bloqueio não protegeria nada.
        raise MuitasTentativasError()

    usuario = autenticar(nome_usuario, senha)
    if usuario is None:
        limitador_por_usuario.registrar_falha(chave_usuario)
        limitador_por_ip.registrar_falha(ip)
        return None

    limitador_por_usuario.zerar(chave_usuario)
    return usuario
