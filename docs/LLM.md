# Provider LLM (ringkasan & dialog)

Langkah **C** dan **D** pipeline (`llm.py`, `run_e2e.py`, cron VPS) memakai salah satu:

| Provider | Env | Model default | Catatan |
|----------|-----|---------------|---------|
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | Default lama |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` | ChatGPT API |
| `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat` | API resmi [platform.deepseek.com](https://platform.deepseek.com) |
| `opencode` | `OPENCODE_API_KEY` | `deepseek-v4-flash-free` | Key dari [opencode.ai](https://opencode.ai) → API Keys (Zen/Go) |

Atau **OpenClaw** (`PAPER2VIDEO_USE_OPENCLAW=1`) — model apa pun yang Anda set di OpenClaw.

## OpenCode (key dari screenshot Anda)

Key `sk-cCiu...` di dashboard **OpenCode → API Keys** **bukan** key DeepSeek resmi. Pakai:

```bash
LLM_PROVIDER=opencode
OPENCODE_API_KEY=sk-...    # salin dari OpenCode dashboard
LLM_MODEL=deepseek-v4-flash-free
```

Endpoint default (Go): `https://opencode.ai/zen/go/v1`  
Model gratis lain: lihat [OpenCode Zen docs](https://opencode.ai/docs/zen).

Zen (bukan Go): `LLM_BASE_URL=https://opencode.ai/zen/v1`

## Konfigurasi

**`.env`** (prioritas tinggi):

```bash
LLM_PROVIDER=openai          # anthropic | openai | deepseek
OPENAI_API_KEY=sk-...
# LLM_MODEL=gpt-4o            # opsional override model
```

**`config/schedule.json`** (fallback):

```json
"llm": {
  "provider": "deepseek",
  "model": "deepseek-chat",
  "base_url": "https://api.deepseek.com"
}
```

## Contoh DeepSeek

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
```

Base URL default: `https://api.deepseek.com` (Chat Completions).

## Contoh OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

## OpenCode / tool lain

Repo ini memanggil API **langsung** (HTTP), bukan lewat binary OpenCode Go.  
Jika OpenCode hanya sebagai **client** ke OpenAI/DeepSeek, cukup pakai key yang sama + `LLM_PROVIDER` di atas.

Integrasi native OpenCode CLI belum ada — gunakan OpenClaw (`PAPER2VIDEO_USE_OPENCLAW=1`) jika ingin agent eksternal.

## Uji

```bash
python scripts/run_e2e.py 1706.03762 --force-llm
# hanya C+D jika paper-summary & dialog sudah ada — hapus dulu atau --force-llm
```
