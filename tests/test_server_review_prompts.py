"""Testes dos prompts de tipos de revisão no servidor MCP (stdio e HTTP)."""

from __future__ import annotations

import pytest
from mcp import Client

from rslapp import server


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_d035_server_lists_all_five_prompts() -> None:
    async with Client(server.mcp) as client:
        prompts = await client.list_prompts()
        prompt_names = {p.name for p in prompts.prompts}
        expected = {
            "plan_search",
            "plan_scoping_review",
            "plan_integrative_review",
            "plan_systematic_review",
            "plan_bibliometric_study",
        }
        assert expected.issubset(prompt_names)


@pytest.mark.anyio
async def test_d035_server_executes_scoping_review_prompt() -> None:
    async with Client(server.mcp) as client:
        res = await client.get_prompt(
            "plan_scoping_review",
            {"topic": "Telessaúde", "population": "Adultos"},
        )
        assert res.messages
        content_text = res.messages[0].content.text
        assert "Telessaúde" in content_text
        assert "Adultos" in content_text
        assert "JBI" in content_text


@pytest.mark.anyio
async def test_d035_server_executes_integrative_review_prompt() -> None:
    async with Client(server.mcp) as client:
        res = await client.get_prompt(
            "plan_integrative_review",
            {"topic": "Enfermagem obstétrica", "guiding_question": "Práticas humanizadas"},
        )
        assert res.messages
        content_text = res.messages[0].content.text
        assert "Enfermagem obstétrica" in content_text
        assert "Práticas humanizadas" in content_text
        assert "Whittemore & Knafl" in content_text


@pytest.mark.anyio
async def test_d035_server_executes_systematic_review_prompt() -> None:
    async with Client(server.mcp) as client:
        res = await client.get_prompt(
            "plan_systematic_review",
            {"topic": "Tratamento de diabetes", "intervention": "Metformina"},
        )
        assert res.messages
        content_text = res.messages[0].content.text
        assert "Tratamento de diabetes" in content_text
        assert "Metformina" in content_text
        assert "Cochrane" in content_text


@pytest.mark.anyio
async def test_d035_server_executes_bibliometric_study_prompt() -> None:
    async with Client(server.mcp) as client:
        res = await client.get_prompt(
            "plan_bibliometric_study",
            {"topic": "Nanotecnologia em energia"},
        )
        assert res.messages
        content_text = res.messages[0].content.text
        assert "Nanotecnologia em energia" in content_text
        assert "VOSviewer" in content_text
