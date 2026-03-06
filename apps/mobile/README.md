# 📱 Credit Risk Mobile (Flutter)

Ứng dụng mobile Flutter cho hệ thống Credit Risk, sử dụng chung backend FastAPI (`apps/backend`) và API prefix `/api/v1`.

## Cấu trúc chính

- `pubspec.yaml` – cấu hình Flutter app và dependency.
- `lib/main.dart` – entrypoint, khởi tạo `ApiClient` và router.
- `lib/config/env.dart` – cấu hình `apiBaseUrl` (mặc định `http://localhost:8000/api/v1`).
- `lib/core/api_client.dart` – HTTP client đơn giản dùng package `http`.
- `lib/features/auth/data/auth_api.dart` – gọi `/auth/login` lấy JWT và thông tin user.
- `lib/features/auth/presentation/login_page.dart` – màn hình đăng nhập.
- `lib/features/dashboard/presentation/dashboard_page.dart` – dashboard mẫu sau khi login.
- `lib/routes/app_router.dart` – định nghĩa route (`/login`, `/dashboard`).

## Chạy backend

Trong `apps/backend`:

```powershell
.\run_dev.ps1
# hoặc
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Chạy Flutter app

Trong thư mục gốc repo:

```bash
cd apps/mobile
flutter pub get
flutter run
```

Mặc định app gọi về `http://localhost:8000/api/v1`.  
Nếu cần đổi base URL (ví dụ khi build production), có thể truyền qua compile-time constant:

```bash
flutter run --dart-define=API_BASE_URL=https://your-domain.com/api/v1
```

## Mở rộng tiếp theo (gợi ý)

- Thêm module:
  - Customers: list, chi tiết, chỉnh sửa.
  - Risk: score/analyze/batch.
  - Portfolio: KPI, risk distribution, trend.
  - AI Chat: tích hợp các endpoint `/ai-chat`.
- Chuẩn hoá state management (Provider/Bloc/Riverpod) nếu app phức tạp hơn.

