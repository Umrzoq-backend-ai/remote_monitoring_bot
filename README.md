# 🖥️ Screen Bot — Ekran Masofadan Boshqaruv

Telegram bot orqali kompyuter ekranini masofadan boshqarish loyihasi.

## 📦 Fayllar

```
screen-bot/
├── bot.py                  # Telegram bot
├── screen_control.sh       # Ekran boshqaruv skripti
├── requirements.txt        # Python kutubxonalar
├── .gitignore              # Git uchun
└── README.md               # Shu fayl
```

## 🚀 O'rnatish

```bash
# 1. Kutubxonalarni o'rnatish
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. Botni ishga tushirish
./venv/bin/python3 bot.py
```

## 🤖 Bot buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Asosiy menyu |
| `/status` | Hozirgi holat |
| `/lock` | Ekranni hozir quflash |
| `/lock_timer 4h` | Vaqtga quflash (keyin logout) |
| `/unlock` | Qulfni bekor qilish |
| `/sleep` | Uyqu rejimi |
| `/wake` | Ekranni yoqish |
| `/timeout 15m` | Timeout belgilash |
| `/off` | Timeoutni o'chirish |
| `/logout` | Kompyuterdan chiqish |

## ⏱️ Timeout formati

```
30s  — 30 soniya
15m  — 15 daqiqa
2h   — 2 soat
24h  — 24 soat
```

## 🔒 Xavfsizlik

- Bot faqat owner Telegram ID ga javob beradi
- Boshqa foydalanuvchilar ⛔ Access Denied ko'radi

## 💻 Terminal buyruqlari

```bash
screen-status          # holat
screen-lock            # quflash
screen-sleep           # uyqu
screen-wake            # yoqish
screen-timeout 15m     # timeout
screen-off             # timeout o'chirish
```
