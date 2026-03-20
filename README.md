# 🤖 Discord Recap Bot

Bot Discord tóm tắt nội dung chat theo khung giờ, sử dụng **Google Gemini AI**.

---

## ✨ Tính Năng

- `/recap start end` — Tóm tắt tất cả chat trong khoảng thời gian chỉ định
- `/recap start end user` — Chỉ tóm tắt tin nhắn của một người cụ thể
- Hỗ trợ nhiều định dạng giờ: `10h30`, `10:30`, `10h`
- Kết quả được post **công khai** lên kênh Discord với embed đẹp

---

## 🛠️ Cài Đặt

### 1. Cài dependencies

```bash
pip install -r requirements.txt
```

### 2. Tạo file `.env`

Sao chép file `.env.example` thành `.env` và điền các giá trị:

```bash
copy .env.example .env
```

```env
DISCORD_BOT_TOKEN=your_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Lấy Discord Bot Token

1. Vào [Discord Developer Portal](https://discord.com/developers/applications)
2. Tạo Application mới → vào tab **Bot**
3. Copy **Token**
4. Bật các **Privileged Intents**:
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**

### 4. Lấy Gemini API Key

Vào [Google AI Studio](https://aistudio.google.com/app/apikey) → Tạo API Key miễn phí.

### 5. Thêm Bot vào Server

Vào Developer Portal → **OAuth2 → URL Generator**:
- Scopes: `bot`, `applications.commands`
- Bot Permissions:
  - ✅ Read Messages / View Channels
  - ✅ Read Message History
  - ✅ Send Messages
  - ✅ Embed Links

### 6. Chạy Bot

```bash
python bot.py
```

---

## 💬 Sử Dụng

```
/recap start:10h30 end:12h30
/recap start:10h30 end:12h30 user:@HieuDQ
/recap start:9h00 end:17h00 date:yesterday
/recap start:9h end:18h date:2024-03-20
```

---

## 📁 Cấu Trúc Project

```
Discord Bot/
├── bot.py                   # Entry point
├── .env                     # Config (không commit lên git!)
├── requirements.txt
├── cogs/
│   └── recap.py             # Slash command /recap
├── services/
│   ├── message_fetcher.py   # Fetch messages từ Discord
│   ├── summarizer.py        # Gọi Gemini AI
│   └── formatter.py         # Tạo Discord Embed
└── utils/
    ├── time_parser.py       # Parse chuỗi giờ
    └── constants.py         # Hằng số cấu hình
```
