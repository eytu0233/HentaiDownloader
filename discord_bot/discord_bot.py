"""
Discord 機器人 — 接收網址並觸發下載
token / channel_id 從 discord_bot/config.json 讀取：
  {
    "discord_bot": {
      "token": "YOUR_BOT_TOKEN",
      "channel_id": 123456789012345678,
      "allowed_user_ids": []
    }
  }

支援指令（前綴 !）：
  !ping    確認機器人在線
  !help    顯示說明

外部呼叫：
  bot = DiscordBot("discord_bot/config.json")
  bot.register_url_callback(fn)   # fn(url: str) -> None
  bot.start()                     # 背景執行緒啟動
  bot.notify("訊息")              # 傳送通知到指定頻道
  bot.stop()                      # 停止機器人
"""

import asyncio
import json
import logging
import os
import re
import threading
from typing import Callable, Optional

import discord
from discord.ext import commands

_logger = logging.getLogger('DiscordBot')

_URL_PATTERN = re.compile(r'https?://\S+')


class DiscordBot:
    def __init__(self, config_path: str = "discord_bot/config.json"):
        self._config_path = config_path
        self._token: str = ""
        self._channel_id: int = 0
        self._allowed_user_ids: list = []
        self._prefix: str = "!"

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._client: Optional[commands.Bot] = None
        self._ready_event = threading.Event()

        self._url_cb: Optional[Callable[[str], None]] = None

        self._load_config()
        self._build_client()

    def _load_config(self):
        if not os.path.exists(self._config_path):
            raise FileNotFoundError(f"找不到設定檔：{self._config_path}")
        with open(self._config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        discord_cfg = cfg.get("discord_bot", {})
        self._token = discord_cfg.get("token", "")
        self._channel_id = int(discord_cfg.get("channel_id", 0))
        self._allowed_user_ids = [int(uid) for uid in discord_cfg.get("allowed_user_ids", [])]
        if not self._token:
            raise ValueError("discord_bot/config.json 中 discord_bot.token 未設定")

    def register_url_callback(self, fn: Callable[[str], None]):
        """fn(url: str) — 當偵測到網址時呼叫"""
        self._url_cb = fn

    def _is_allowed(self, author_id: int) -> bool:
        if not self._allowed_user_ids:
            return True
        return author_id in self._allowed_user_ids

    def _build_client(self):
        intents = discord.Intents.default()
        if hasattr(intents, 'message_content'):
            intents.message_content = True
        self._client = commands.Bot(command_prefix=self._prefix, intents=intents)
        self._client.remove_command("help")

        @self._client.event
        async def on_ready():
            _logger.info(f"[DiscordBot] 已登入：{self._client.user} (id={self._client.user.id}), channel_id={self._channel_id}")
            self._ready_event.set()
            await self._send("✅ 漫畫下載機器人已上線，請貼上漫畫網址開始下載")

        @self._client.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.CommandNotFound):
                await ctx.send(f"❓ 未知指令，輸入 `{self._prefix}help` 查看可用指令")
            else:
                await ctx.send(f"❌ 錯誤：{error}")

        @self._client.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return
            if self._channel_id and message.channel.id != self._channel_id:
                return
            if not self._is_allowed(message.author.id):
                return

            # 先處理指令
            await self._client.process_commands(message)

            # 偵測訊息中的 URL（指令訊息跳過）
            if message.content.startswith(self._prefix):
                return

            urls = _URL_PATTERN.findall(message.content)
            for url in urls:
                _logger.info(f"[DiscordBot] 收到網址：{url}")
                await message.reply(f"✅ 已接收網址，開始解析...\n`{url}`")
                if self._url_cb:
                    try:
                        self._url_cb(url)
                    except Exception as e:
                        _logger.error(f"[DiscordBot] 呼叫 URL callback 失敗：{e}")
                        await message.reply(f"❌ 解析失敗：{e}")

        @self._client.command(name="ping")
        async def cmd_ping(ctx):
            if not self._is_allowed(ctx.author.id):
                return
            latency = round(self._client.latency * 1000)
            await ctx.send(f"🏓 Pong！延遲 {latency} ms")

        @self._client.command(name="help")
        async def cmd_help(ctx):
            if not self._is_allowed(ctx.author.id):
                return
            lines = [
                "**漫畫下載機器人說明**",
                "直接貼上漫畫網址即可自動開始下載",
                "",
                "**支援站台**",
                "• NHentai / WNACG / EHentai",
                "• 18Comic / AHentai / ImHentai",
                "",
                "**指令**",
                f"`{self._prefix}ping`  確認機器人在線",
                f"`{self._prefix}help`  顯示此說明",
            ]
            await ctx.send("\n".join(lines))

    def start(self):
        """在背景執行緒啟動機器人（非阻塞）"""
        if self._thread and self._thread.is_alive():
            _logger.info("[DiscordBot] 機器人已在執行中")
            return

        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._client.start(self._token))
            except asyncio.CancelledError:
                pass
            finally:
                self._loop.close()

        self._thread = threading.Thread(target=_run, name="DiscordBotThread", daemon=True)
        self._thread.start()
        _logger.info("[DiscordBot] 背景執行緒已啟動")

    def stop(self):
        """關閉機器人"""
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._client.close(), self._loop)
        _logger.info("[DiscordBot] 機器人已關閉")

    def notify(self, message: str):
        """傳送通知訊息到指定頻道"""
        if not self._ready_event.is_set():
            _logger.warning(f"[DiscordBot] 機器人尚未就緒，訊息丟棄：{message}")
            return
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._send(message), self._loop)
        else:
            _logger.warning("[DiscordBot] Loop 未執行中")

    async def _send(self, message: str):
        try:
            channel = self._client.get_channel(self._channel_id)
            if channel is None:
                channel = await self._client.fetch_channel(self._channel_id)
            await channel.send(message)
        except Exception as e:
            _logger.error(f"[DiscordBot] 發送失敗 (channel_id={self._channel_id})：{e}")
