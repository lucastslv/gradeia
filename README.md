# matricula-ai

Assistente de matrícula de veteranos da UFRGS.

A entrada é o HTML exportado da tela **Possibilidade de Matrícula** do Portal do
Aluno. O arquivo diz o que o aluno **pode querer** cursar (elegibilidade, já
resolvida pelo Portal). A API pública de graduação da UFRGS diz o que está
**ofertado** no período. O assistente cruza os dois.

O ícone de relógio do Portal é ignorado de propósito: ele responde "tem turma no
semestre do arquivo", não "vai ter turma quando o aluno se matricular".

## Estados

| Estado | Significado |
|---|---|
| `ofertada` | há pelo menos uma turma no período, para o curso do aluno |
| `nao_ofertada` | o período tem oferta, mas não para essa disciplina |
| `nao_publicado` | o período ainda não tem nenhuma turma publicada |

`nao_publicado` nunca é tratado como "nada é ofertado".

## Uso

```bash
uv sync
uv run python -m matricula.cli "Aluno - Possibilidade de Matrícula.html"
uv run python -m matricula.cli "Aluno - Possibilidade de Matrícula.html" --json
```

Interface web:

```bash
uv run uvicorn matricula.web.app:app --reload
# http://127.0.0.1:8000
```

A UI usa HTMX e Tailwind via CDN (protótipo). Para produção, gere o CSS do
Tailwind em vez de usar o CDN.

## Chat

Opcional. Usa um provedor OpenAI-compatível (DeepSeek por padrão):

```bash
export DEEPSEEK_API_KEY=...
# opcionais
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-flash
```

`deepseek-chat` foi descontinuado em 2026-07-24. Use `deepseek-flash` (padrão)
ou `deepseek-v4-pro`.

A API da DeepSeek é **stateless**: não existe um "conversations mode" no
servidor (o parâmetro `conversation` do Responses API é explicitamente não
suportado). O histórico é mantido localmente, em SQLite. O thinking mode fica
desligado porque, com tool calls, a API exige reenviar o `reasoning_content` em
todas as chamadas seguintes — e o histórico persistido é só texto.

O modelo recebe a análise como contexto e pode chamar ferramentas (`resumo`,
`listar_disciplinas`, `detalhar_disciplina`, `listar_turmas`). Sem a chave, o
painel fica desabilitado e o resto do app funciona normalmente.

O HTML contém dados pessoais (nome, IP, sessão). O parser descarta esses campos;
não versione o arquivo original. O fixture em `tests/fixtures/` é anonimizado.

## Testes

```bash
uv run pytest
```
