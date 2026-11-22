// ---------- Acesso à API ----------
// Todas as chamadas passam por aqui. Se a API responder 401 (sem login ou sessão
// expirada), vamos para a tela de login. A promessa devolvida nunca termina, para
// que o código que chamou simplesmente pare, sem mostrar erro na tela.
async function chamarApi(url, opcoes = {}) {
  const resposta = await fetch(url, opcoes);
  if (resposta.status === 401) {
    window.location.replace("/login.html");
    return new Promise(() => {});
  }
  return resposta;
}

// ---------- Sessão (cabeçalho) ----------
async function carregarUsuario() {
  const resposta = await chamarApi("/me");
  if (resposta.ok) {
    const usuario = await resposta.json();
    document.getElementById("usuario-logado").textContent = usuario.nome_usuario;
  }
}

document.getElementById("btn-sair").addEventListener("click", async () => {
  await fetch("/logout", { method: "POST" });
  window.location.replace("/login.html");
});

carregarUsuario();

const filtroData = document.getElementById("filtro-data");
const lista = document.getElementById("lista-consultas");
const form = document.getElementById("form-agendar");
const mensagem = document.getElementById("mensagem");

// ---------- Seleção pesquisável ----------
// Liga um campo de texto a uma lista de sugestões que vem da API enquanto se digita.
// Ao escolher uma sugestão, guardamos o objeto inteiro; o formulário pega só a chave
// (cpf ou cro) com valor(). Se a pessoa editar o texto depois, a escolha é desfeita.
function criarSeletor({ input, lista, url, formatar, chave }) {
  let escolhido = null;
  let itensAtuais = [];
  let ativo = -1;
  let temporizador = null;
  let numeroPedido = 0;

  function fechar() {
    lista.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    ativo = -1;
  }

  function destacar(indice) {
    ativo = indice;
    [...lista.children].forEach((li, i) => li.classList.toggle("ativo", i === indice));
    if (indice >= 0) {
      const li = lista.children[indice];
      input.setAttribute("aria-activedescendant", li.id);
      li.scrollIntoView({ block: "nearest" });
    }
  }

  function escolher(item) {
    escolhido = item;
    input.value = formatar(item);
    fechar();
  }

  function mostrar(itens) {
    itensAtuais = itens;
    lista.replaceChildren();
    ativo = -1;

    if (itens.length === 0) {
      const vazio = document.createElement("li");
      vazio.className = "vazio";
      vazio.textContent = "Nenhum resultado.";
      lista.appendChild(vazio);
    }

    itens.forEach((item, i) => {
      const li = document.createElement("li");
      li.id = `${lista.id}-${i}`;
      li.setAttribute("role", "option");
      li.textContent = formatar(item); // textContent: dados do banco nunca viram HTML
      // mousedown (e não click) porque o click viria depois do blur, que fecha a lista
      li.addEventListener("mousedown", (evento) => {
        evento.preventDefault();
        escolher(item);
      });
      lista.appendChild(li);
    });

    lista.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }

  async function buscar() {
    const meuNumero = ++numeroPedido;
    const termo = encodeURIComponent(input.value.trim());
    const resposta = await chamarApi(`${url}?busca=${termo}&limite=10`);
    if (!resposta.ok) return;
    const itens = await resposta.json();
    // Se a pessoa digitou de novo enquanto esperávamos, esta resposta já está velha
    if (meuNumero !== numeroPedido) return;
    if (document.activeElement === input) mostrar(itens);
  }

  input.addEventListener("input", () => {
    escolhido = null;
    clearTimeout(temporizador);
    temporizador = setTimeout(buscar, 250); // espera a pessoa parar de digitar
  });
  input.addEventListener("focus", buscar);
  input.addEventListener("blur", fechar);
  input.addEventListener("keydown", (evento) => {
    if (lista.hidden || itensAtuais.length === 0) return;
    if (evento.key === "ArrowDown") {
      evento.preventDefault();
      destacar(Math.min(ativo + 1, itensAtuais.length - 1));
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      destacar(Math.max(ativo - 1, 0));
    } else if (evento.key === "Enter" && ativo >= 0) {
      evento.preventDefault();
      escolher(itensAtuais[ativo]);
    } else if (evento.key === "Escape") {
      fechar();
    }
  });

  return {
    valor: () => (escolhido ? escolhido[chave] : null),
    limpar: () => {
      escolhido = null;
      input.value = "";
      fechar();
    },
  };
}

const seletorPaciente = criarSeletor({
  input: document.getElementById("busca-paciente"),
  lista: document.getElementById("opcoes-paciente"),
  url: "/pacientes",
  formatar: (p) => `${p.nome} - ${p.cpf}`,
  chave: "cpf",
});

const seletorDentista = criarSeletor({
  input: document.getElementById("busca-dentista"),
  lista: document.getElementById("opcoes-dentista"),
  url: "/dentistas",
  formatar: (d) => `${d.nome} - ${d.cro} - ${d.especialidade}`,
  chave: "cro",
});

// data de hoje no fuso local (toISOString usaria UTC e poderia errar o dia)
filtroData.value = new Date().toLocaleDateString("sv-SE");

function mostrarMensagem(texto, tipo) {
  mensagem.textContent = texto;
  mensagem.className = tipo;
}

// A API devolve {"detail": "texto"} nos erros comuns e uma lista nos erros de validação (422)
function extrairErro(corpo) {
  if (typeof corpo.detail === "string") return corpo.detail;
  return "Dados inválidos. Confira os campos do formulário.";
}

async function carregarConsultas() {
  const resposta = await chamarApi(`/consultas?data=${filtroData.value}`);
  const consultas = await resposta.json();

  lista.innerHTML = "";

  if (consultas.length === 0) {
    const vazio = document.createElement("li");
    vazio.textContent = "Nenhuma consulta nesse dia.";
    lista.appendChild(vazio);
    return;
  }

  for (const c of consultas) {
    const item = document.createElement("li");
    if (c.estado === "Cancelada") item.classList.add("cancelada");

    const formatarHora = (texto) =>
      new Date(texto).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    const hora = `${formatarHora(c.data_hora)} às ${formatarHora(c.data_hora_fim)}`;

    // textContent (e não innerHTML) evita que um nome com HTML seja interpretado como código
    const texto = document.createElement("span");
    texto.textContent = `${hora} - ${c.paciente} com ${c.dentista} (${c.motivo}) [${c.estado}]`;
    item.appendChild(texto);

    if (c.estado === "Agendada") {
      const botao = document.createElement("button");
      botao.textContent = "Cancelar";
      botao.className = "btn-cancelar";
      botao.addEventListener("click", () => cancelarConsulta(c.id));
      item.appendChild(botao);
    }

    lista.appendChild(item);
  }
}

async function cancelarConsulta(id) {
  const resposta = await chamarApi(`/consultas/${id}/cancelar`, { method: "PATCH" });
  if (!resposta.ok) {
    const corpo = await resposta.json();
    mostrarMensagem(extrairErro(corpo), "erro");
    return;
  }
  mostrarMensagem("Consulta cancelada.", "sucesso");
  carregarConsultas();
}

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  const pacienteCpf = seletorPaciente.valor();
  const dentistaCro = seletorDentista.valor();
  if (!pacienteCpf || !dentistaCro) {
    mostrarMensagem("Escolha o paciente e o dentista na lista de sugestões.", "erro");
    return;
  }

  const dados = {
    paciente_cpf: pacienteCpf,
    dentista_cro: dentistaCro,
    data_hora: document.getElementById("data-hora").value,
    motivo: document.getElementById("motivo").value,
    duracao_minutos: Number(document.getElementById("duracao").value),
  };

  const resposta = await chamarApi("/consultas", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
  const corpo = await resposta.json();

  if (!resposta.ok) {
    mostrarMensagem(extrairErro(corpo), "erro");
    return;
  }

  mostrarMensagem("Consulta agendada com sucesso!", "sucesso");
  form.reset();
  seletorPaciente.limpar();
  seletorDentista.limpar();
  filtroData.value = dados.data_hora.slice(0, 10); // mostra o dia da consulta recém-criada
  carregarConsultas();
});

filtroData.addEventListener("change", carregarConsultas);
carregarConsultas();

// ---------- Cadastros ----------

function mostrarMensagemEm(elemento, texto, tipo) {
  elemento.textContent = texto;
  elemento.className = tipo;
}

async function enviarCadastro(url, dados, formulario, elementoMsg, textoSucesso) {
  const resposta = await chamarApi(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(dados),
  });
  const corpo = await resposta.json();

  if (!resposta.ok) {
    mostrarMensagemEm(elementoMsg, extrairErro(corpo), "erro");
    return;
  }
  mostrarMensagemEm(elementoMsg, textoSucesso, "sucesso");
  formulario.reset();
}

const formPaciente = document.getElementById("form-paciente");
formPaciente.addEventListener("submit", (evento) => {
  evento.preventDefault();
  enviarCadastro(
    "/pacientes",
    {
      nome: document.getElementById("pac-nome").value,
      cpf: document.getElementById("pac-cpf").value,
      telefone: document.getElementById("pac-telefone").value,
    },
    formPaciente,
    document.getElementById("msg-paciente"),
    "Paciente cadastrado!"
  );
});

const formDentista = document.getElementById("form-dentista");
formDentista.addEventListener("submit", (evento) => {
  evento.preventDefault();
  enviarCadastro(
    "/dentistas",
    {
      nome: document.getElementById("den-nome").value,
      cro: document.getElementById("den-cro").value,
      especialidade: document.getElementById("den-especialidade").value,
    },
    formDentista,
    document.getElementById("msg-dentista"),
    "Dentista cadastrado!"
  );
});