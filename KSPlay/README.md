# KSPlay

Fast, unified game environments for **GuanDan**, **DouDizhu**, and **Gin Rummy**.
KSPlay is the gameplay layer of [CardKS](https://github.com/Calix-L/CardKS):
the same rules power local experiments, reinforcement-learning rollouts, and
multiplayer rooms.

| Game | Players | Engine | Direct training path |
|---|---:|---|:---:|
| GuanDan | 4 | Python + optional Go source backend | ✓ |
| DouDizhu | 3 | Python | ✓ |
| Gin Rummy | 2 | Python, with attributed RLCard mechanics | ✓ |

## Quick start

```bash
git clone https://github.com/Calix-L/CardKS.git
cd CardKS/KSPlay
python -m venv .venv
source .venv/bin/activate
pip install -e .
ksplay smoke --game all
```

Use every game through one API:

```python
import ksplay

game = ksplay.make("guandan", seed=7, training_fast_path=True)
game.reset(["north", "east", "south", "west"])

while game.table.results is None:
    action_index = 0  # replace with your agent's choice
    game.step(game.current_seat, action_index)
```

`training_fast_path=True` keeps the rollout loop in process and avoids socket,
JSON, and trace-copying overhead.

### Training fast path

Use one in-process session per rollout worker:

```python
game = ksplay.make("guandan", seed=worker_seed, training_fast_path=True)
```

This is the same engine configuration used by the training path: step-back is
disabled, Gin Rummy trace recording is disabled, DouDizhu and Gin Rummy reuse
read-only action/wire values, and trusted action indices go directly to the
active engine handler. Keep `ksplay serve` for interactive rooms; rollout
workers should call `Session.step()` directly.

## Multiplayer service

One server hosts all three games:

```bash
ksplay serve --host 127.0.0.1 --port 8765
```

Clients exchange `create`, `join`, and `act` JSON commands and receive
seat-targeted game messages. A connection is bound to one room seat, so an
action cannot impersonate another player.

```json
{"command":"create","game":"guandan","players":["n","e","s","w"],"seed":7}
{"command":"join","room":"ROOM_ID","seat":0}
{"command":"act","room":"ROOM_ID","seat":0,"action":3}
```

The room begins accepting actions after every seat has joined. `action` is an
index into the current seat's `actionList` message.

## Repository map

```text
KSPlay/
├── src/ksplay/
│   ├── games/          # three self-contained rule engines
│   ├── server/         # one shared room and WebSocket service
│   ├── native/         # optional GuanDan Go source backend
│   └── session.py      # unified in-process API
├── tests/              # public API, security, and packaging checks
└── pyproject.toml
```

The Python engines work immediately after installation. The optional Go source
is kept in `src/ksplay/native/guandan-go` for deployments that want a native
GuanDan service; it is not required for the standard API.

## Development

```bash
pip install -e '.[dev]'
pytest -q
python -m build
```

KSPlay is released under Apache-2.0. The bundled RLCard subset retains its MIT
license in [`RLCard-MIT.md`](RLCard-MIT.md).
