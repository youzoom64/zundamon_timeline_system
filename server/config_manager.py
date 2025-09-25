import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self):
        self.config_path = Path("config/settings.json")
        self.config = None
    
    def load_config(self):
        """設定ファイル読み込み"""
        if not self.config_path.exists():
            self.create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
                print(f"[設定] 設定ファイル読み込み完了: {self.config_path}")
                return self.config
        except Exception as e:
            print(f"[設定] 設定ファイル読み込みエラー: {e}")
            return self.get_default_config()
    
    def save_config(self, config=None):
        """設定ファイル保存"""
        if config:
            self.config = config
        
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"[設定] 設定ファイル保存完了: {self.config_path}")
        except Exception as e:
            print(f"[設定] 設定ファイル保存エラー: {e}")
    
    def create_default_config(self):
        """デフォルト設定ファイル作成"""
        default_config = self.get_default_config()
        self.config = default_config
        self.save_config()
    
    def get_default_config(self):
        """デフォルト設定取得"""
        return {
            "directories": {
                "import_dir": "./import",
                "timeline_dir": "./timeline", 
                "obs_timeline_dir": "./obs_timeline",
                "assets_dir": "./assets",
                "audio_temp_dir": "./audio_temp",
                "logs_dir": "./logs"
            },
            "servers": {
                "http_port": 5000,
                "websocket_browser_port": 8767,
                "websocket_control_port": 8768,
                "voicevox_host": "localhost",
                "voicevox_port": 50021,
                "obs_websocket_host": "localhost",
                "obs_websocket_port": 4455,
                "obs_password": ""
            },
            "characters": {
                "zundamon": {
                    "voice_id": 3,
                    "default_expression": "normal",
                    "default_outfit": "usual",
                    "default_pose": "basic",
                    "default_position": "center"
                }
            },
            "timeline": {
                "auto_blink_interval": 5.0,
                "speech_end_wait": 1.0,
                "comment_response_timeout": 30.0
            },
            "plugins": {
                "enabled": [],
                "plugin_dir": "./plugins"
            },
            "logging": {
                "level": "INFO",
                "file": "./logs/system.log"
            }
        }
    
    def get(self, key, default=None):
        """設定値取得"""
        if not self.config:
            self.load_config()
        
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key, value):
        """設定値設定"""
        if not self.config:
            self.load_config()
        
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save_config()