# AGAL: obsługa zdalnych serwerów MCP (HTTP) — plan implementacji

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AGAL ma umieć zdefiniować w źródle i zainstalować do `.mcp.json` serwer MCP typu HTTP (`type` / `url` / `headers`), a nie tylko stdio (`command` / `args` / `env`).

**Architecture:** Parser manifestów `parse_mcp_manifest` w `agal/sources.py` dziś zostawia z serwera tylko `command/args/env/description`, więc serwer HTTP traci `url` i `headers`. Dodajemy jedną funkcję pomocniczą `_server_config()`, która dla wpisu z `url` zachowuje `type/url/headers`, a dla reszty zostawia dotychczasowe zachowanie. Używają jej dwa przypadki parsera: „Case 1” (`mcpServers`) i „Case 4” (płaska mapa serwerów). `install_mcp` w `agal/mcp.py` już teraz przepisuje config 1:1, więc nie wymaga zmian. Dostaje tylko test regresji.

**Tech Stack:** Python ≥ 3.10, PyYAML, `unittest` (testy: `python -m unittest discover -s tests`).

**Spec:** brak osobnego dokumentu. Wymagania są w sekcji „Global Constraints” poniżej. Kontekst: chcemy podpiąć do presetu AGAL serwer MCP itsaplan (`https://api.example.com/mcp`, nagłówek `Authorization: Bearer …`).

## Global Constraints

- Repo: `https://github.com/RepcaKeM/agal`, gałąź `main`. Pracuj na osobnej gałęzi, np. `feat/http-mcp`.
- Zero nowych zależności.
- Zachowanie dla serwerów stdio nie może się zmienić. Istniejące testy (29) muszą przechodzić bez modyfikacji.
- Serwer HTTP w wyniku parsera ma klucze: `type` (domyślnie `"http"`, gdy brak), `url`, opcjonalnie `headers` (tylko gdy niepuste) i `description`. **Nie** ma kluczy `command/args/env`.
- Wartości typu `${ITSAPLAN_TOKEN}` przechodzą bez zmian. AGAL niczego nie rozwija, robi to Claude Code przy odczycie `.mcp.json`.
- Nie ruszaj „Case 2” (pojedynczy serwer na top-level) ani „Case 3” (schema rejestru MCP z `packages`). To poza zakresem.
- Nie poprawiaj niezwiązanych rzeczy (np. README wspomina `agal add mcp <name> --local`, a CLI nie ma flagi `--local`). Zgłoś je w podsumowaniu, ale ich nie zmieniaj.

## Przed startem (sprawdzenie bazy)

Plan przygotowano na kodzie z commita zainstalowanego na serwerze 2026-09-18. Lokalne repo może być nowsze, więc najpierw upewnij się, że poprawiane fragmenty wyglądają tak samo:

```bash
git checkout main && git pull
git checkout -b feat/http-mcp
python -m unittest discover -s tests 2>&1 | tail -3      # oczekiwane: OK
grep -n '"command" in sval' agal/sources.py               # oczekiwane: 1 trafienie (Case 4)
grep -n 'get("command", "")' agal/cli.py agal/presets.py  # oczekiwane: po 1 trafieniu
```

Jeśli któreś trafienie się nie zgadza, dopasuj kroki do aktualnego kodu, zachowując zachowanie opisane w „Global Constraints”.

## Mapa plików

| Plik | Zmiana |
|---|---|
| `agal/sources.py` | nowa `_server_config()`, użyta w Case 1 i Case 4 w `parse_mcp_manifest` |
| `tests/test_sources.py` | 2 nowe testy parsera (JSON `mcpServers` + YAML płaska mapa) |
| `tests/test_mcp.py` | 1 test regresji: `install_mcp` zapisuje serwer HTTP do `.mcp.json` |
| `agal/cli.py` | `agal list mcp` pokazuje `url:` dla serwerów HTTP |
| `agal/presets.py` | etykieta w interaktywnym kreatorze presetu pokazuje `url:` |
| `README.md` | krótka sekcja: jak zdefiniować serwer HTTP w źródle |

---

### Task 1: Parser i instalacja serwerów HTTP

**Files:**
- Modify: `agal/sources.py` (nad `def parse_mcp_manifest`, Case 1 ok. l. 99–107, Case 4 ok. l. 158–167)
- Test: `tests/test_sources.py`, `tests/test_mcp.py`

**Interfaces:**
- Produces: `_server_config(sval: dict[str, Any]) -> dict[str, Any]` (prywatna, w `agal/sources.py`). Wynik `parse_mcp_manifest()` dla serwera HTTP to `{"type": str, "url": str, "headers"?: dict, "description": str}`.

- [ ] **Step 1: Napisz testy parsera, które nie przejdą**

W `tests/test_sources.py` wstaw poniższe dwie metody do klasy `TestSources`, bezpośrednio przed `def test_index_source_dir(self):`:

```python
    def test_parse_mcp_manifest_http_server(self):
        with tempfile.TemporaryDirectory() as td:
            mcp_json = Path(td) / "mcp.json"
            mcp_json.write_text(
                json.dumps({
                    "mcpServers": {
                        "remote": {
                            "type": "http",
                            "url": "https://example.com/mcp",
                            "headers": {"Authorization": "Bearer ${TOKEN}"},
                            "description": "Remote MCP server",
                        }
                    }
                }),
                encoding="utf-8",
            )
            servers = parse_mcp_manifest(mcp_json)
            self.assertEqual(servers["remote"], {
                "type": "http",
                "url": "https://example.com/mcp",
                "headers": {"Authorization": "Bearer ${TOKEN}"},
                "description": "Remote MCP server",
            })

    def test_parse_mcp_manifest_http_server_map_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "agal-mcp.yaml"
            manifest.write_text(
                "itsaplan:\n"
                "  url: https://example.com/mcp\n"
                "  headers:\n"
                "    Authorization: Bearer ${ITSAPLAN_TOKEN}\n",
                encoding="utf-8",
            )
            servers = parse_mcp_manifest(manifest)
            self.assertEqual(servers["itsaplan"]["type"], "http")
            self.assertEqual(servers["itsaplan"]["url"], "https://example.com/mcp")
            self.assertEqual(
                servers["itsaplan"]["headers"],
                {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
            )
            self.assertNotIn("command", servers["itsaplan"])
```

Drugi test celowo pomija `type`: sprawdza, że domyślnie ustawia się `"http"`.

- [ ] **Step 2: Dopisz test regresji instalacji**

W `tests/test_mcp.py` wstaw do klasy `TestMCP` bezpośrednio przed `@patch(...)` metody `test_install_and_uninstall_mcp_alias`:

```python
    @patch("agal.mcp.get_all_mcp_servers")
    def test_install_http_mcp_local(self, mock_get_servers):
        mock_get_servers.return_value = {
            "itsaplan": {
                "name": "itsaplan",
                "source": "mcp-source",
                "config": {
                    "type": "http",
                    "url": "https://example.com/mcp",
                    "headers": {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
                    "description": "itsaplan",
                },
            }
        }

        install_mcp("itsaplan", target_dir=self.target_dir, scope="local")

        with open(self.target_dir / LOCAL_MCP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["mcpServers"]["itsaplan"], {
            "type": "http",
            "url": "https://example.com/mcp",
            "headers": {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"},
        })
```

- [ ] **Step 3: Uruchom testy i potwierdź, że parser pada**

Run: `python -m unittest tests.test_sources tests.test_mcp -v 2>&1 | grep -E 'http|^Ran|^FAILED|^OK'`

Expected:
- `test_parse_mcp_manifest_http_server ... FAIL` (brak `type/url/headers` w wyniku)
- `test_parse_mcp_manifest_http_server_map_yaml ... ERROR` (`KeyError: 'itsaplan'`, bo Case 4 wymaga `command`)
- `test_install_http_mcp_local ... ok`. To oczekiwane: `install_mcp` już przepisuje config 1:1, a ten test pilnuje, żeby tak zostało.

- [ ] **Step 4: Implementacja minimalna**

W `agal/sources.py` wstaw bezpośrednio nad `def parse_mcp_manifest(`:

```python
def _server_config(sval: dict[str, Any]) -> dict[str, Any]:
    """Remote servers (url) keep type/url/headers; stdio servers keep command/args/env."""
    if "url" in sval:
        config: dict[str, Any] = {"type": sval.get("type", "http"), "url": sval["url"]}
        if sval.get("headers"):
            config["headers"] = sval["headers"]
    else:
        config = {
            "command": sval.get("command", ""),
            "args": sval.get("args", []),
            "env": sval.get("env", {}),
        }
    config["description"] = sval.get("description", "")
    return config


```

Case 1, zamień:

```python
                if isinstance(sval, dict):
                    servers[sname] = {
                        "command": sval.get("command", ""),
                        "args": sval.get("args", []),
                        "env": sval.get("env", {}),
                        "description": sval.get("description", ""),
                    }
```

na:

```python
                if isinstance(sval, dict):
                    servers[sname] = _server_config(sval)
```

Case 4, zamień:

```python
                if isinstance(sval, dict) and "command" in sval:
                    servers[sname] = {
                        "command": sval.get("command", ""),
                        "args": sval.get("args", []),
                        "env": sval.get("env", {}),
                        "description": sval.get("description", ""),
                    }
```

na:

```python
                if isinstance(sval, dict) and ("command" in sval or "url" in sval):
                    servers[sname] = _server_config(sval)
```

(`Any` jest już zaimportowane: `from typing import Any`.)

- [ ] **Step 5: Uruchom całą suitę**

Run: `python -m unittest discover -s tests 2>&1 | grep -E '^(Ran|OK|FAILED)'`
Expected: `Ran 32 tests` / `OK`. Na kodzie bazowym było 29, doszły 3 nowe.

- [ ] **Step 6: Commit**

```bash
git add agal/sources.py tests/test_sources.py tests/test_mcp.py
git commit -m "feat(mcp): support remote HTTP MCP servers (type/url/headers) in source manifests"
```

---

### Task 2: Czytelne wyświetlanie serwerów HTTP + README

**Files:**
- Modify: `agal/cli.py` (blok `if cat in ("mcp", "all"):`, ok. l. 276–284)
- Modify: `agal/presets.py` (pętla `mcp_labels`, ok. l. 274–281)
- Modify: `README.md` (po sekcji z komendami `agal source …`)

**Interfaces:**
- Consumes: kształt configu z Task 1 (`"url" in config` ⇒ serwer HTTP).

- [ ] **Step 1: `agal list mcp`**

W `agal/cli.py` zamień:

```python
            cmd = minfo.get("config", {}).get("command", "")
            print(f"  · {mname:<32} [{src}]  command: {cmd}")
```

na:

```python
            mcfg = minfo.get("config", {})
            if "url" in mcfg:
                print(f"  · {mname:<32} [{src}]  url: {mcfg['url']}")
            else:
                print(f"  · {mname:<32} [{src}]  command: {mcfg.get('command', '')}")
```

- [ ] **Step 2: Kreator presetu**

W `agal/presets.py` zamień:

```python
        cmd = minfo.get("config", {}).get("command", "")
        label = f"{mname:<24} [{src}]"
        if cmd:
            label = f"{label:<40} command: {cmd}"
```

na:

```python
        mcfg = minfo.get("config", {})
        label = f"{mname:<24} [{src}]"
        if "url" in mcfg:
            label = f"{label:<40} url: {mcfg['url']}"
        elif mcfg.get("command"):
            label = f"{label:<40} command: {mcfg['command']}"
```

- [ ] **Step 3: README**

W `README.md`, pod blokiem komend „Git Sources (Skills & MCP Repositories)”, dodaj:

````markdown
### Remote (HTTP) MCP servers

A source can define remote MCP servers next to stdio ones. Put an `agal-mcp.yaml`
(or `mcp.json` with `mcpServers`) in the source repo:

```yaml
itsaplan:
  type: http            # optional, defaults to http
  url: https://api.example.com/mcp
  headers:
    Authorization: "Bearer ${ITSAPLAN_TOKEN}"
```

Never commit secrets — use `${VAR}` placeholders; Claude Code expands them from
the environment when it reads `.mcp.json`.
````

- [ ] **Step 4: Weryfikacja ręczna end-to-end (izolowany AGAL_HOME)**

```bash
T=$(mktemp -d); export AGAL_HOME=$T/home HOME=$T/home
mkdir -p $T/src $T/proj
( cd $T/src && git init -q -b main && cat > agal-mcp.yaml <<'EOF'
itsaplan:
  type: http
  url: https://api.example.com/mcp
  headers:
    Authorization: "Bearer ${ITSAPLAN_TOKEN}"
EOF
  git add . && git -c user.name=t -c user.email=t@t commit -qm init )
cd $T/proj
python -m agal source add $T/src --name test-mcp </dev/null | tail -3
python -m agal list mcp | grep itsaplan
python -m agal add mcp itsaplan && cat .mcp.json
```

(Uruchamiaj z katalogu repo z `PYTHONPATH=<repo>` albo po `pip install -e .`.)

Expected:
- `source add` → `MCP: 1 discovered`
- `list mcp` → `· itsaplan  [test-mcp]  url: https://api.example.com/mcp`
- `.mcp.json` → `{"mcpServers": {"itsaplan": {"type": "http", "url": "…", "headers": {"Authorization": "Bearer ${ITSAPLAN_TOKEN}"}}}}`, **bez** `command`

- [ ] **Step 5: Testy + commit + push**

```bash
python -m unittest discover -s tests 2>&1 | grep -E '^(Ran|OK|FAILED)'   # 32 / OK
git add agal/cli.py agal/presets.py README.md
git commit -m "feat(mcp): show url for HTTP MCP servers; document remote servers"
git push -u origin feat/http-mcp
```

Następnie zmerguj do `main` (PR albo fast-forward). Wdrożenie na serwerze opisuje `docs/agal-itsaplan-mcp.md` w repo itsaplan i nie należy do tego planu.

---

## Self-review (wykonane przy pisaniu planu)

- Każde wymaganie z „Global Constraints” ma swój krok: parser → T1 S4, domyślny `type` → test YAML, `${VAR}` bez zmian → oba testy, stdio bez zmian → 29 starych testów w T1 S5.
- Kod z T1 i T2 został wypróbowany na kopii AGAL z serwera: 32/32 testów OK, `source add` → `list mcp` → `add mcp` → `prepare <preset>` dają poprawny `.mcp.json`.
