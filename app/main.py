from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.endpoints import router as api_router
from app.api.routers.registration import router as registration_router
from app.api.routers.loan_products import router as loan_products_router
from app.api.routers.ai_chat import router as ai_chat_router
from app.api.routers.powerbi import router as powerbi_router
# from app.api.routers import upload, analysis  # TODO: Fix imports
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(registration_router, prefix=settings.API_V1_PREFIX)
app.include_router(loan_products_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(powerbi_router, prefix=settings.API_V1_PREFIX)
# app.include_router(upload.router, prefix=settings.API_V1_PREFIX)  # TODO: Fix imports
# app.include_router(analysis.router, prefix=settings.API_V1_PREFIX)  # TODO: Fix imports


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:

    return RedirectResponse(url="/docs")


@app.get("/chat-ui", include_in_schema=False, response_class=HTMLResponse)
async def chat_ui() -> str:
    return """
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Credit Risk – AI Chat Test</title>
    <style>
      :root { color-scheme: light; }
      body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #0b1220; color: #e5e7eb; }
      .wrap { max-width: 980px; margin: 0 auto; padding: 24px; }
      .card { background: #111a2e; border: 1px solid #223055; border-radius: 14px; padding: 16px; }
      h1 { font-size: 18px; margin: 0 0 12px; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      label { display: block; font-size: 12px; color: #a5b4fc; margin-bottom: 6px; }
      input, textarea { width: 100%; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; border: 1px solid #243152; background: #0b1220; color: #e5e7eb; }
      textarea { min-height: 78px; resize: vertical; }
      .row { display: flex; gap: 10px; align-items: end; flex-wrap: wrap; }
      button { padding: 10px 12px; border-radius: 10px; border: 1px solid #2b3b66; background: #1b2a52; color: #e5e7eb; cursor: pointer; }
      button.primary { background: #4f46e5; border-color: #4f46e5; }
      button:disabled { opacity: 0.6; cursor: not-allowed; }
      .muted { font-size: 12px; color: #94a3b8; }
      .chat { margin-top: 12px; display: flex; flex-direction: column; gap: 10px; }
      .msg { padding: 10px 12px; border-radius: 12px; border: 1px solid #223055; max-width: 90%; white-space: pre-wrap; }
      .me { align-self: flex-end; background: #0f1a33; }
      .ai { align-self: flex-start; background: #0f2a24; border-color: #134e4a; }
      .err { background: #2a1420; border-color: #7f1d1d; }
      .bar { display:flex; gap:10px; align-items:center; justify-content:space-between; flex-wrap:wrap; }
      code { background: #0b1220; padding: 2px 6px; border-radius: 8px; border: 1px solid #223055; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <div class="bar">
          <h1>AI Chatbot Test (Gemini) – Không cần Swagger</h1>
          <div class="muted">URL: <code id="baseUrl"></code></div>
        </div>

        <div class="grid" style="margin-top: 10px;">
          <div>
            <label>Login (username/email)</label>
            <input id="loginUser" placeholder="admin@company.com" />
          </div>
          <div>
            <label>Password</label>
            <input id="loginPass" placeholder="••••••••" type="password" />
          </div>
          <div style="grid-column: 1 / -1;">
            <div class="row">
              <button class="primary" id="btnLogin">Đăng nhập lấy JWT</button>
              <span class="muted">JWT sẽ tự điền vào ô Token.</span>
            </div>
          </div>
          <div style="grid-column: 1 / -1;">
            <label>Token (Bearer)</label>
            <textarea id="token" placeholder="Dán access_token ở đây (không cần chữ 'Bearer')"></textarea>
          </div>
        </div>

        <hr style="border: none; border-top: 1px solid #223055; margin: 16px 0;" />

        <div class="grid">
          <div>
            <label>Session name</label>
            <input id="sessionName" value="Test session" />
          </div>
          <div>
            <label>Session ID</label>
            <input id="sessionId" placeholder="Nhấn Start để tạo" />
          </div>
          <div style="grid-column: 1 / -1;">
            <label>Initial context (tuỳ chọn)</label>
            <textarea id="initialContext" placeholder="VD: Customer ABC, Credit Score 720, Income 1.2B VND/năm"></textarea>
          </div>
          <div style="grid-column: 1 / -1;">
            <div class="row">
              <button id="btnStart" class="primary">Start session</button>
              <button id="btnLoadSessions">List sessions</button>
              <button id="btnClose">Close session</button>
              <span class="muted">API: <code>/api/v1/ai-chat/*</code></span>
            </div>
          </div>
        </div>

        <div class="chat" id="chat"></div>

        <div style="margin-top: 12px;" class="grid">
          <div style="grid-column: 1 / -1;">
            <label>Message</label>
            <textarea id="message" placeholder="Nhập câu hỏi..."></textarea>
          </div>
          <div style="grid-column: 1 / -1;">
            <div class="row">
              <button id="btnSend" class="primary">Send</button>
              <span class="muted">Enter để gửi, Shift+Enter xuống dòng.</span>
            </div>
          </div>
        </div>
      </div>

      <div class="muted" style="margin-top: 10px;">
        Gợi ý: nếu AI trả về lỗi <code>GEMINI_API_KEY not found</code>, hãy set env var <code>GEMINI_API_KEY</code> rồi restart server.
      </div>
    </div>

    <script>
      const $ = (id) => document.getElementById(id);
      const chat = $("chat");
      const base = window.location.origin;
      $("baseUrl").textContent = base;

      function addMsg(kind, text) {
        const div = document.createElement("div");
        div.className = "msg " + kind;
        div.textContent = text;
        chat.appendChild(div);
        div.scrollIntoView({ behavior: "smooth", block: "end" });
      }

      function tokenHeader() {
        const t = $("token").value.trim();
        return t ? { Authorization: "Bearer " + t } : {};
      }

      async function api(path, options = {}) {
        const res = await fetch(base + path, {
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...tokenHeader(),
            ...(options.headers || {}),
          },
        });
        const text = await res.text();
        let body = null;
        try { body = text ? JSON.parse(text) : null; } catch { body = text; }
        if (!res.ok) {
          const detail = body && body.detail ? body.detail : body;
          throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
        }
        return body;
      }

      $("btnLogin").onclick = async () => {
        try {
          const body = await api("/api/v1/auth/login", {
            method: "POST",
            body: JSON.stringify({
              username_or_email: $("loginUser").value.trim(),
              password: $("loginPass").value,
            }),
          });
          $("token").value = body.access_token || "";
          addMsg("ai", "Login OK. Token đã được điền.");
        } catch (e) {
          addMsg("err", "Login lỗi: " + e.message);
        }
      };

      $("btnStart").onclick = async () => {
        try {
          const body = await api("/api/v1/ai-chat/start", {
            method: "POST",
            body: JSON.stringify({
              session_name: $("sessionName").value.trim() || "Test session",
              initial_context: $("initialContext").value.trim() || null,
            }),
          });
          $("sessionId").value = body.session_id;
          chat.innerHTML = "";
          addMsg("ai", body.greeting_message || "Started.");
        } catch (e) {
          addMsg("err", "Start lỗi: " + e.message);
        }
      };

      $("btnSend").onclick = async () => {
        const msg = $("message").value;
        const sid = ($("sessionId").value || "").trim();
        if (!sid) { addMsg("err", "Bạn chưa có Session ID. Hãy Start session trước."); return; }
        if (!msg.trim()) return;
        $("message").value = "";
        addMsg("me", msg);
        try {
          const body = await api("/api/v1/ai-chat/send", {
            method: "POST",
            body: JSON.stringify({ session_id: sid, message: msg, customer_context: null }),
          });
          addMsg("ai", body.message || "");
        } catch (e) {
          addMsg("err", "Send lỗi: " + e.message);
        }
      };

      $("btnLoadSessions").onclick = async () => {
        try {
          const sessions = await api("/api/v1/ai-chat/sessions");
          const lines = (sessions || []).map(s => `#${s.session_id} - ${s.session_name} (${s.is_active ? "active" : "closed"})`);
          addMsg("ai", lines.length ? lines.join("\\n") : "Không có session nào.");
        } catch (e) {
          addMsg("err", "List sessions lỗi: " + e.message);
        }
      };

      $("btnClose").onclick = async () => {
        const sid = ($("sessionId").value || "").trim();
        if (!sid) { addMsg("err", "Không có Session ID."); return; }
        try {
          const summary = await api("/api/v1/ai-chat/close/" + sid, { method: "POST" });
          addMsg("ai", "Closed: " + JSON.stringify(summary));
        } catch (e) {
          addMsg("err", "Close lỗi: " + e.message);
        }
      };

      $("message").addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          $("btnSend").click();
        }
      });
    </script>
  </body>
</html>
""".strip()
