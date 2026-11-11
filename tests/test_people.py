"""Testes do cadastro de pessoas, códigos pessoais e comandos token (D-012, D-016)."""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import threading
from pathlib import Path

import pytest

from rslapp import cli, people


@pytest.fixture(autouse=True)
def isolated_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Aponta RSL_DATA_DIR para pasta temporária isolada em cada teste."""
    data_dir = tmp_path / "rsl_data"
    monkeypatch.setenv("RSL_DATA_DIR", str(data_dir))
    return data_dir


def _extract_code(stdout: str) -> str:
    match = re.search(r"(rsl_[A-Za-z0-9_-]+)", stdout)
    assert match is not None, f"Código rsl_ não encontrado em stdout: {stdout!r}"
    return match.group(1)


# D-012, D-016, D-007: token add cria a pessoa, exibe código rsl_ uma vez e grava só o SHA-256
def test_d016_token_add_guarda_so_o_hash(
    isolated_data_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not (isolated_data_dir / "auth").exists()

    cli.main(["token", "add", "maria"])
    out = capsys.readouterr().out
    code = _extract_code(out)
    assert code.startswith("rsl_")
    assert len(code) >= 4 + 32
    assert "não aparece de novo" in out

    people_file = isolated_data_dir / "auth" / "people.json"
    assert people_file.exists()
    raw_text = people_file.read_text(encoding="utf-8")
    assert code not in raw_text

    expected_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    records = json.loads(raw_text)
    assert len(records) == 1
    assert records[0]["id"] == "maria"
    assert records[0]["code_hash"] == expected_hash
    assert records[0]["created_at"] == records[0]["code_created_at"]
    assert records[0]["revoked_at"] is None

    person = people.get("maria")
    assert person is not None
    assert code not in repr(person)
    assert expected_hash not in repr(person)
    assert code not in str(person)
    assert expected_hash not in str(person)


# D-012, D-016: find_by_code acha pessoa ativa e devolve None para errado, revogada e vazio
def test_d012_d016_find_by_code_acha_ativa_e_recusa_errado_revogada_e_vazio(
    isolated_data_dir: Path,
) -> None:
    assert people.find_by_code("") is None
    assert not (isolated_data_dir / "auth").exists()

    code_maria = people.add("maria")
    found = people.find_by_code(code_maria)
    assert found is not None
    assert found.id == "maria"
    assert found.is_active is True

    assert people.find_by_code("rsl_codigo_errado_qualquer_1234567890") is None
    assert people.find_by_code("") is None
    assert people.find_by_code("sem_prefixo") is None

    people.revoke("maria")
    assert people.find_by_code(code_maria) is None
    revoked = people.get("maria")
    assert revoked is not None
    assert revoked.is_active is False
    assert revoked.revoked_at is not None


# D-016: token add repetido é recusado; --replace gera código novo, invalida o antigo e muda code_created_at
def test_d016_token_add_repetido_recusado_e_replace_troca_codigo_e_data(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli.main(["token", "add", "maria"])
    first_code = _extract_code(capsys.readouterr().out)
    before = people.get("maria")
    assert before is not None

    with pytest.raises(SystemExit) as exc_dup:
        cli.main(["token", "add", "maria"])
    assert exc_dup.value.code != 0
    err_dup = capsys.readouterr().err
    assert "maria" in err_dup
    assert first_code not in err_dup

    cli.main(["token", "add", "maria", "--replace"])
    second_code = _extract_code(capsys.readouterr().out)
    after = people.get("maria")
    assert after is not None
    assert second_code != first_code
    assert after.created_at == before.created_at
    assert after.code_created_at != before.code_created_at
    assert after.code_created_at > before.code_created_at
    assert people.find_by_code(first_code) is None
    assert people.find_by_code(second_code) is not None

    # Também reativa uma pessoa que havia sido revogada
    people.revoke("maria")
    assert people.find_by_code(second_code) is None
    cli.main(["token", "add", "maria", "--replace"])
    third_code = _extract_code(capsys.readouterr().out)
    reactivated = people.get("maria")
    assert reactivated is not None
    assert reactivated.revoked_at is None
    assert people.find_by_code(third_code) is not None


# D-016: token revoke marca revogada e mantém people/maria/; token list mostra revogada sem código nem hash
def test_d016_token_revoke_mantem_pasta_e_token_list_sem_codigo_nem_hash(
    isolated_data_dir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code_maria = people.add("maria")
    code_joao = people.add("joao")
    maria_dir = isolated_data_dir / "people" / "maria"
    maria_dir.mkdir(parents=True)
    (maria_dir / "log.md").write_text("# Log da Maria\n", encoding="utf-8")

    cli.main(["token", "revoke", "maria"])
    capsys.readouterr()

    assert maria_dir.exists()
    assert (maria_dir / "log.md").exists()

    cli.main(["token", "list"])
    list_out = capsys.readouterr().out
    lines = [line for line in list_out.strip().splitlines() if line.strip()]
    assert len(lines) == 3
    assert lines[0] == "pessoa\tcriada_em\tcodigo_desde\tsituacao"

    maria_line = next(line for line in lines if line.startswith("maria\t"))
    joao_line = next(line for line in lines if line.startswith("joao\t"))
    assert "revogada" in maria_line
    assert "ativa" in joao_line

    for person_rec in people.list_people():
        assert person_rec.code_hash not in list_out
    assert code_maria not in list_out
    assert code_joao not in list_out


# D-016: token add recusa "../x", "Maria", "" e id com 41 caracteres
@pytest.mark.parametrize("bad_id", ["../x", "Maria", "", "a" * 41, "-abc", "_abc", "joão"])
def test_d016_token_add_recusa_ids_invalidos(
    isolated_data_dir: Path,
    capsys: pytest.CaptureFixture[str],
    bad_id: str,
) -> None:
    with pytest.raises(ValueError, match="(?i)inválido"):
        people.add(bad_id, data_dir=isolated_data_dir)

    cli_args = ["token", "add", "--", bad_id] if bad_id.startswith("-") else ["token", "add", bad_id]
    with pytest.raises(SystemExit) as exc_info:
        cli.main(cli_args)
    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert "inválido" in err.lower()
    assert not (isolated_data_dir / "auth" / "people.json").exists()


# D-007, D-016: Duas chamadas de token add ao mesmo tempo (threads) não perdem nenhuma pessoa
def test_d007_d016_token_add_concorrente_em_threads_nao_perde_pessoas(
    isolated_data_dir: Path,
) -> None:
    total = 8
    barrier = threading.Barrier(total)
    codes: dict[str, str] = {}
    errors: list[BaseException] = []
    lock = threading.Lock()

    def _worker(idx: int) -> None:
        pid = f"pessoa-{idx}"
        try:
            barrier.wait(timeout=5)
            c = people.add(pid, data_dir=isolated_data_dir)
            with lock:
                codes[pid] = c
        except BaseException as exc:  # noqa: BLE001
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(total)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == []
    saved_ids = {p.id for p in people.list_people(data_dir=isolated_data_dir)}
    assert saved_ids == {f"pessoa-{i}" for i in range(total)}
    for pid, code in codes.items():
        found = people.find_by_code(code, data_dir=isolated_data_dir)
        assert found is not None and found.id == pid


# D-016, D-004: user purge --yes apaga cadastro e people/maria/ sem tocar em joao; sem --yes cancela se outro texto
def test_d016_user_purge_apaga_cadastro_e_pasta_e_cancela_sem_confirmacao(
    isolated_data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code_maria = people.add("maria")
    code_joao = people.add("joao")

    maria_dir = isolated_data_dir / "people" / "maria"
    joao_dir = isolated_data_dir / "people" / "joao"
    (maria_dir / "lists").mkdir(parents=True)
    (maria_dir / "lists" / "l-0001.json").write_text("{}", encoding="utf-8")
    (joao_dir / "lists").mkdir(parents=True)
    (joao_dir / "lists" / "l-0001.json").write_text("{}", encoding="utf-8")

    # Sem --yes, digitar outro texto cancela sem apagar nada
    monkeypatch.setattr(sys, "stdin", io.StringIO("outro-texto\n"))
    with pytest.raises(SystemExit) as exc_cancel:
        cli.main(["user", "purge", "maria"])
    assert exc_cancel.value.code != 0
    capsys.readouterr()
    assert people.get("maria") is not None
    assert people.find_by_code(code_maria) is not None
    assert (maria_dir / "lists" / "l-0001.json").exists()

    # Com --yes, apaga o cadastro e a pasta de maria sem tocar em joao
    cli.main(["user", "purge", "maria", "--yes"])
    capsys.readouterr()
    assert people.get("maria") is None
    assert people.find_by_code(code_maria) is None
    assert not maria_dir.exists()

    assert people.get("joao") is not None
    assert people.find_by_code(code_joao) is not None
    assert (joao_dir / "lists" / "l-0001.json").exists()

    # Sem --yes, digitar o id exato confirma e apaga
    monkeypatch.setattr(sys, "stdin", io.StringIO("joao\n"))
    cli.main(["user", "purge", "joao"])
    capsys.readouterr()
    assert people.get("joao") is None
    assert not joao_dir.exists()


# D-016: token list começa pelo cabeçalho pessoa criada_em codigo_desde situacao
def test_d016_token_list_comeca_pelo_cabecalho(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Sem pessoas cadastradas: imprime apenas o cabeçalho
    cli.main(["token", "list"])
    out_vazio = capsys.readouterr().out
    assert out_vazio.strip() == "pessoa\tcriada_em\tcodigo_desde\tsituacao"

    # Com pessoas cadastradas: primeira linha é o cabeçalho
    people.add("maria")
    people.add("joao")
    cli.main(["token", "list"])
    out_com_pessoas = capsys.readouterr().out
    linhas = out_com_pessoas.strip().splitlines()
    assert len(linhas) == 3
    assert linhas[0] == "pessoa\tcriada_em\tcodigo_desde\tsituacao"
    assert linhas[1].startswith("maria\t")
    assert linhas[2].startswith("joao\t")


