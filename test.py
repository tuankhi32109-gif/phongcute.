import asyncio
import aiohttp
import random
import os
import sys
import json
import time
import logging
import base64
import unicodedata
import re
from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
]

def build_super_properties():
    ua = random.choice(USER_AGENTS)
    sp = {
        "os": "Windows", "browser": "Chrome", "device": "", "system_locale": "vi-VN",
        "browser_user_agent": ua, "browser_version": "116.0.0.0", "os_version": "10",
        "referrer": "", "referring_domain": "", "referrer_current": "",
        "referring_domain_current": "", "release_channel": "stable",
        "client_build_number": random.randint(200000, 300000)
    }
    return base64.b64encode(json.dumps(sp).encode()).decode()

def sanitize_content(text, max_len=2000):
    text = unicodedata.normalize('NFC', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = re.sub(r'[\ud800-\udfff]', '', text)
    if not text.strip(): text = " "
    if len(text) > max_len: text = text[:max_len-3] + '...'
    return text

async def send_message(token, channel_id, content):
    content = sanitize_content(content)
    async with aiohttp.ClientSession() as sess:
        headers = {
            "Authorization": token,
            "User-Agent": random.choice(USER_AGENTS),
            "Content-Type": "application/json",
            "X-Super-Properties": build_super_properties(),
            "Origin": "https://discord.com"
        }
        msg_url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        payload = {"content": content, "tts": False}
        try:
            async with sess.post(msg_url, headers=headers, json=payload) as resp:
                if resp.status == 200: return True, 0
                elif resp.status == 429:
                    wait = float(resp.headers.get("Retry-After", "1"))
                    return False, max(wait, 0.5)
                elif resp.status in (401, 403):
                    return False, -1
                return False, 0
        except Exception:
            return False, 0

async def text_worker(token, channel_id, target_id, lines, delay, mode, stop_event):
    idx = 0
    total = len(lines)
    while not stop_event.is_set():
        msg = lines[idx % total]
        content = f"<@{target_id}> {msg}" if mode == 1 else msg
        success, wait = await send_message(token, channel_id, content)
        if success:
            log.info(f"[{token[:8]}] OK: {content[:40]}...")
            idx += 1
            await asyncio.sleep(delay)
        elif wait == -1:
            break
        elif wait > 0:
            await asyncio.sleep(wait)
        else:
            await asyncio.sleep(1)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tool Discord VIP</title>
    <style>
        body { font-family: Arial, sans-serif; background: #2f3136; color: white; padding: 20px; }
        .box { background: #36393f; padding: 20px; border-radius: 8px; max-width: 500px; margin: auto; }
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0 15px 0; background: #40444b; border: none; color: white; border-radius: 4px; box-sizing: border-box;}
        button { width: 100%; padding: 12px; background: #7289da; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 16px;}
        button:hover { background: #5b6eae; }
        label { font-size: 14px; color: #b9bbbe; font-weight: bold;}
        .btn-stop { background: #ed4245; margin-top: 10px; }
        .btn-stop:hover { background: #c93b3d; }
    </style>
</head>
<body>
    <div class="box">
        <h2>TOOL DISCORD BOT (WEB)</h2>
        <label>Chọn chức năng:</label>
        <select id="mode">
            <option value="1">1. Treo Tag</option>
            <option value="2">2. Treo Spam</option>
        </select>
        <label>Dán Token Discord vào đây (Mỗi dòng 1 token):</label>
        <textarea id="tokens" rows="3"></textarea>
        <label>Dán nội dung tin nhắn (Mỗi dòng 1 câu):</label>
        <textarea id="messages" rows="3"></textarea>
        <label>ID Kênh (Channel ID):</label>
        <input type="text" id="channel_id">
        <label>ID Thằng bị Tag (Chỉ dùng cho chức năng 1):</label>
        <input type="text" id="target_id">
        <label>Delay (Giây - VD: 1.5):</label>
        <input type="number" id="delay" value="1.5" step="0.1">
        <button onclick="startTool()">🚀 KHỞI CHẠY TOOL</button>
        <button class="btn-stop" onclick="stopTool()">🛑 DỪNG TOOL</button>
        <p id="status" style="color: #43b581; text-align: center; margin-top: 15px; font-weight: bold;"></p>
    </div>
    <script>
        async function startTool() {
            const data = {
                mode: document.getElementById('mode').value,
                tokens: document.getElementById('tokens').value,
                messages: document.getElementById('messages').value,
                channel_id: document.getElementById('channel_id').value,
                target_id: document.getElementById('target_id').value,
                delay: document.getElementById('delay').value
            };
            document.getElementById('status').innerText = "Đang khởi chạy...";
            const res = await fetch('/start', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
            const result = await res.json();
            document.getElementById('status').innerText = result.message;
        }
        async function stopTool() {
            document.getElementById('status').innerText = "Đang dừng tool...";
            const res = await fetch('/stop', { method: 'POST' });
            const result = await res.json();
            document.getElementById('status').innerText = result.message;
        }
    </script>
</body>
</html>
"""

global_stop_event = None

async def web_index(request):
    return web.Response(text=HTML_PAGE, content_type='text/html')

async def web_start(request):
    global global_stop_event
    try:
        data = await request.json()
        mode = int(data['mode'])
        tokens = [t.strip() for t in data['tokens'].strip().split('\n') if t.strip()]
        messages = [m.strip() for m in data['messages'].strip().split('\n') if m.strip()]
        channel_id = data['channel_id'].strip()
        target_id = data.get('target_id', '').strip()
        delay = float(data['delay'])

        if not tokens or not messages or not channel_id:
            return web.json_response({"message": "❌ Lỗi: Thiếu Token, Tin nhắn hoặc ID Kênh!"})

        if global_stop_event and not global_stop_event.is_set():
            global_stop_event.set()
            await asyncio.sleep(1)

        global_stop_event = asyncio.Event()
        asyncio.create_task(run_bg(tokens, channel_id, target_id, messages, delay, mode, global_stop_event))
        return web.json_response({"message": f"✅ Đã chạy! Đang dùng {len(tokens)} token."})
    except Exception as e:
        return web.json_response({"message": f"❌ Lỗi: {str(e)}"})

async def web_stop(request):
    global global_stop_event
    if global_stop_event and not global_stop_event.is_set():
        global_stop_event.set()
        return web.json_response({"message": "✅ Đã dừng tool!"})
    return web.json_response({"message": "⚠️ Tool đang không chạy."})

async def run_bg(tokens, channel_id, target_id, messages, delay, mode, stop_event):
    tasks = [text_worker(tok, channel_id, target_id, messages, delay, mode, stop_event) for tok in tokens]
    await asyncio.gather(*tasks)

# ĐÂY LÀ PHẦN QUAN TRỌNG ĐỂ RENDER CHẠY TỰ ĐỘNG
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app = web.Application()
    app.router.add_get('/', web_index)
    app.router.add_post('/start', web_start)
    app.router.add_post('/stop', web_stop)
    log.info(f"Web Server đang chạy tại cổng {port}")
    web.run_app(app, host='0.0.0.0', port=port)
