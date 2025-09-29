# ずんだもんタイムラインシステム - Claude開発者向けガイド

## プロジェクト概要

ずんだもんを使った配信システム。VOICEVOX音声合成・OBS連携・タイムライン自動実行・コメント処理を統合したシステム。

### 基本アーキテクチャ

```
┌─ GUI (tkinter管理画面)          ├─ Web (ブラウザUI)
│  └─ gui/main_window.py         │  ├─ index.html (ずんだもん表示)
│                                │  └─ admin.html (管理画面)
├─ Server (WebSocket/HTTP)       │
│  ├─ main.py (メインサーバー)    ├─ 統合システム
│  ├─ obs_controller.py          │  └─ run.py (フロー管理)
│  ├─ voicevox_client.py         │
│  ├─ timeline_generator.py      ├─ 設定・アセット
│  ├─ timeline_executor.py       │  ├─ config/settings.json
│  ├─ comment_handler.py         │  ├─ assets/zundamon_en/ (立ち絵データ)
│  └─ rag_responce.py            │  ├─ import/timeline_projects/
│                                │  └─ _deprecated/ (旧ファイル)
└─ プラグインシステム
   └─ plugins/
```

## 主要コンポーネント

### 1. サーバーサイド (`server/`)

- **main.py**: WebSocketサーバー（ブラウザ用:8767、OBS制御用:8768）、HTTP:5000
- **voicevox_client.py**: VOICEVOX API連携、音声合成
- **obs_controller.py**: OBS WebSocket制御、シーン切替
- **timeline_executor.py**: タイムライン自動実行
- **comment_handler.py**: コメント処理・割り込み
- **rag_responce.py**: RAGシステム（コメント検索・AI応答）★新規追加

### 2. フロントエンド (`web/`)

- **index.html**: ずんだもん表示画面（OBS Browser Source用）
- **admin.html**: 管理・制御画面
- **app.js**: ずんだもん描画ロジック
- **admin.js**: 管理画面制御

### 3. GUI管理画面 (`gui/`)

- **main_window.py**: tkinterメイン画面、サーバー制御・プロジェクト管理

### 4. 統合実行システム

- **run.py**: 起動制御（auto/broadcast/server/manualモード）

## 重要な設定ファイル

### config/settings.json
```json
{
  "servers": {
    "websocket_browser_port": 8767,
    "websocket_control_port": 8768,
    "voicevox_host": "localhost",
    "voicevox_port": 50021,
    "obs_websocket_port": 4455
  },
  "characters": {
    "zundamon": {
      "voice_id": 3,
      "default_expression": "normal"
    }
  },
  "automation": {
    "mode": "auto",
    "auto_start_components": ["server", "gui"]
  }
}
```

## データフロー

```
1. run.py → サーバー起動 → GUI起動
2. WebSocketクライアント接続（ブラウザ・OBS制御）
3. タイムライン実行 → ずんだもん制御 → VOICEVOX → 音声再生
4. コメント受信 → RAG検索 → AI応答 → ずんだもん発話
5. OBSシーン自動切替
```

## ずんだもん制御フロー

### 起動・表示フロー
```
run.py → obs_controller.py → OBS WebSocket → OBSシーン切替
                                              ↓
                         OBS Browser Source → http://localhost:5000/web/index.html
                                              ↓
                         web/app.js → WebSocket接続(8767) → server/main.py
```

### アクセスURL
- **キャラクター表示画面（OBS用）**: http://localhost:5000/web/index.html
- **管理画面**: http://localhost:5000/web/admin.html

### 制御・終了フロー
```
【制御】server/main.py → WebSocket(8767) → web/app.js → ずんだもん動作

【終了】web/app.js → WebSocket(8767) → server/main.py → WebSocket(8768) → run.py → obs_controller.py
```

### 役割分担と動作方式
- **run.py**: 配信フロー管理（スケジューラー・進行表）
  - 配信の時間管理とフェーズ制御のみ
  - 各フェーズのタイミングで指示を出すが、実作業はしない

- **server/main.py**: 常駐WebSocketサーバー（統合コントローラー）
  - 非同期でマルチタスク実行
  - WebSocket（8767/8768）+ HTTP（5000）サーバー
  - 実際のずんだもん制御・音声合成・OBS制御を統合実行
  - リアルタイムでコメント割り込み処理

- **obs_controller.py**: OBS操作リモコン
  - OBS WebSocket APIの薄いラッパー
  - server/main.pyの指示でOBS操作を実行

- **web/app.js**: ずんだもん表示・完了検知（演者）
  - OBS Browser Sourceで実行
  - server/main.pyからのWebSocket指示でずんだもん制御

### WebSocketポート使い分け
- **8767**: ブラウザ用（ずんだもん制御）
- **8768**: OBS制御用（統合システム通信）

## 開発時の注意点

### 起動順序
1. `python run.py auto` でフルシステム起動
2. または `python run.py server` でサーバーのみ

### 依存サービス
- **VOICEVOX**: localhost:50021 で起動必須
- **OBS Studio**: WebSocket Plugin有効化、4455ポート
- **ブラウザ**: index.html を OBS Browser Source で表示

### ポート使用状況
- 5000: HTTP (静的ファイル配信)
- 8767: WebSocket (ブラウザ用)
- 8768: WebSocket (OBS制御用)
- 50021: VOICEVOX API
- 4455: OBS WebSocket

### ログ・デバッグ
- `logs/system.log`: システムログ
- `config.logging.level` で DEBUG/INFO/WARNING切替
- `python run.py --debug` でデバッグモード

## プロジェクト構造

### タイムラインプロジェクト
```
import/timeline_projects/project_001/
├── timeline.json (ずんだもんタイムライン)
├── obs_timeline.json (OBSタイムライン)
├── audio/ (音声ファイル)
├── backgrounds/ (背景画像)
├── videos/ (動画ファイル)
└── texts/ (テキストファイル)
```

### アセットデータ
```
assets/zundamon_en/
├── eye/ (目の表情)
├── mouth/ (口の形)
├── eyebrow/ (眉毛)
├── face_color/ (頬の色)
├── outfit1/, outfit2/ (服装)
└── position_map.json (座標データ)
```

## RAGシステム (`server/rag_responce.py`)

新規追加されたコンポーネント。Aシステム（ncv_special_monitor）のデータを利用したニコ生コメント検索・AI応答生成機能。

### 主要機能
- SQLiteベクトル検索
- OpenAI/Google AI連携
- コメント類似度検索
- ずんだもん口調応答生成

### Aシステム連携設定
**絶対パス設定（デフォルト）:**
- 設定ファイル: `C:/project_root/app_workspaces/ncv_special_monitor/config/ncv_special_config.json`
- メインDB: `C:/project_root/app_workspaces/ncv_special_monitor/data/ncv_monitor.db`
- ベクトルDB: `C:/project_root/app_workspaces/ncv_special_monitor/data/vectors.db`

### データベース構造（重要）
**メインテーブル（放送情報統合済み）:**

#### 1. `comments`テーブル（生コメントデータ）
- 放送情報が直接含まれている
- JOINやビュー不要で全情報取得可能

#### 2. `ai_analyses`テーブル（AI分析・要約データ）
- 放送情報が直接含まれている
- JOINやビュー不要で全情報取得可能

**利用可能な情報:**
- **生コメント情報**: comment_id, comment_text, user_id, timestamp, elapsed_time
- **AI分析・要約情報**: analysis_result, summary_text, analysis_type
- **配信情報**: broadcast_lv_id, broadcast_title, broadcast_start_time（各テーブルに直接含有）
- **ユーザー情報**: user_name, is_special_user

**検索例:**
```python
# 特定ユーザーの生コメント取得（放送情報込み）
SELECT * FROM comments WHERE user_id = '21639740'

# 特定ユーザーのAI分析結果取得（放送情報込み）
SELECT * FROM ai_analyses WHERE user_id = '21639740'

# 特定配信の要約取得
SELECT * FROM ai_analyses WHERE broadcast_lv_id = 'lv348354633'

# 時間範囲でのコメント取得
SELECT * FROM comments WHERE timestamp BETWEEN start_time AND end_time
```

### 設定必要項目
- APIキー設定（OpenAI/Google）
- ずんだもん読み上げ範囲命令（user_id、時間範囲、配信ID等）

## 開発・デバッグ Tips

### よく使うコマンド
```bash
# フル起動
python run.py auto

# サーバーのみ
python run.py server

# 配信モード
python run.py broadcast --title "テスト配信"

# デバッグモード
python run.py auto --debug
```

### トラブルシューティング
1. **VOICEVOX接続失敗**: VOICEVOXアプリ起動確認
2. **OBS接続失敗**: WebSocketプラグイン・ポート確認
3. **ずんだもん表示されない**: index.html の WebSocket接続確認
4. **音声再生されない**: audio_temp/ ディレクトリ権限確認

### コード修正時の影響範囲
- **server/main.py**: WebSocket通信・全体に影響
- **server/voicevox_client.py**: 音声合成に影響
- **server/obs_controller.py**: OBS制御に影響
- **web/app.js**: ずんだもん表示に影響
- **config/settings.json**: 全体設定に影響

## システム内グローバル変数

### server/main.py（WebSocketサーバー）
```python
# グローバル変数
browser_clients = set()          # ブラウザ用WebSocket接続クライアント
obs_control_clients = set()      # OBS制御用WebSocket接続クライアント
voicevox = None                  # VoicevoxClientインスタンス
audio_analyzer = None            # AudioAnalyzerインスタンス
obs_controller = None            # OBSControllerインスタンス
plugin_manager = None            # PluginManagerインスタンス
volume_queue = queue.Queue()     # 音量データキュー
```

### run.py（統合システム）
```python
# IntegratedBroadcastSystemクラス内状態変数
self.config                      # システム設定
self.obs                         # OBSControllerインスタンス
self.zundamon_server_thread      # ずんだもんサーバースレッド
self.current_phase               # 現在フェーズ（idle/preparation/opening/zundamon_interactive/ending）
self.termination_event           # 終了イベント
```

### server/timeline_executor.py（タイムライン実行）
```python
# TimelineExecutorクラス内状態変数
self.config                      # システム設定
self.obs_controller              # OBSControllerインスタンス
self.zundamon_timeline           # ずんだもんタイムラインデータ
self.obs_timeline                # OBSタイムラインデータ
self.project_dir                 # プロジェクトディレクトリパス
self.is_running                  # 実行状態フラグ
self.is_paused                   # 一時停止状態フラグ
self.start_time                  # 開始時刻
self.current_action_index        # 現在実行中アクション番号
```

### server/rag_responce.py（RAGシステム）
```python
# RAGSearchSystemクラス内設定変数
self.a_system_base               # Aシステムベースパス
self.main_db_path                # メインDBパス
self.vector_db_path              # ベクトルDBパス
self.config_path                 # 設定ファイルパス
self.config                      # 設定データ
self.query_client                # 質問整形用AIクライアント
self.answer_client               # 回答生成用AIクライアント
self.embedding_client            # 埋め込み用クライアント
```

### 放送関連データ（データベース内）
```python
# commentsテーブル・ai_analysesテーブル共通
broadcast_lv_id                  # 放送ID（例: "lv348354633"）
broadcast_title                  # 放送タイトル（例: "始めてAI絵を覚えました"）
broadcast_start_time             # 放送開始時間（UNIX timestamp）
timestamp                        # コメント・分析の投稿時間
elapsed_time                     # 放送開始からの経過時間
user_id                          # ユーザーID（例: "21639740"）
user_name                        # ユーザー名
```

### タイムライン関連データ
```python
# timeline_executor.py内
self.zundamon_timeline["title"]          # タイムラインタイトル
self.zundamon_timeline["listener_name"]  # リスナー名
self.zundamon_timeline["nickname"]       # ニックネーム
self.zundamon_timeline["other_text"]     # その他テキスト

# 設定ファイル内時間管理
config["timeline"]["preparation_duration"]   # 準備時間（秒）
config["timeline"]["opening_duration"]       # オープニング時間（秒）
config["timeline"]["ending_duration"]        # エンディング時間（秒）
```

### 重要な状態管理
- **current_phase**: システム全体の現在状態
- **is_running/is_paused**: タイムライン実行状態
- **browser_clients**: WebSocket接続状態
- **zundamon_timeline**: 実行中タイムラインデータ
- **broadcast_lv_id**: 現在処理中の放送ID
- **broadcast_title**: 現在処理中の放送タイトル

## 音声合成・口パクシステム

### 音量ベース口パクアニメーション

**仕組み:**
1. VOICEVOX音声合成時、RMS音量分析を実行（`server/voicevox_client.py`）
2. 音量データをWebSocketでブラウザに送信（`volume_level`メッセージ）
3. ブラウザ側で音量閾値判定し、3段階の口テクスチャを切り替え

**キャラクター別設定（`config/settings.json`）:**
```json
"zundamon": {
  "mouth": {
    "closed": "muhu",
    "half_open": "hoa",
    "open": "hoaa",
    "threshold_open": 0.11,
    "threshold_half_open": 0.075
  }
},
"metan": {
  "mouth": {
    "closed": "smile",
    "half_open": "o",
    "open": "waaa",
    "threshold_open": 0.22,
    "threshold_half_open": 0.15
  }
}
```

**判定ロジック（`web/app.js`, `web/admin.js`）:**
```javascript
function updateMouthByVolume(volume, character = "zundamon") {
  if (!sprites.mouth || !config) return;

  const mouthConfig = config.characters?.[character]?.mouth || {
    closed: "muhu",
    half_open: "hoa",
    open: "hoaa",
    threshold_open: 0.11,
    threshold_half_open: 0.075
  };

  const thresholdOpen = mouthConfig.threshold_open || 0.11;
  const thresholdHalfOpen = mouthConfig.threshold_half_open || 0.075;

  if (volume >= thresholdOpen) {
    changeMouthTexture(mouthConfig.open);       // 大きく開く
  } else if (volume >= thresholdHalfOpen) {
    changeMouthTexture(mouthConfig.half_open);  // 半開き
  } else {
    changeMouthTexture(mouthConfig.closed);     // 閉じる
  }
}
```

**重要な実装ポイント:**
- `config`オブジェクトを**必ず初期化時に読み込む**（`await loadConfig()`）
- `config`が未定義だと`updateMouthByVolume`が早期リターンして動作しない
- キャラクター判定は`data.character`をWebSocketメッセージから受け取る
- 音量データは約0.05秒間隔で送信される（リアルタイム性確保）

### admin.html の config 読み込み必須設定

**admin.js での config 初期化（2025-09-30修正）:**

```javascript
// 1. グローバル変数宣言
let config = {};

// 2. loadConfig関数実装
async function loadConfig() {
  try {
    const response = await fetch('/config/settings.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    config = await response.json();
    console.log("✅ 設定読み込み完了:", config);
  } catch (error) {
    console.error("❌ 設定読み込みエラー:", error);
  }
}

// 3. 初期化時に必ず呼び出し
async function init() {
  await loadConfig();  // ← これがないと口パクが動かない
  connectWebSocket();
  loadPresets();
  // ...
}
```

**修正箇所:**
- `web/admin.js:48` - config変数宣言
- `web/admin.js:63-74` - loadConfig関数追加
- `web/admin.js:536` - 初期化時にawait loadConfig()呼び出し

**トラブルシューティング:**
- 口パクが2種類しか動かない → config未読み込み、ブラウザキャッシュ
- `config is not defined` エラー → loadConfig()の呼び出し忘れ
- キャラクター切り替えで閾値が変わらない → character引数の渡し忘れ

**デバッグ確認:**
```javascript
// ブラウザコンソールで確認
console.log("config:", config);
console.log("characters:", config.characters);
```

## デュアルキャラクターシステム（ずんだもん＆めたん）

### タイムラインJSONフォーマット
```json
{
  "title": "ずんだもん＆めたん掛け合いタイムライン",
  "timeline": [
    {
      "time": 0.0,
      "character": "zundamon",
      "position": "right",
      "expression": "normal",
      "text": "こんにちはなのだ！"
    },
    {
      "time": 3.0,
      "character": "metan",
      "position": "left",
      "expression": "happy",
      "text": "こんにちは、四国めたんです！"
    }
  ]
}
```

### キャラクター制御データフロー
```
timeline.json → timeline_executor.py → WebSocket(action: speak_text)
  → main.py → voicevox_client.py → 音声合成 + RMS分析
  → WebSocket(action: load_character, volume_level) → app.js
  → キャラクター表示 + 口パク制御
```

### 実装済み機能
- ✅ 2キャラクター交互会話
- ✅ キャラクター別音声ID（ずんだもん:3, めたん:2）
- ✅ キャラクター別音量閾値
- ✅ 位置制御（left/right）
- ✅ 表情・ポーズ・衣装切り替え
- ✅ リアルタイム口パクアニメーション

## 実装予定・TODO

- [ ] RAGシステムのDBパス設定
- [ ] ニコニコ生放送自動化
- [ ] リアルタイムコメント処理
- [ ] プラグインシステム拡張
- [ ] 音声ストリーミング
- [ ] 配信自動化フロー
- [x] デュアルキャラクターシステム（ずんだもん＆めたん）
- [x] 音量ベース口パクアニメーション（3段階）
- [x] admin.html の config 読み込み実装