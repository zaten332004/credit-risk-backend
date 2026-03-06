# 📧 Email Configuration Guide

## Lý Do Chưa Nhận Email

Email service hiện tại đang chạy ở **DEMO MODE** (console logging). Để nhận email thực tế, bạn cần cấu hình một trong các backend sau:

---

## 🚀 Option 1: Mailgun (Khuyên Dùng - Dễ Nhất)

### Bước 1: Đăng ký Mailgun
1. Truy cập: https://www.mailgun.com/
2. Đăng ký tài khoản miễn phí (free tier có 100 emails/ngày)
3. Xác minh domain hoặc sử dụng sandbox domain

### Bước 2: Lấy API Key
- Vào dashboard → API Keys
- Copy **API Key** (bắt đầu với `key-`)
- Copy **Domain** (sandbox domain như `sandbox123abc.mailgun.org`)

### Bước 3: Cấu Hình .env
Mở file `.env` và thay đổi:

```env
EMAIL_BACKEND=mailgun
MAILGUN_API_KEY=key_xxxxxxxxxxxx
MAILGUN_DOMAIN=sandbox123abc.mailgun.org
SMTP_FROM=Credit Risk <postmaster@sandbox123abc.mailgun.org>
```

### Bước 4: Khởi Động Lại Server
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 📧 Option 2: Gmail SMTP

### Bước 1: Chuẩn Bị Tài Khoản Gmail
1. Bật 2-step verification: https://myaccount.google.com/security
2. Tạo **App Password** (không phải password Gmail thường):
   - Truy cập: https://myaccount.google.com/apppasswords
   - Chọn Mail, Windows Computer
   - Copy password được cấp

### Bước 2: Cấu Hình .env
```env
EMAIL_BACKEND=smtp
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=xxxx_xxxx_xxxx_xxxx  (app password từ bước 1)
SMTP_FROM=Credit Risk <your_email@gmail.com>
```

### Bước 3: Khởi Động Lại Server
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 🧪 Test Email Sending

Sau khi cấu hình, hãy:

1. Đăng ký user mới qua API:
```
POST http://127.0.0.1:8000/api/v1/auth/register/signup
Body:
{
  "username": "testuser",
  "email": "your_real_email@gmail.com",
  "password": "testpass123",
  "full_name": "Test User",
  "registration_type": "analyst",
  "phone": "0123456789"
}
```

2. Kiểm tra email inbox của bạn
3. Nếu không thấy, kiểm tra thư mục Spam/Promotions

---

## 🔍 Kiểm Tra Status

Mở server terminal, bạn sẽ thấy log:
- **DEMO MODE**: `📧 [DEMO MODE] Email would be sent to...`
- **Mailgun**: `✅ Email sent to...`
- **SMTP**: `✅ Email sent to...`
- **Lỗi**: `❌ SMTP Error: ...`

---

## ⚠️ Troubleshooting

**Lỗi: "Mailgun API key or domain not configured"**
- Kiểm tra `.env` có đúng format không
- Đảm bảo API key bắt đầu với `key-`
- Domain phải là sandbox hoặc verified domain

**Lỗi SMTP: "Invalid login"**
- Gmail: Đảm bảo dùng **App Password**, không phải password Gmail
- Outlook: Đảm bảo 2-step verification bật

**Lỗi SMTP: "Connection refused"**
- Kiểm tra SMTP_SERVER và SMTP_PORT đúng
- Đảm bảo server không bị firewall chặn port 587

---

## 📋 Email Verification Flow

Sau khi cấu hình thành công:

1. User đăng ký → Email verification được gửi
2. User click link trong email → Email được xác minh
3. Analyst: Auto-approved + approval email
4. Manager: Chờ admin approve + approval email

---

## 💡 Tips

- **Mailgun Free Tier**: 100 emails/ngày, unlimited domains
- **Gmail**: Unlimited emails, nhưng có rate limit
- **Testing**: Dùng Mailgun sandbox domain trước (no DNS setup needed)

---

## Current Status

```
EMAIL_BACKEND=console  ← Hiện tại (demo mode)
```

Để thay đổi, edit `.env` và set:
```
EMAIL_BACKEND=mailgun  ← Hoặc
EMAIL_BACKEND=smtp     ← Hoặc
```
