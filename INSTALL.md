# Installing Harlo

## What Is This

Harlo is an AI assistant that remembers how you work — not just what you said, but your momentum, your energy, your patterns. It sits between you and Claude (or any AI), tracking your cognitive state across sessions. It knows when you're in deep flow and shouldn't be interrupted, when you're burning out and need a break, and when you're stuck and need scaffolding. Your cognitive state is stored as a `.usda` file — the same format as your Houdini scenes. Yes, really.

---

## What You Need

- **Windows 10 or 11** (tested on Threadripper, works on any modern PC)
- **Python 3.12** (not 3.13 or 3.14 — USD requires exactly 3.12)
- **Claude Desktop** or **Claude Code**
- **~500MB disk space** (for USD, models, and Python packages)
- **Git** (for cloning the repo)

### Check Your Python Version

Open a terminal and run:
```
py -3.12 --version
```
You should see `Python 3.12.x`. If you don't have Python 3.12, download it from [python.org](https://www.python.org/downloads/).

---

## Install (Step by Step)

### 1. Clone the Repo

```bash
git clone https://github.com/JosephOIbrahim/harlo.git
cd harlo
```

### 2. Create a Python 3.12 Virtual Environment

```bash
py -3.12 -m venv .venv312
```

Activate it:
```bash
# Windows (Command Prompt)
.venv312\Scripts\activate

# Windows (Git Bash / MSYS2)
source .venv312/Scripts/activate

# macOS / Linux
source .venv312/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e .
pip install pydantic networkx xgboost scikit-learn joblib
pip install onnxruntime transformers
```

### 4. Build the Fast Memory Engine (Rust)

This compiles the Rust hot path that makes memory search super fast. It's optional — the system works without it, just slower.

```bash
pip install maturin
maturin develop -r
```

If this fails, don't worry. The system falls back to Python-only encoding.

### 5. Download the Semantic Model

```bash
python scripts/setup_semantic_encoder.py
```

This downloads the BGE embedding model (~27MB) used for semantic memory search.

### 6. Configure Claude Desktop

Open your Claude Desktop config file:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this to the `mcpServers` section:

```json
{
  "mcpServers": {
    "cognitive-twin": {
      "command": "C:\\path\\to\\cognitive-twin\\.venv312\\Scripts\\cognitive-twin.exe"
    }
  }
}
```

Replace `C:\\path\\to\\cognitive-twin` with the actual path where you cloned the repo.

### 7. Configure Claude Code

The repo already includes `.mcp.json`. If Claude Code doesn't pick it up automatically, add to your Claude Code settings:

```json
{
  "mcpServers": {
    "cognitive-twin": {
      "command": ".venv312/Scripts/cognitive-twin"
    }
  }
}
```

### 8. Verify the Install

```bash
python scripts/health_check.py
```

You should see something like:
```json
{
  "engine": "active",
  "stage_type": "real_usd",
  "predictor": true,
  "delegates_registered": 2,
  "observations_logged": 0
}
```

If `stage_type` shows `"mock"` instead of `"real_usd"`, that's fine — it means USD couldn't load, and the system is using its built-in fallback. Everything still works.

---

## First Run

1. **Restart Claude Desktop** (it needs to pick up the new MCP config)
2. Open a new conversation
3. The `twin_coach` tool should appear in Claude's tool list
4. Ask Claude anything — the twin evaluates your cognitive state in the background
5. After a few exchanges, check your cognitive state:

```bash
# See your state file (if using real USD)
type data\stages\cognitive_twin.usda

# Or run the health check
python scripts/health_check.py
```

Your cognitive state is now a USD file. Yes, like a Houdini scene.

---

## Troubleshooting

### "python312.dll conflicts with this version of Python"
You're running with the wrong Python version. Make sure you activated the `.venv312` environment:
```bash
.venv312\Scripts\activate
```

### "No module named pxr"
The USD Python path isn't set. This is expected on Python 3.13/3.14. The system falls back to its built-in mock stage. To use real USD, run from the `.venv312` environment.

### "twin_coach not found in Claude Desktop"
Restart Claude Desktop after changing the config file. The MCP tools only load on startup.

### "xgboost not found" or "scikit-learn not found"
Run:
```bash
pip install xgboost scikit-learn joblib
```

### "maturin develop failed"
The Rust hot path is optional. If it fails, the system uses Python-only encoding. Memory search will be a bit slower but everything works.

### The system shows `stage_type: "mock"` instead of `"real_usd"`
This means USD 26 couldn't load. The most common reason is running from the wrong Python version. Make sure you're using Python 3.12 (`.venv312`). If you don't have USD built, the mock backend is fully functional — you just won't get `.usda` files on disk.

---

## For Houdini Artists

If you work in Houdini, you're already familiar with everything this system uses:

- **Your cognitive state is stored as `.usda`** — the same format as your Houdini scenes. Open `data/stages/cognitive_twin.usda` in any text editor. You can read it.

- **The composition uses LIVRPS** — the same priority system as your USD layers in Solaris. Local overrides win. Payloads are lazy-loaded. Specializes is weakest.

- **The delegate pattern is Hydra** — the same pattern that routes your scene to Karma, Arnold, or RenderMan. Here it routes your cognitive state to Claude, Claude Code, or any future AI model.

- **If you can read a `.usda` file, you can read your own cognitive state.** Time samples are keyed by `exchange_index`. Delegate sublayers are in `data/stages/delegates/`. Composition resolves via standard USD mechanics.

- **When OpenExec Python bindings ship**, the cognitive state machines will run as native USD computation plugins — the same way FK constraints run in USD 26. The architecture is ready. Pixar just needs to ship the Python bindings.

---

## What's in the Box

```
data/stages/cognitive_twin.usda    Your cognitive state (real USD)
data/stages/delegates/             Per-delegate opinion sublayers
data/observations.db               Organic observation buffer
models/cognitive_predictor_v1.joblib  XGBoost predictor (trained on 10K sessions)
src/                               The cognitive engine (Python)
crates/hippocampus/                The fast memory engine (Rust)
```

---

*Harlo v3.3.1 — Patent Pending*
*Joseph O. Ibrahim, 2026*
