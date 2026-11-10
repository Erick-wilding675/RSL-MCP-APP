"""Testes do armazenamento de clientes e tokens OAuth e do verificador por requisição."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from mcp.server.auth.middleware.auth_context import AuthenticatedUser, auth_context_var
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from rslapp import people
from rslapp.auth import (
    AuthStore,
    RSLAccessToken,
    RSLAuthorizationCode,
    RSLRefreshToken,
    RSLTokenVerifier,
    current_person_id,
    hash_token,
)


# D-016, NFR-03: Tokens ficam só como hash SHA-256 em <RSL_DATA_DIR>/auth/, e client_secret persiste em clients.json
def test_d016_nfr03_auth_store_persists_only_sha256_hashes_on_disk(tmp_path: Path) -> None:
    personal_code = people.add("ana", data_dir=tmp_path)
    store = AuthStore(data_dir=tmp_path)

    client_secret_plain = "fake-client-secret-123"
    client_info = OAuthClientInformationFull(
        client_id="client-1",
        client_secret=client_secret_plain,
        redirect_uris=[AnyUrl("http://localhost:3030/callback")],
        client_name="Claude",
    )
    store.save_client(client_info)

    # Novo AuthStore na mesma pasta recupera o client_secret (sobrevive a reinício do servidor)
    restarted_store = AuthStore(data_dir=tmp_path)
    reloaded_client = restarted_store.get_client("client-1")
    assert reloaded_client is not None
    assert reloaded_client.client_secret == client_secret_plain

    oauth_token = store.issue_token_pair(
        person_id="ana",
        client_id="client-1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )
    assert oauth_token.access_token
    assert oauth_token.refresh_token

    auth_dir = tmp_path / "auth"
    assert auth_dir.is_dir()

    for file_path in auth_dir.iterdir():
        if file_path.is_file():
            content = file_path.read_text(encoding="utf-8")
            assert oauth_token.access_token not in content
            assert oauth_token.refresh_token not in content
            assert personal_code not in content

    tokens_content = (auth_dir / "tokens.json").read_text(encoding="utf-8")
    assert hash_token(oauth_token.access_token) in tokens_content
    assert hash_token(oauth_token.refresh_token) in tokens_content


# D-016, D-007: Ao gravar tokens.json, apaga tokens de acesso vencidos e tokens de pessoas revogadas ou inexistentes
def test_d016_tokens_json_prunes_expired_access_tokens_and_revoked_or_missing_people(
    tmp_path: Path,
) -> None:
    now_box = [datetime.now(timezone.utc) + timedelta(seconds=5)]
    people.add("ana", data_dir=tmp_path)
    people.add("beto", data_dir=tmp_path)
    people.add("carlos", data_dir=tmp_path)

    store = AuthStore(
        data_dir=tmp_path,
        access_token_minutes=60,
        clock=lambda: now_box[0],
    )

    ana_t1 = store.issue_token_pair(
        person_id="ana",
        client_id="c1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )
    beto_t1 = store.issue_token_pair(
        person_id="beto",
        client_id="c1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )
    carlos_t1 = store.issue_token_pair(
        person_id="carlos",
        client_id="c1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )
    assert ana_t1.refresh_token is not None
    assert beto_t1.refresh_token is not None
    assert carlos_t1.refresh_token is not None

    # Avança 61 minutos (access token de ana vence), revoga beto e remove carlos
    now_box[0] = now_box[0] + timedelta(minutes=61)
    people.revoke("beto", data_dir=tmp_path)
    people.purge("carlos", data_dir=tmp_path)

    # Ao gravar novamente (por exemplo, emitindo novo par para ana), tokens.json é limpo
    ana_t2 = store.issue_token_pair(
        person_id="ana",
        client_id="c1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )
    assert ana_t2.refresh_token is not None

    tokens_content = (tmp_path / "auth" / "tokens.json").read_text(encoding="utf-8")
    # Access token vencido de ana foi apagado do arquivo
    assert hash_token(ana_t1.access_token) not in tokens_content
    # Refresh token válido de ana (sem vencimento) e o novo par de ana permanecem
    assert hash_token(ana_t1.refresh_token) in tokens_content
    assert hash_token(ana_t2.access_token) in tokens_content
    assert hash_token(ana_t2.refresh_token) in tokens_content
    # Todos os tokens de beto (revogado) e carlos (inexistente) foram apagados do arquivo
    assert hash_token(beto_t1.access_token) not in tokens_content
    assert hash_token(beto_t1.refresh_token) not in tokens_content
    assert hash_token(carlos_t1.access_token) not in tokens_content
    assert hash_token(carlos_t1.refresh_token) not in tokens_content


# D-015, D-016: Verificação por requisição valida hash, vencimento, resource e vínculo com a pessoa
@pytest.mark.anyio
async def test_d015_d016_token_verifier_checks_expiry_and_resource(tmp_path: Path) -> None:
    now_box = [datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)]
    people.add("ana", data_dir=tmp_path)

    # Ajusta o relógio simulado para após o cadastro da pessoa
    now_box[0] = datetime.now(timezone.utc) + timedelta(seconds=5)
    store = AuthStore(
        data_dir=tmp_path,
        access_token_minutes=60,
        clock=lambda: now_box[0],
    )
    verifier = RSLTokenVerifier(store, resource_server_url="http://127.0.0.1:8000/mcp")

    oauth_token = store.issue_token_pair(
        person_id="ana",
        client_id="client-1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )

    verified = await verifier.verify_token(oauth_token.access_token)
    assert verified is not None
    assert verified.person_id == "ana"
    assert verified.scopes == ["rsl"]

    # Resource divergente é recusado
    wrong_verifier = RSLTokenVerifier(store, resource_server_url="https://outro.exemplo.org/mcp")
    assert await wrong_verifier.verify_token(oauth_token.access_token) is None

    # Avança o relógio além dos 60 minutos: access token vence
    now_box[0] = now_box[0] + timedelta(minutes=61)
    assert await verifier.verify_token(oauth_token.access_token) is None


# D-016: Refresh token não tem vencimento e gira a cada uso, invalidando o anterior
@pytest.mark.anyio
async def test_d016_refresh_token_rotates_and_invalidates_previous(tmp_path: Path) -> None:
    people.add("ana", data_dir=tmp_path)
    store = AuthStore(data_dir=tmp_path)
    verifier = RSLTokenVerifier(store, resource_server_url="http://127.0.0.1:8000/mcp")

    initial = store.issue_token_pair(
        person_id="ana",
        client_id="client-1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )
    assert initial.refresh_token is not None

    loaded_refresh = store.verify_refresh_token(initial.refresh_token)
    assert loaded_refresh is not None
    assert loaded_refresh.expires_at is None

    rotated = store.rotate_refresh_token(
        old_refresh_token_hash=hash_token(initial.refresh_token),
        scopes=["rsl"],
    )
    assert rotated is not None
    assert rotated.access_token != initial.access_token
    assert rotated.refresh_token is not None
    assert rotated.refresh_token != initial.refresh_token

    # O refresh token antigo não funciona uma segunda vez
    assert store.verify_refresh_token(initial.refresh_token) is None
    assert (
        store.rotate_refresh_token(
            old_refresh_token_hash=hash_token(initial.refresh_token),
            scopes=["rsl"],
        )
        is None
    )

    # Os novos tokens funcionam normalmente
    assert await verifier.verify_token(rotated.access_token) is not None
    assert store.verify_refresh_token(rotated.refresh_token) is not None


# D-016: Revogar ou trocar o código pessoal corta imediatamente o acesso e a renovação
@pytest.mark.anyio
async def test_d016_revoke_and_replace_code_invalidate_tokens_immediately(tmp_path: Path) -> None:
    people.add("ana", data_dir=tmp_path)
    store = AuthStore(data_dir=tmp_path)
    verifier = RSLTokenVerifier(store, resource_server_url="http://127.0.0.1:8000/mcp")

    first_tokens = store.issue_token_pair(
        person_id="ana",
        client_id="client-1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )
    assert first_tokens.refresh_token is not None
    assert await verifier.verify_token(first_tokens.access_token) is not None

    # Trocar o código (token add --replace) invalida os tokens emitidos antes de code_created_at
    people.replace_code("ana", data_dir=tmp_path)
    assert await verifier.verify_token(first_tokens.access_token) is None
    assert store.verify_refresh_token(first_tokens.refresh_token) is None
    assert (
        store.rotate_refresh_token(
            old_refresh_token_hash=hash_token(first_tokens.refresh_token),
        )
        is None
    )

    # Um novo token emitido após a troca de código volta a funcionar
    second_tokens = store.issue_token_pair(
        person_id="ana",
        client_id="client-1",
        scopes=["rsl"],
        resource="http://127.0.0.1:8000/mcp",
    )
    assert second_tokens.refresh_token is not None
    assert await verifier.verify_token(second_tokens.access_token) is not None

    # Revogar a pessoa (token revoke) corta o acesso imediatamente sem reiniciar nada
    people.revoke("ana", data_dir=tmp_path)
    assert await verifier.verify_token(second_tokens.access_token) is None
    assert store.verify_refresh_token(second_tokens.refresh_token) is None


# D-015, D-016: current_person_id devolve None em stdio e o person_id autenticado em HTTP
def test_d015_current_person_id_reads_auth_context() -> None:
    assert current_person_id() is None

    access_token = RSLAccessToken(
        token="***",
        client_id="client-1",
        scopes=["rsl"],
        expires_at=9999999999,
        resource="http://127.0.0.1:8000/mcp",
        person_id="ana",
    )
    reset_token = auth_context_var.set(AuthenticatedUser(access_token))
    try:
        assert current_person_id() == "ana"
    finally:
        auth_context_var.reset(reset_token)

    assert current_person_id() is None


# NFR-03: Nenhum repr() ou str() de objetos de autenticação expõe código, token ou hash
def test_nfr03_auth_models_repr_never_leaks_secrets() -> None:
    raw_secret = "tok-secreto-abc-987654"
    secret_hash = hash_token(raw_secret)

    access = RSLAccessToken(
        token=raw_secret,
        client_id="client-1",
        scopes=["rsl"],
        expires_at=123456,
        resource="http://127.0.0.1:8000/mcp",
        person_id="ana",
    )
    access._token_hash = secret_hash

    refresh = RSLRefreshToken(
        token=raw_secret,
        client_id="client-1",
        scopes=["rsl"],
        person_id="ana",
    )
    refresh._token_hash = secret_hash

    auth_code = RSLAuthorizationCode(
        code=raw_secret,
        scopes=["rsl"],
        expires_at=123456.0,
        client_id="client-1",
        code_challenge="challenge-secreto-xyz",
        redirect_uri=AnyUrl("http://localhost:3030/callback"),
        redirect_uri_provided_explicitly=True,
        person_id="ana",
    )

    for obj in (access, refresh, auth_code):
        for text in (repr(obj), str(obj)):
            assert raw_secret not in text
            assert secret_hash not in text
            assert "challenge-secreto-xyz" not in text
