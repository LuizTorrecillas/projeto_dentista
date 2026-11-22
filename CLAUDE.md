# CLAUDE.md

Guia para trabalhar neste projeto: sistema de agendamento de clínica odontológica
(Python OO + SQLite + FastAPI + front-end estático). Descrição completa no README.md.

## Sobre quem desenvolve

Estudante de Ciência da Computação, aprendendo. Explicar tudo em português simples,
sem jargão não explicado. Ao final de cada tarefa: o que mudou e por quê, arquivos
alterados, como testar manualmente, decisões tomadas e alternativas descartadas.

## Ambiente

- Linux Mint, venv em `.venv` (Python 3.12). Instalar pacotes só com o venv ativado;
  nunca `pip install` fora dele nem `--break-system-packages`.
- Rodar tudo a partir da raiz do projeto:
  - servidor: `uvicorn app.main:app --reload`
  - testes: `pytest -q`
  - scripts: `python -m scripts.criar_usuario`, `python -m scripts.backup`,
    `python -m scripts.restaurar_backup`
- O servidor exige `.env` com `CLINICA_CHAVE_SECRETA` (veja `.env.example`).

## Arquitetura (manter)

```
app/main.py                      API: rotas finas, validação (pydantic), erros -> HTTP
app/seguranca/autenticacao.py    hash scrypt, login, limitador de tentativas
app/dominio/clinica.py           Paciente, Dentista, Consulta, EstadoConsulta, Agenda
app/dominio/excecoes.py          erros de negócio (sem depender de FastAPI/SQLite)
app/persistencia/repositorio.py  tuplas <-> objetos; cria registros
app/persistencia/banco.py        SQL puro com sqlite3, devolve tuplas
app/config.py                    .env, RAIZ_DO_PROJETO, PASTA_DADOS
app/static/                      front (index.html, login.html, app.js, login.js, style.css)
scripts/                         criar_usuario, backup, restaurar_backup
tests/                           pytest (conftest.py com fixtures)
dados/                           clinica.db e backups/ (fora do Git)
```

- `main.py` **não** importa do `banco.py`, exceto `criar_tabelas` (há um teste que
  garante isso). Ele usa o repositório e a `Agenda`.
- Imports absolutos a partir do pacote: `from app.persistencia.banco import ...`.
- O import circular entre `clinica.py` e `repositorio.py` é evitado com imports
  **dentro dos métodos** da `Agenda`.

## Convenções

- Toda função do `banco.py` abre a conexão e fecha num `try/finally`; o `return`
  fica dentro do `try`, nunca no `finally`.
- SELECTs listam as colunas pelo nome (nada de `SELECT *`). A tupla de consulta tem
  7 colunas: `id, data_hora, motivo, estado, paciente_id, dentista_id, duracao_minutos`.
  Colunas novas entram sempre no **fim** da tabela, com migração em `_criar_tabelas()`
  (checar com `PRAGMA table_info` e fazer `ALTER TABLE ADD COLUMN`).
- Datas no banco: texto `"%Y-%m-%d %H:%M:%S"` (`clinica.FORMATO_DATA_HORA`), horário
  local sem fuso. Datas com fuso recebidas pela API são convertidas para o local.
- Erros -> HTTP: `ConflitoDeHorarioError` (herda de ValueError) -> 409; outro
  `ValueError` da Agenda (data no passado, duração) -> 400; `RegistroDuplicadoError`
  -> 409; `ConsultaNaoEncontradaError` -> 404; `ConsultaJaCanceladaError` -> 409.
  Capturar `ConflitoDeHorarioError` **antes** de `ValueError`.
- Conflito de horário: `[início, fim)`; conflita se `inicio_existente < fim_novo` e
  `fim_existente > inicio_novo`, mesmo dentista, estado diferente de 'Cancelada'.
  Checagem e INSERT na mesma transação (`BEGIN IMMEDIATE`).
- Padronização: CPF só com 11 dígitos (`normalizar_cpf`), CRO em maiúsculas
  (`normalizar_cro`), nomes com `normalizar_nome`. Busca por nome ignora maiúsculas e
  acentos com a função SQL `normalizar` registrada em `criar_conexao()` e `instr`
  (não LIKE, para `%` e `_` não virarem curinga).
- Front: dados do banco entram no DOM só por `textContent` (nunca `innerHTML`).
  Chamadas à API passam por `chamarApi()`, que leva ao login em caso de 401.
- Commits em português, mensagem clara. Não fazer `git push` (quem desenvolve envia).

## Regras de trabalho

- **Nunca alterar `dados/clinica.db` em testes.** Os testes usam banco temporário
  (`CLINICA_DB` apontado para `tmp_path` pela fixture `banco_temporario`, automática).
- Antes de qualquer mudança de estrutura no banco, fazer backup
  (`python -m scripts.backup` ou cópia com a API `Connection.backup`, nunca `cp`
  com o servidor rodando).
- Dependências novas: o mínimo possível, justificadas e registradas em
  `requirements.txt` (gerado com `pip freeze` dentro do venv).
- Se uma instrução conflitar com o código ou faltar informação, perguntar antes.

## Estado atual (nov/2026)

Itens concluídos: duração e conflito por intervalo; busca por nome sem acento com
seleção pesquisável; login com sessão por cookie assinado; backup/restauração;
109 testes com pytest; revisão de camadas; organização em pastas; README.

Pendências conhecidas:
- O banco real tem um paciente cadastrado duas vezes (o mesmo CPF, uma vez com espaço
  no início), de antes da padronização. Decidir com quem desenvolve qual manter
  (conferir consultas ligadas e fazer backup antes). Nunca copiar dados reais de
  pacientes (CPF, nome, telefone) para arquivos versionados.
- Veja "Limitações e próximos passos" no README (HTTPS, LGPD, PostgreSQL etc.).
