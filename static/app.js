// ---------- Acesso à API ----------
// Todas as chamadas passam por aqui. Se a API responder 401 (sem login ou sessão
// expirada), vamos para a tela de login. A promessa devolvida nunca termina, para
// que o código que chamou simplesmente pare, sem mostrar erro na tela.
// Se o servidor estiver fora do ar, devolvemos uma resposta de erro "de mentira",
// para que todo o código trate esse caso igual a qualquer outro erro da API.
async function chamarApi(url, opcoes = {}) {
  let resposta;
  try {
    resposta = await fetch(url, opcoes);
  } catch {
    return Response.json({ detail: "Não foi possível falar com o servidor." }, { status: 503 });
  }
  if (resposta.status === 401) {
    window.location.replace("/login.html");
    return new Promise(() => {});
  }
  return resposta;
}

// Lê o corpo JSON sem quebrar se o servidor devolver outra coisa (ex.: erro 500 em texto)
async function lerJson(resposta) {
  try {
    return await resposta.json();
  } catch {
    return {};
  }
}

// A API devolve {"detail": "texto"} nos erros comuns e uma lista nos erros de
// validação (422), onde cada item tem a mensagem em "msg".
function extrairErro(corpo) {
  if (typeof corpo.detail === "string") return corpo.detail;
  if (Array.isArray(corpo.detail) && corpo.detail[0]?.msg) {
    return corpo.detail[0].msg.replace(/^Value error, /, "");
  }
  return "Dados inválidos. Confira os campos do formulário.";
}

function mostrarMensagem(elemento, texto, tipo) {
  elemento.textContent = texto;
  elemento.className = tipo;
}

// ---------- Sessão (cabeçalho) ----------
async function carregarUsuario() {
  const resposta = await chamarApi("/me");
  if (resposta.ok) {
    const usuario = await lerJson(resposta);
    document.getElementById("usuario-logado").textContent = usuario.nome_usuario;
  }
}

document.getElementById("btn-sair").addEventListener("click", async () => {
  await fetch("/logout", { method: "POST" });
  window.location.replace("/login.html");
});

carregarUsuario();

const filtroData = document.getElementById("filtro-data");
const listaConsultas = document.getElementById("lista-consultas");
const formAgendar = document.getElementById("form-agendar");
const msgAgendar = document.getElementById("mensagem");

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
    const itens = await lerJson(resposta);
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

function formatarHora(texto) {
  return new Date(texto).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function mostrarAvisoNaLista(texto) {
  const item = document.createElement("li");
  item.textContent = texto;
  listaConsultas.replaceChildren(item);
}

// ---------- Consultas do dia ----------

async function carregarConsultas() {
  if (!filtroData.value) {
    mostrarAvisoNaLista("Escolha uma data.");
    return;
  }

  const resposta = await chamarApi(`/consultas?data=${filtroData.value}`);
  const consultas = await lerJson(resposta);
  if (!resposta.ok) {
    mostrarAvisoNaLista(extrairErro(consultas));
    return;
  }
  if (consultas.length === 0) {
    mostrarAvisoNaLista("Nenhuma consulta nesse dia.");
    return;
  }

  listaConsultas.replaceChildren();
  for (const c of consultas) {
    const item = document.createElement("li");
    if (c.estado === "Cancelada") item.classList.add("cancelada");

    // textContent (e não innerHTML) evita que um nome com HTML seja interpretado como código
    const texto = document.createElement("span");
    const horario = `${formatarHora(c.data_hora)} às ${formatarHora(c.data_hora_fim)}`;
    texto.textContent = `${horario} - ${c.paciente} com ${c.dentista} (${c.motivo}) [${c.estado}]`;
    item.appendChild(texto);

    if (c.estado === "Agendada") {
      const botao = document.createElement("button");
      botao.type = "button";
      botao.textContent = "Cancelar";
      botao.className = "btn-cancelar";
      botao.addEventListener("click", () => cancelarConsulta(c, horario));
      item.appendChild(botao);
    }

    listaConsultas.appendChild(item);
  }
}

async function cancelarConsulta(consulta, horario) {
  // Cancelar não tem volta pela tela, então pedimos confirmação
  if (!confirm(`Cancelar a consulta de ${consulta.paciente} (${horario})?`)) return;

  const resposta = await chamarApi(`/consultas/${consulta.id}/cancelar`, { method: "PATCH" });
  if (!resposta.ok) {
    mostrarMensagem(msgAgendar, extrairErro(await lerJson(resposta)), "erro");
  } else {
    mostrarMensagem(msgAgendar, "Consulta cancelada.", "sucesso");
  }
  carregarConsultas();
}

filtroData.addEventListener("change", carregarConsultas);
carregarConsultas();

// ---------- Formulários ----------

// Envia um formulário em JSON, travando o botão enquanto espera (evita duplo clique).
// Devolve o corpo da resposta se deu certo, ou null se deu erro (já mostrado na tela).
async function enviarFormulario(formulario, url, dados, elementoMsg) {
  const botao = formulario.querySelector('button[type="submit"]');
  botao.disabled = true;
  try {
    const resposta = await chamarApi(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(dados),
    });
    const corpo = await lerJson(resposta);
    if (!resposta.ok) {
      mostrarMensagem(elementoMsg, extrairErro(corpo), "erro");
      return null;
    }
    return corpo;
  } finally {
    botao.disabled = false;
  }
}

formAgendar.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  const pacienteCpf = seletorPaciente.valor();
  const dentistaCro = seletorDentista.valor();
  if (!pacienteCpf || !dentistaCro) {
    mostrarMensagem(msgAgendar, "Escolha o paciente e o dentista na lista de sugestões.", "erro");
    return;
  }

  const dados = {
    paciente_cpf: pacienteCpf,
    dentista_cro: dentistaCro,
    data_hora: document.getElementById("data-hora").value,
    motivo: document.getElementById("motivo").value,
    duracao_minutos: Number(document.getElementById("duracao").value),
  };

  const criada = await enviarFormulario(formAgendar, "/consultas", dados, msgAgendar);
  if (!criada) return;

  mostrarMensagem(msgAgendar, "Consulta agendada com sucesso!", "sucesso");
  formAgendar.reset();
  seletorPaciente.limpar();
  seletorDentista.limpar();
  filtroData.value = dados.data_hora.slice(0, 10); // mostra o dia da consulta recém-criada
  carregarConsultas();
});

function ligarCadastro(idFormulario, url, campos, idMensagem, textoSucesso) {
  const formulario = document.getElementById(idFormulario);
  const elementoMsg = document.getElementById(idMensagem);

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const dados = {};
    for (const [chave, idCampo] of Object.entries(campos)) {
      dados[chave] = document.getElementById(idCampo).value;
    }
    const salvo = await enviarFormulario(formulario, url, dados, elementoMsg);
    if (!salvo) return;
    // As sugestões do agendamento vêm direto da API a cada busca, então o cadastro
    // novo já aparece lá sem recarregar a página.
    mostrarMensagem(elementoMsg, `${textoSucesso}: ${salvo.nome}`, "sucesso");
    formulario.reset();
  });
}

ligarCadastro("form-paciente", "/pacientes",
  { nome: "pac-nome", cpf: "pac-cpf", telefone: "pac-telefone" },
  "msg-paciente", "Paciente cadastrado");

ligarCadastro("form-dentista", "/dentistas",
  { nome: "den-nome", cro: "den-cro", especialidade: "den-especialidade" },
  "msg-dentista", "Dentista cadastrado");
