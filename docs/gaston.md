# Gaston — Multi-Agent Coding Orchestrator

## What

A Go CLI that receives a high-level coding task, decomposes it into subtasks using a manager agent, spawns parallel worker agents (each with a different NVIDIA free-tier API key), and aggregates the results. All agents use GLM-5.2 via NVIDIA's free API.

Inspiration: Kilocode's old Orchestrator mode (Boomerang Tasks) — decompose → spawn specialists → aggregate.

## Architecture

```
gaston/
├── cmd/gaston/main.go           # CLI (cobra): run, session, config
├── internal/
│   ├── agent/
│   │   ├── loop.go              # Shared agent loop: think → act → observe
│   │   ├── manager.go           # Orchestrator: decompose → spawn → aggregate
│   │   └── worker.go            # Worker: receives subtask, runs tool loop
│   ├── provider/
│   │   └── nvidia/
│   │       └── client.go        # OpenAI-compatible HTTP client for NVIDIA
│   ├── tool/
│   │   ├── registry.go          # Tool interface + registry
│   │   ├── file.go              # read_file, write_file, edit_file
│   │   ├── search.go            # glob, grep
│   │   ├── shell.go             # shell (yolo mode — no blocking)
│   │   └── web.go               # web_fetch
│   ├── keyring/
│   │   └── pool.go              # API key pool, round-robin
│   ├── config/
│   │   └── config.go            # YAML config + env vars
│   └── session/
│       └── store.go             # JSON save/resume
├── config.example.yaml
├── go.mod / go.sum
├── Makefile
└── README.md
```

## Agent Loop (core pattern)

Both manager and workers share `RunLoop()`:

```
messages = [system_prompt, user_task]
for turn in 0..maxTurns:
    resp = nvidia.Chat(messages, tools)
    append assistant message
    if no tool_calls: return content  // done
    for each tool_call:
        result = tools.Execute(name, args)
        append tool result message
    // loop back (observe → think)
```

- Max turns: 25 (prevents infinite loops)
- Temperature: 0.3 for deterministic output
- Cold starts: 300s HTTP timeout (NVIDIA free tier)

## Orchestrator Flow

```
Manager receives task: "Build a REST API for todos"
  │
  ├─ Phase 1: DECOMPOSE
  │   Manager sends task to GLM-5.2 with a decomposition prompt
  │   Returns structured subtask list: ["Design data model", "Create router", ...]
  │
  ├─ Phase 2: EXECUTE (parallel goroutines, max_workers concurrency limit)
  │   For each subtask:
  │     key = keyPool.Acquire()         // round-robin from API key pool
  │     worker = NewWorker(subtask, key)
  │     result = worker.Run(ctx)        // runs full agent loop with tools
  │     keyPool.Release(key)
  │
  └─ Phase 3: AGGREGATE
      Manager sends all results back to LLM: "Synthesize these into a final answer"
```

## Tool System

All 7 tools follow the OpenAI function-calling schema pattern:

| Tool | Schema args | Description |
|------|------------|-------------|
| `read_file` | `path, offset?, limit?` | Read file contents |
| `write_file` | `path, content` | Create/overwrite file (workspace-scoped) |
| `edit_file` | `path, search, replace` | Find & replace (first occurrence) |
| `glob` | `pattern, path?` | File pattern search |
| `grep` | `pattern, path?, glob?` | Content search via regex |
| `shell` | `command, cwd?` | Run shell command (YOLO — no blocking) |
| `web_fetch` | `url` | HTTP GET, returns text (50KB cap) |

Shell is fully permissive — the user explicitly chose yolo mode.

## NVIDIA Provider

Reuses the exact pattern from `probe.py`:
- Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
- Auth: `Bearer <key>`
- Format: Standard OpenAI chat completions with `tools` support
- Default model: `z-ai/glm-5.2`
- Retry: 429/5xx with backoff (2s, 5s, 12s)
- Cost: All free tier — `$0.00`

## Key Pool

Multiple NVIDIA API keys, loaded from:
1. Config file (`api_keys:` array in YAML)
2. Env vars: `NVIDIA_API_KEY`, `NVIDIA_API_KEY_1`, `NVIDIA_API_KEY_2`, ...

Round-robin allocation: `nextIndex = (lastIndex + 1) % len(keys)`. Keys are acquired for the duration of a worker task and released when done.

## Configuration

```yaml
# config.yaml
api_keys:
  - "nvapi-..."
  - "nvapi-..."

model:
  manager: "meta/llama-3.3-70b-instruct"   # smarter for decomposition
  worker: "z-ai/glm-5.2"                   # default worker

workspace: "."
max_workers: 5          # max concurrent workers
max_turns: 25           # turns per agent loop
```

## CLI

```bash
gaston run "Build a REST API for a todo app in Go"
gaston run --workers 3 --model meta/llama-3.3-70b-instruct "Add auth to this project"
gaston session list
gaston session resume <id>
gaston config init    # generate default config.yaml
```

## Session Storage

JSON files in `~/.gaston/sessions/<id>.json` — same pattern as geo-tool's `data/audits/`. Each session stores: task, subtask plan, per-worker results, final output, timestamps, model used, total tokens.

## Dependencies

- `github.com/spf13/cobra` — CLI framework
- `gopkg.in/yaml.v3` — YAML config parsing
- Stdlib: `net/http`, `encoding/json`, `sync`, `context`, `os/exec`, `regexp`, `path/filepath`

## Implementation Order

| Step | What | Files |
|------|------|-------|
| 1 | Go module + directory structure | `go.mod`, all dirs |
| 2 | Config + key pool | `internal/config/`, `internal/keyring/` |
| 3 | NVIDIA client | `internal/provider/nvidia/` |
| 4 | Tool registry + all 7 tools | `internal/tool/` |
| 5 | Agent loop | `internal/agent/loop.go` |
| 6 | Worker | `internal/agent/worker.go` |
| 7 | Manager (decompose + aggregate) | `internal/agent/manager.go` |
| 8 | Session store | `internal/session/` |
| 9 | CLI (cobra commands) | `cmd/gaston/main.go` |
| 10 | Smoke test | End-to-end: "write hello world in Go" |

## Verification

1. `gaston run "Create a hello.go file that prints 'hello from gaston'"` → file exists, compiles, prints correct string
2. `gaston run "What files are in this directory?"` → manager decomposes, worker uses glob/ls, returns file list
3. With 2+ API keys configured, verify both keys are used (check round-robin allocation)
4. `gaston session list` → shows completed session
5. `gaston session resume <id>` → shows the task and results

## New Repo Setup

```bash
mkdir ~/gaston && cd ~/gaston
git init
go mod init github.com/<github-username>/gaston
# Then implement steps 1-10 above
```
