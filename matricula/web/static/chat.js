(() => {
  const form = document.getElementById("chat-form");
  if (!form) return;

  const chat = document.getElementById("chat");
  const input = form.querySelector("input[name='mensagem']");
  const submit = form.querySelector("button[type='submit']");
  const status = document.getElementById("chat-status");
  const url = form.dataset.streamUrl;
  let busy = false;

  function bubble(role) {
    const div = document.createElement("div");
    div.className =
      role === "user"
        ? "ml-6 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
        : "chat-md mr-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 whitespace-pre-wrap";
    chat.appendChild(div);
    scroll();
    return div;
  }

  function scroll() {
    chat.scrollTop = chat.scrollHeight;
  }

  function handleEvent(raw, assistant) {
    let event = "message";
    const dataLines = [];
    for (const line of raw.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (!dataLines.length) return;

    let data;
    try {
      data = JSON.parse(dataLines.join("\n"));
    } catch (_) {
      return;
    }

    if (event === "delta") {
      assistant.textContent += data.text || "";
    } else if (event === "reset") {
      assistant.textContent = "";
    } else if (event === "done" || event === "error") {
      assistant.classList.remove("whitespace-pre-wrap");
      assistant.innerHTML = data.html || "";
    }
    scroll();
  }

  async function send(text) {
    if (busy || !text || !text.trim()) return;
    busy = true;
    form.reset();
    bubble("user").textContent = text;
    const assistant = bubble("assistant");

    if (status) status.classList.remove("hidden");
    if (submit) submit.disabled = true;

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ mensagem: text }),
      });
      if (!response.ok || !response.body) {
        throw new Error("HTTP " + response.status);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let index;
        while ((index = buffer.indexOf("\n\n")) >= 0) {
          const raw = buffer.slice(0, index);
          buffer = buffer.slice(index + 2);
          handleEvent(raw, assistant);
        }
      }
      if (buffer.trim()) handleEvent(buffer, assistant);
      if (!assistant.textContent.trim()) {
        assistant.textContent = "Não consegui concluir a resposta.";
      }
    } catch (_) {
      assistant.classList.remove("whitespace-pre-wrap");
      assistant.textContent = "Não consegui falar com o servidor. Tente novamente.";
    } finally {
      busy = false;
      if (status) status.classList.add("hidden");
      if (submit) submit.disabled = false;
      scroll();
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    send(input.value);
  });

  document.querySelectorAll("[data-mensagem]").forEach((button) => {
    button.addEventListener("click", () => send(button.dataset.mensagem));
  });
})();
