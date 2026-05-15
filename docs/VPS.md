# Deploy otomasi harian ke VPS

## Jadwal (default WIB)

| Waktu | Job | Fungsi |
|-------|-----|--------|
| **07:00** | `morning` | Tarik **3** paper arXiv terbaru (cs.CL, cs.LG, cs.AI, stat.ML) → fetch → ringkasan LLM → dialog → render |
| **09:00** | `upload` | Upload **1** video dari antrian ke YouTube |
| **14:00** | `upload` | Upload video ke-2 |
| **20:00** | `upload` | Upload video ke-3 |

Antrian: `data/.schedule/state.json`

## Yang perlu Anda sediakan (untuk setup remote)

Kami **tidak** butuh password di chat. Gunakan **SSH key**:

| Item | Keterangan |
|------|------------|
| **IP** | `43.133.149.168` (dari panel Anda) |
| **User** | `ubuntu` |
| **SSH key** | Public key Anda ditambahkan ke `~ubuntu/.ssh/authorized_keys` |
| **Path repo** | Mis. `/home/ubuntu/paper2video` |
| **Timezone** | Default `Asia/Jakarta` — ubah di `config/schedule.json` atau env `PAPER2VIDEO_TZ` |

### File rahasia di server (jangan di Git)

Salin manual ke VPS (scp/rsync):

```
.env                          # ELEVENLABS_API_KEY, ANTHROPIC_API_KEY, TTS_PROVIDER
config/youtube/client_secret.json
config/youtube/token.json     # setelah auth.py
```

### API & layanan

- **Anthropic** — `ANTHROPIC_API_KEY` (ringkasan + dialog otomatis)
- **ElevenLabs** — `ELEVENLABS_API_KEY` (TTS)
- **YouTube OAuth** — sudah pernah `auth.py` di laptop; salin `token.json` ke VPS **atau** jalankan auth di VPS (lihat bawah)

## Install di VPS

```bash
ssh ubuntu@43.133.149.168

git clone https://github.com/<user>/paper2video.git
cd paper2video
chmod +x deploy/vps/install.sh
./deploy/vps/install.sh
```

Edit `.env`, salin OAuth YouTube, lalu:

```bash
# Dari laptop — salin token OAuth (jika sudah login di lokal)
scp config/youtube/token.json config/youtube/client_secret.json \
  ubuntu@43.133.149.168:~/paper2video/config/youtube/

# Atau auth di VPS dengan port forward:
# ssh -L 8080:localhost:8080 ubuntu@43.133.149.168
# python scripts/youtube/auth.py
```

## Cron

```bash
crontab -e
# Salin isi deploy/vps/crontab.example — sesuaikan path /home/ubuntu/paper2video
```

## Uji manual

```bash
cd ~/paper2video
./scripts/daily/run_cron.sh morning   # proses 3 paper (lama, ~30–90 menit)
./scripts/daily/run_cron.sh upload    # upload 1 video
```

Lihat log: `logs/morning-YYYYMMDD.log`, `logs/upload-YYYYMMDD.log`

## Konfigurasi

`config/schedule.json` — jumlah paper, query arXiv, jam upload, privacy YouTube.

Tambahkan paper yang sudah pernah diproses ke state agar tidak duplikat:

```bash
# State otomatis terisi; untuk seed manual edit data/.schedule/state.json
```

## OpenClaw (opsional)

Default memakai **Anthropic API** langsung. Untuk pakai OpenClaw:

```bash
export PAPER2VIDEO_USE_OPENCLAW=1
# openclaw gateway harus jalan
```

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| Cron tidak jalan | `chmod +x scripts/daily/run_cron.sh`; cek `crontab -l` |
| Upload kosong | Belum ada antrian — cek `morning` log; pastikan render sukses |
| OAuth expired | `python scripts/youtube/auth.py --reauth` |
| LLM gagal | Cek `ANTHROPIC_API_KEY` di `.env` |
