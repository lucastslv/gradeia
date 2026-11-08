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

A UI usa Jinja + Tailwind via CDN (protótipo). A grade semanal é uma **ilha
Svelte** em `frontend/`, compilada para `matricula/web/static/planner/`; ela tem
CSS próprio. O chat usa SSE com JS puro.

Para produção, gere o CSS da página com o Tailwind em vez do CDN.

### Rebuild da ilha

Os assets compilados são versionados, então só é preciso rebuildar ao alterar a
grade:

```bash
cd frontend
npm install
npm run build
```

## Chat

Opcional. Usa um provedor OpenAI-compatível (DeepSeek por padrão):

```bash
cp .env.example .env
# edite o .env e preencha DEEPSEEK_API_KEY
uv run uvicorn matricula.web.app:app --reload
```

O `.env` é carregado automaticamente (sem sobrescrever variáveis já exportadas
no shell). Variáveis aceitas:

```bash
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_TIMEOUT=120
```

`deepseek-chat` foi descontinuado em 2026-07-24. Use `deepseek-flash` (padrão)
ou `deepseek-v4-pro`.

A API da DeepSeek é **stateless**: não existe um "conversations mode" no
servidor (`conversation` e `previous_response_id` não são suportados). O
histórico é mantido localmente, em SQLite. O chat usa a **Responses API**
(`/responses`), com `reasoning.effort = "none"` para reduzir latência e custo.

O modelo recebe a análise como contexto e pode chamar ferramentas de leitura
(`resumo`, `listar_disciplinas`, `detalhar_disciplina`, `listar_turmas`,
`estado_da_grade`) e de escrita (`adicionar_disciplina`, `trocar_turma`,
`remover_disciplina`, `montar_grade_sem_conflito`). O chat altera o plano no
SQLite e a ilha recebe um evento SSE `plano` para atualizar a grade na hora.
Sem a chave, o painel fica desabilitado e o resto do app funciona normalmente.

A resposta é transmitida por **SSE** (`POST /analise/{id}/chat/stream`): o texto
aparece enquanto é gerado e, ao final, é renderizado em Markdown. O histórico é
persistido no SQLite para o próximo carregamento da página.

O HTML contém dados pessoais (nome, IP, sessão). O parser descarta esses campos;
não versione o arquivo original. O fixture em `tests/fixtures/` é anonimizado.

## Testes

```bash
uv run pytest
```
