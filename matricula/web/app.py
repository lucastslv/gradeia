"""Interface web (FastAPI + HTMX) do assistente de matrícula."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..ai.chat import ChatService
from ..ai.config import Settings
from ..core.api import UfrgsApi
from ..core.cache import SqliteCache
from ..core.errors import MatriculaError
from ..core.format import format_encontros
from ..core.models import Analise
from ..service.possibilidades import analisar, analisar_html
from .filters import filter_ofertas
from .markdown import render_markdown
from .store import AnalysisStore

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
CHAT_NAO_CONFIGURADO = (
    "O chat ainda não está configurado. Defina DEEPSEEK_API_KEY para ativar."
)

app = FastAPI(title="Assistente de Matrícula")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.filters["encontros"] = format_encontros
templates.env.filters["markdown"] = render_markdown


@lru_cache
def get_api() -> UfrgsApi:
    return UfrgsApi(cache=SqliteCache())


@lru_cache
def get_store() -> AnalysisStore:
    return AnalysisStore()


@lru_cache
def get_chat_service() -> ChatService | None:
    settings = Settings.from_env()
    if not settings.configured:
        return None

    from openai import OpenAI

    client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
    return ChatService(client, settings.model)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return _render(request, "index.html", {"erro": None})


@app.post("/analisar")
async def analisar_upload(
    request: Request,
    arquivo: UploadFile = File(...),
    api: UfrgsApi = Depends(get_api),
    store: AnalysisStore = Depends(get_store),
):
    raw = await arquivo.read()
    if not raw:
        return _erro(request, "O arquivo enviado está vazio.")
    if len(raw) > MAX_UPLOAD_BYTES:
        return _erro(request, "O arquivo passa do limite de 5 MB.")

    try:
        analise = analisar_html(raw, api)
    except MatriculaError as exc:
        return _erro(request, str(exc))

    analise_id = store.save(analise)
    return RedirectResponse(f"/analise/{analise_id}", status_code=303)


@app.get("/analise/{analise_id}", response_class=HTMLResponse)
def ver_analise(
    request: Request,
    analise_id: str,
    store: AnalysisStore = Depends(get_store),
    service: ChatService | None = Depends(get_chat_service),
) -> HTMLResponse:
    analise = _carregar(store, analise_id)
    return _render(
        request,
        "analise.html",
        {
            "analise": analise,
            "analise_id": analise_id,
            "ofertas": analise.ofertas,
            "filtros": {"estado": "", "carater": "", "q": ""},
            "mensagens": store.messages(analise_id),
            "chat_configurado": service is not None,
        },
    )


@app.get("/analise/{analise_id}/linhas", response_class=HTMLResponse)
def linhas(
    request: Request,
    analise_id: str,
    estado: str = "",
    carater: str = "",
    q: str = "",
    store: AnalysisStore = Depends(get_store),
) -> HTMLResponse:
    analise = _carregar(store, analise_id)
    ofertas = filter_ofertas(analise.ofertas, estado, carater, q)
    return _render(
        request,
        "partials/linhas.html",
        {
            "analise": analise,
            "analise_id": analise_id,
            "ofertas": ofertas,
            "filtros": {"estado": estado, "carater": carater, "q": q},
        },
    )


@app.post("/analise/{analise_id}/reverificar")
def reverificar(
    analise_id: str,
    api: UfrgsApi = Depends(get_api),
    store: AnalysisStore = Depends(get_store),
):
    analise = _carregar(store, analise_id)
    nova = analisar(analise.possibilidades, api)
    store.save(nova, analise_id)
    return RedirectResponse(f"/analise/{analise_id}", status_code=303)


@app.post("/analise/{analise_id}/chat", response_class=HTMLResponse)
def chat(
    request: Request,
    analise_id: str,
    mensagem: str = Form(...),
    store: AnalysisStore = Depends(get_store),
    service: ChatService | None = Depends(get_chat_service),
) -> HTMLResponse:
    analise = _carregar(store, analise_id)
    texto = mensagem.strip()

    if texto:
        historico = store.messages(analise_id)
        store.add_message(analise_id, "user", texto)
        if service is None:
            resposta = CHAT_NAO_CONFIGURADO
        else:
            try:
                resposta = service.reply(analise, historico, texto)
            except Exception:
                logger.exception("falha ao consultar o modelo")
                resposta = "Não consegui falar com o modelo agora. Tente novamente."
        store.add_message(analise_id, "assistant", resposta)

    return _render(
        request,
        "partials/chat.html",
        {
            "mensagens": store.messages(analise_id),
            "chat_configurado": service is not None,
        },
    )


def _carregar(store: AnalysisStore, analise_id: str) -> Analise:
    analise = store.get(analise_id)
    if analise is None:
        raise HTTPException(status_code=404, detail="análise não encontrada")
    return analise


def _render(
    request: Request, template: str, context: dict, status_code: int = 200
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name=template, context=context, status_code=status_code
    )


def _erro(request: Request, mensagem: str) -> HTMLResponse:
    return _render(request, "index.html", {"erro": mensagem}, status_code=400)
