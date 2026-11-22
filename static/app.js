const filtroData = document.getElementById("filtro-data");
const lista = document.getElementById("lista-consultas");
const form = document.getElementById("form-agendar");
const mensagem = document.getElementById("mensagem");

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
  const resposta = await fetch(`/consultas?data=${filtroData.value}`);
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
  const resposta = await fetch(`/consultas/${id}/cancelar`, { method: "PATCH" });
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

  const dados = {
    paciente_cpf: document.getElementById("paciente-cpf").value,
    dentista_cro: document.getElementById("dentista-cro").value,
    data_hora: document.getElementById("data-hora").value,
    motivo: document.getElementById("motivo").value,
    duracao_minutos: Number(document.getElementById("duracao").value),
  };

  const resposta = await fetch("/consultas", {
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
  const resposta = await fetch(url, {
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