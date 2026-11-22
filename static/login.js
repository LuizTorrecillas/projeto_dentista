const formLogin = document.getElementById("form-login");
const mensagem = document.getElementById("mensagem");
const campoSenha = document.getElementById("senha");

// Quem já está logado não precisa ver esta tela
fetch("/me").then((resposta) => {
  if (resposta.ok) window.location.replace("/");
});

formLogin.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  mensagem.textContent = "";
  mensagem.className = "";

  const botao = formLogin.querySelector("button");
  botao.disabled = true; // evita duplo envio enquanto o servidor confere a senha

  try {
    const resposta = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome_usuario: document.getElementById("nome-usuario").value,
        senha: campoSenha.value,
      }),
    });

    if (resposta.ok) {
      window.location.replace("/");
      return;
    }

    const corpo = await resposta.json().catch(() => ({}));
    mensagem.textContent =
      typeof corpo.detail === "string" ? corpo.detail : "Usuário ou senha inválidos.";
    mensagem.className = "erro";
    campoSenha.value = "";
    campoSenha.focus();
  } catch {
    mensagem.textContent = "Não foi possível falar com o servidor.";
    mensagem.className = "erro";
  } finally {
    botao.disabled = false;
  }
});
