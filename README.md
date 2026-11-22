# Sistema de Agendamento para Clínica Odontológica

Sistema web para a recepção de uma clínica odontológica agendar, consultar e cancelar
consultas, com cadastro de pacientes e dentistas, login e backup automático do banco.

Feito em **Python** (orientação a objetos), **FastAPI**, **SQLite** e front-end em
**HTML, CSS e JavaScript puros**, servido pelo próprio FastAPI. Projeto de estudo,
desenvolvido durante a graduação em Ciência da Computação.

---

## Funcionalidades

- **Agenda do dia:** lista as consultas de uma data com o intervalo (ex.: `14:00 às 15:00`),
  paciente, dentista, motivo e situação (Agendada / Cancelada).
- **Agendamento com duração:** cada consulta tem duração de 10 a 240 minutos.
- **Conflito de horário realista:** o sistema impede dois horários que se sobrepõem
  para o mesmo dentista, e não só horários exatamente iguais.
- **Seguro contra agendamentos simultâneos:** se duas pessoas tentarem o mesmo horário
  ao mesmo tempo, só uma consegue.
- **Busca por nome sem acento:** ao agendar, digita-se parte do nome do paciente ou do
  dentista e escolhe-se numa lista. `joao` encontra `João`.
- **Cadastro de pacientes e dentistas**, com CPF e CRO padronizados (`111.222.333-44`
  e `11122233344` são reconhecidos como o mesmo CPF).
- **Cancelamento que mantém o histórico:** a consulta cancelada continua registrada e
  libera o horário.
- **Login:** só usuários cadastrados acessam a agenda. As senhas são guardadas com hash
  e há bloqueio temporário após várias tentativas erradas.
- **Backup automático:** cópia diária consistente do banco, com rodízio dos mais
  antigos, e script de restauração.
- **109 testes automatizados** com pytest.

---

## Arquitetura

O código é dividido em camadas. Cada camada só conversa com a de baixo, então dá
para trocar uma parte (por exemplo, o banco) sem reescrever as outras.

```
  Navegador (app/static: HTML + CSS + JS)
        │  requisições HTTP com JSON
        ▼
  API — app/main.py (FastAPI)
  Recebe e valida os dados, chama o domínio e converte erros em códigos HTTP.
  Não contém regra de negócio nem SQL.
        │
        ├──► Segurança — app/seguranca/autenticacao.py
        │    Hash de senha, verificação de login e limite de tentativas.
        ▼
  Domínio — app/dominio/
  clinica.py: Paciente, Dentista, Consulta, EstadoConsulta e Agenda (as regras:
  data no passado, duração permitida, cancelamento).
  excecoes.py: os erros de negócio (conflito de horário, registro duplicado...).
        │
        ▼
  Repositório — app/persistencia/repositorio.py
  Converte as linhas do banco (tuplas) em objetos do domínio, e vice-versa.
        │
        ▼
  Banco — app/persistencia/banco.py
  Só SQL puro com sqlite3. Cada função abre e fecha a própria conexão.
        │
        ▼
  dados/clinica.db (SQLite)
```

### Estrutura de pastas

```
projeto_dentista/
├── app/                        o sistema
│   ├── main.py                 API: rotas, validação de entrada, sessão
│   ├── config.py               leitura do .env e caminhos do projeto
│   ├── dominio/
│   │   ├── clinica.py          entidades e regras da agenda
│   │   └── excecoes.py         erros de regra de negócio
│   ├── persistencia/
│   │   ├── banco.py            SQL (tabelas, migração, consultas)
│   │   └── repositorio.py      tuplas do banco <-> objetos
│   ├── seguranca/
│   │   └── autenticacao.py     hash de senha e limite de tentativas
│   └── static/                 telas: index.html, login.html, app.js, login.js, style.css
├── scripts/
│   ├── criar_usuario.py        cria um usuário pelo terminal
│   ├── backup.py               backup do banco com rodízio
│   └── restaurar_backup.py     restaura um backup
├── tests/                      testes automatizados (pytest)
├── dados/                      banco e backups (criado automaticamente, fora do Git)
├── .env.example                modelo das configurações
├── pyproject.toml              configuração do pytest
└── requirements.txt            dependências com versões fixadas
```

---

## Instalação (Linux)

Requisitos: Python 3.10 ou mais novo (desenvolvido com 3.12) e Git.

```bash
git clone https://github.com/LuizTorrecillas/projeto_dentista.git
cd projeto_dentista
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> O `venv` cria um Python isolado só para este projeto, sem misturar pacotes com os
> do sistema. Toda vez que abrir um terminal novo, rode `source .venv/bin/activate`
> de novo, dentro da pasta do projeto.

### 1. Configurar o `.env`

O `.env` guarda as configurações secretas. Ele **não** vai para o Git.

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Cole a chave gerada depois de `CLINICA_CHAVE_SECRETA=` no arquivo `.env`.
Sem essa chave, o servidor não inicia: é ela que assina o cookie de login.

| Variável | Para que serve | Padrão |
|---|---|---|
| `CLINICA_CHAVE_SECRETA` | assina o cookie de sessão (mínimo 32 caracteres) | **obrigatória** |
| `CLINICA_COOKIE_SECURE` | `true` somente quando o sistema roda em HTTPS | `false` |
| `CLINICA_SESSAO_HORAS` | tempo sem uso até pedir login de novo | `8` |
| `CLINICA_DB` | caminho do arquivo do banco | `dados/clinica.db` |
| `CLINICA_BACKUPS_MANTER` | quantos backups manter | `14` |

### 2. Criar o primeiro usuário

Não existe usuário nem senha padrão. Crie o primeiro pelo terminal (a senha não aparece
enquanto você digita e precisa ter pelo menos 10 caracteres):

```bash
python -m scripts.criar_usuario
```

### 3. Rodar

Para usar só neste computador:

```bash
uvicorn app.main:app --reload
```

Acesse **http://127.0.0.1:8000**. A documentação interativa da API fica em
**http://127.0.0.1:8000/docs** (as rotas exigem login: entre pela tela do sistema
antes, no mesmo navegador).

Para que outros computadores da rede da clínica acessem:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Nos outros computadores, acesse `http://IP-DESTE-COMPUTADOR:8000` (o IP aparece com
`hostname -I`). O `--reload` é só para desenvolvimento e fica de fora aqui.
**Leia a seção sobre HTTPS** antes de usar assim com dados reais.

---

## Testes

```bash
pytest -q
```

Cada teste usa um banco novo e temporário; o `dados/clinica.db` real nunca é tocado.
Os testes cobrem, entre outros pontos:

- cadastros, duplicados (409) e registros inexistentes (404);
- todos os casos de sobreposição de horário;
- data no passado (400);
- cancelar e reagendar o mesmo horário;
- busca com e sem acento;
- login correto e incorreto, bloqueio por tentativas, 401 sem sessão e cookie adulterado;
- migração de banco antigo e agendamentos simultâneos;
- integridade do backup, limite de arquivos e restauração.

---

## Backup e restauração

### Fazer um backup

```bash
python -m scripts.backup              # mantém os 14 mais recentes
python -m scripts.backup --manter 30
```

Gera `dados/backups/clinica_AAAA-MM-DD_HHMM.db` e apaga os mais antigos além do limite.
O script usa a API de backup do próprio SQLite, e não uma cópia simples do arquivo:
assim o backup sai consistente mesmo se o servidor estiver gravando naquele momento.
Cada backup é conferido (`PRAGMA integrity_check`) antes de ser aceito.

### Backup automático todo dia (cron)

Abra o agendador de tarefas com `crontab -e` e acrescente uma linha (troque o caminho
pelo da sua pasta):

```
30 22 * * * cd /caminho/para/projeto_dentista && .venv/bin/python -m scripts.backup >> dados/backup.log 2>&1
```

| Parte | Significado |
|---|---|
| `30 22` | minuto 30, hora 22 (22:30) |
| `* * *` | todo dia do mês, todo mês, todo dia da semana |
| `cd ...` | entra na pasta do projeto (o cron começa na pasta pessoal) |
| `.venv/bin/python` | usa o Python do venv, sem precisar ativá-lo |
| `>> dados/backup.log 2>&1` | guarda as mensagens e os erros num arquivo de log |

O computador precisa estar ligado nesse horário. Guarde também, de tempos em tempos,
uma cópia da pasta `dados/backups/` em **outro lugar** (HD externo, nuvem): um backup
no mesmo disco não protege contra a perda desse disco.

### Restaurar

Pare o servidor antes. Depois:

```bash
python -m scripts.restaurar_backup                                     # lista os backups
python -m scripts.restaurar_backup dados/backups/clinica_2026-11-22_2230.db
```

O script recusa arquivos corrompidos e pede que você digite `RESTAURAR` para confirmar.
Antes de sobrescrever, ele guarda o banco atual em
`dados/backups/antes_de_restaurar_*.db`, para que a restauração possa ser desfeita.

---

## API

Todas as rotas, exceto `/login` e `/logout`, exigem uma sessão ativa e respondem
**401** sem login.

| Método | Rota | Descrição | Respostas principais |
|---|---|---|---|
| `POST` | `/login` | Entra no sistema (`nome_usuario`, `senha`) | 200, 401, 429 |
| `POST` | `/logout` | Sai do sistema | 200 |
| `GET` | `/me` | Usuário logado | 200, 401 |
| `POST` | `/pacientes` | Cadastra paciente (`nome`, `cpf`, `telefone`) | 201, 409, 422 |
| `GET` | `/pacientes?busca=&limite=` | Lista/busca por nome (até 50, ordem alfabética) | 200, 422 |
| `GET` | `/pacientes/{cpf}` | Busca por CPF (com ou sem pontuação) | 200, 404 |
| `POST` | `/dentistas` | Cadastra dentista (`nome`, `cro`, `especialidade`) | 201, 409, 422 |
| `GET` | `/dentistas?busca=&limite=` | Lista/busca por nome | 200, 422 |
| `GET` | `/dentistas/{cro}` | Busca por CRO | 200, 404 |
| `POST` | `/consultas` | Agenda (`data_hora`, `motivo`, `paciente_cpf`, `dentista_cro`, `duracao_minutos`) | 201, 400, 404, 409, 422 |
| `GET` | `/consultas?data=AAAA-MM-DD` | Consultas do dia, em ordem de horário | 200, 422 |
| `PATCH` | `/consultas/{id}/cancelar` | Cancela uma consulta agendada | 200, 404, 409 |

Os códigos significam: **400** regra violada (ex.: data no passado), **401** sem login,
**404** não encontrado, **409** conflito (horário ocupado, CPF/CRO já cadastrado,
consulta já cancelada), **422** dados em formato inválido, **429** tentativas demais.

---

## Regras de negócio

- **Conflito de horário por intervalo.** Uma consulta ocupa o intervalo
  `[início, início + duração)`. Uma consulta nova conflita com uma existente do mesmo
  dentista quando `início_existente < fim_novo` **e** `fim_existente > início_novo`.
  Exemplo, com uma consulta das 14:00 às 15:00:

  | Tentativa | Resultado |
  |---|---|
  | 14:30, 30 min | conflito (começa no meio) |
  | 13:30, 60 min | conflito (termina no meio) |
  | 13:30, 30 min | permitido (termina às 14:00, colada) |
  | 15:00, 30 min | permitido (começa às 15:00, colada) |

- **A checagem é atômica.** A verificação de conflito e a gravação acontecem na mesma
  transação (`BEGIN IMMEDIATE`). Assim, duas pessoas agendando o mesmo horário ao
  mesmo tempo não conseguem as duas.
- **Cancelamento mantém o histórico.** A consulta não é apagada: muda para
  "Cancelada", deixa de bloquear o horário e continua aparecendo na agenda do dia.
  Uma consulta já cancelada não pode ser cancelada de novo.
- **Sem agendamento no passado** e duração sempre entre 10 e 240 minutos.
- **Dados padronizados.** O CPF é salvo só com os 11 dígitos, o CRO em maiúsculas e os
  nomes com iniciais maiúsculas e sem espaços sobrando, para evitar cadastros duplicados.
- **Senhas.** Nunca são guardadas: o banco guarda só um hash `scrypt` com "sal"
  aleatório. Depois de 5 erros seguidos para o mesmo usuário (ou 20 do mesmo IP) em
  15 minutos, o login fica bloqueado por 15 minutos. A mensagem de erro não revela se
  foi o usuário ou a senha que estava errado.

---

## Limitações e próximos passos

Este é um projeto de estudo. Funciona para o que se propõe, mas **ainda não está pronto
para uso real com dados de pacientes**. Abaixo estão alguns pontos que pretendo adicionar futuramente para uma possível integração:

**Segurança e LGPD**
- **HTTPS.** Em HTTP, a senha e o cookie de login trafegam sem criptografia pela rede:
  qualquer pessoa no mesmo Wi-Fi poderia capturá-los. Fora do `localhost`, é preciso
  colocar um servidor como Caddy ou Nginx na frente do uvicorn, com certificado, e
  ligar `CLINICA_COOKIE_SECURE=true`.
- **LGPD.** Dados de saúde são "dados sensíveis" pela lei. Ainda faltam: registro de
  quem acessou ou alterou cada dado (auditoria), consentimento do paciente, como
  exportar ou excluir os dados de um paciente a pedido dele, política de retenção e
  criptografia do banco e dos backups.
- **Logout não invalida cookies copiados.** A sessão fica no próprio cookie assinado;
  um cookie copiado continua válido até expirar (8 h sem uso). Sessões guardadas no
  servidor resolveriam isso.
- **Contador de tentativas de login em memória.** Reiniciar o servidor zera a contagem.
  Atrás de um proxy, todos os acessos aparecem com o IP do proxy.
- **Sem perfis de acesso.** Todo usuário logado pode fazer tudo. Não há tela para
  gerenciar usuários (só o script `criar_usuario`) nem para trocar a senha.

**Funcionalidades**
- Editar ou excluir pacientes e dentistas, e reagendar uma consulta (hoje é preciso
  cancelar e agendar de novo).
- Marcar consulta como "Realizada" (o estado existe no banco, mas não há tela para isso).
- Horário de atendimento de cada dentista, intervalo de almoço e feriados.
- Conflito de horário também para o **paciente** (hoje só o dentista é verificado).
- Alergias e prontuário (a tabela `alergias` existe, mas ainda não é usada).
- Validação dos dígitos verificadores do CPF (hoje só confere se são 11 dígitos).
- Lembretes automáticos por WhatsApp ou SMS na véspera da consulta.

**Técnico**
- **Migrar para PostgreSQL** se houver vários computadores gravando ao mesmo tempo com
  frequência. O SQLite trava o arquivo inteiro a cada escrita.
- Migrações de banco com uma ferramenta própria (ex.: Alembic), em vez da checagem
  manual em `criar_tabelas()`.
- A listagem do dia busca paciente e dentista de cada consulta separadamente. Com um
  `JOIN`, seria uma consulta só.
- Integração contínua (rodar os testes automaticamente a cada push no GitHub).
- O backup roda no mesmo disco do banco; falta uma cópia automática para fora da máquina.
