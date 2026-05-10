import importlib
import os
import sys
import types
import unittest
from typing import Union, get_args, get_origin
from unittest.mock import patch


def _install_telegram_stubs():
    pydantic_settings = types.ModuleType("pydantic_settings")

    class SettingsConfigDict(dict):
        pass

    class BaseSettings:
        def __init__(self):
            annotations = getattr(self.__class__, "__annotations__", {})
            for name, annotation in annotations.items():
                env_value = os.environ.get(name)
                if env_value is None:
                    if hasattr(self.__class__, name):
                        setattr(self, name, getattr(self.__class__, name))
                        continue
                    raise ValueError(f"missing env {name}")

                target = annotation
                origin = get_origin(target)
                args = get_args(target)
                if origin is Union and type(None) in args:
                    non_none = [arg for arg in args if arg is not type(None)]
                    target = non_none[0] if non_none else str

                if target is int:
                    casted = int(env_value)
                elif target is bool:
                    casted = env_value.lower() in {"1", "true", "yes", "on"}
                else:
                    casted = env_value

                setattr(self, name, casted)

    pydantic_settings.SettingsConfigDict = SettingsConfigDict
    pydantic_settings.BaseSettings = BaseSettings

    telegramify = types.ModuleType("telegramify_markdown")
    telegramify.markdownify = lambda text, normalize_whitespace=False: text

    aiogram = types.ModuleType("aiogram")

    class Bot:
        def __init__(self, token, default):
            self.token = token
            self.default = default
            self.session = types.SimpleNamespace(close=lambda: None)

    aiogram.Bot = Bot

    aiogram_client_default = types.ModuleType("aiogram.client.default")

    class DefaultBotProperties:
        def __init__(self, parse_mode):
            self.parse_mode = parse_mode

    aiogram_client_default.DefaultBotProperties = DefaultBotProperties

    aiogram_enums = types.ModuleType("aiogram.enums")

    class ParseMode:
        MARKDOWN_V2 = "MarkdownV2"

    aiogram_enums.ParseMode = ParseMode

    return {
        "pydantic_settings": pydantic_settings,
        "telegramify_markdown": telegramify,
        "aiogram": aiogram,
        "aiogram.client.default": aiogram_client_default,
        "aiogram.enums": aiogram_enums,
    }


class NotificationManagerTest(unittest.TestCase):
    def _reload_notification_manager(self):
        for module_name in (
            "app.core.config",
            "app.services.notifications.providers.telegram",
            "app.services.notifications.manager",
        ):
            sys.modules.pop(module_name, None)

        manager_module = importlib.import_module("app.services.notifications.manager")
        return manager_module.NotificationManager

    def test_registers_multiple_telegram_channels(self):
        env = {
            "GITHUB_APP_ID": "1",
            "GITHUB_PRIVATE_KEY": "key",
            "GITHUB_WEBHOOK_SECRET": "secret",
            "GEMINI_API_KEY": "gemini",
            "TELEGRAM_BOT_TOKEN": "token",
            "TELEGRAM_CHANNELS": "-1001:12,-1002,invalid,-1003:",
        }
        with patch.dict(os.environ, env, clear=False), patch.dict(
            sys.modules, _install_telegram_stubs()
        ):
            NotificationManager = self._reload_notification_manager()
            with self.assertLogs(
                "app.services.notifications.manager", level="WARNING"
            ) as captured_logs:
                manager = NotificationManager()

        self.assertEqual(
            [(p.chat_id, p.thread_id) for p in manager.providers],
            [(-1001, 12), (-1002, None), (-1003, None)],
        )
        self.assertTrue(
            any(
                "Invalid TELEGRAM_CHANNELS entry 'invalid'" in message
                for message in captured_logs.output
            )
        )

    def test_uses_legacy_single_channel_when_multi_channel_not_set(self):
        env = {
            "GITHUB_APP_ID": "1",
            "GITHUB_PRIVATE_KEY": "key",
            "GITHUB_WEBHOOK_SECRET": "secret",
            "GEMINI_API_KEY": "gemini",
            "TELEGRAM_BOT_TOKEN": "token",
            "TELEGRAM_CHAT_ID": "-2001",
            "TELEGRAM_THREAD_ID": "22",
            "TELEGRAM_CHANNELS": "",
        }
        with patch.dict(os.environ, env, clear=False), patch.dict(
            sys.modules, _install_telegram_stubs()
        ):
            NotificationManager = self._reload_notification_manager()
            manager = NotificationManager()

        self.assertEqual(
            [(p.chat_id, p.thread_id) for p in manager.providers], [(-2001, 22)]
        )


if __name__ == "__main__":
    unittest.main()
