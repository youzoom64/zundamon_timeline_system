console.log("🔧 管理画面 admin.js 読み込み開始");

// PixiJSアプリケーション（プレビュー用）
let app = new PIXI.Application({
  width: 600,
  height: 800,
  backgroundColor: 0x333333
});
document.getElementById('preview-container').appendChild(app.view);

// WebSocket接続
let ws = null;

function connectWebSocket() {
  ws = new WebSocket("ws://localhost:8767");
  
  ws.onopen = () => {
    console.log("✅ WebSocket接続完了");
    updateConnectionStatus("connected");
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleServerMessage(data);
    } catch (e) {
      console.error("メッセージ解析エラー:", e);
    }
  };
  
  ws.onclose = () => {
    console.log("⚠️ WebSocket切断");
    updateConnectionStatus("disconnected");
    // 自動再接続
    setTimeout(connectWebSocket, 3000);
  };
  
  ws.onerror = (error) => {
    console.error("WebSocketエラー:", error);
    updateConnectionStatus("error");
  };
}

// プリセット設定
let presets = {};
let currentState = {
  expression: "normal",
  pose: "basic", 
  outfit: "usual"
};

// プレビュー用キャラクター
let zundamonContainer;
let sprites = {};

// プリセット読み込み
async function loadPresets() {
  try {
    const response = await fetch('/config/presets.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    presets = await response.json();
    console.log("✅ プリセット読み込み完了:", presets);
    setupUI();
    loadAssets();
  } catch (error) {
    console.error("❌ プリセット読み込みエラー:", error);
    // デフォルトプリセット使用
    useDefaultPresets();
  }
}

function useDefaultPresets() {
  presets = {
    expressions: {
      normal: { name: "通常" },
      happy: { name: "喜び" },
      angry: { name: "怒り" },
      sad: { name: "悲しみ" },
      tired: { name: "疲れ" }
    },
    poses: {
      basic: { name: "基本" },
      point: { name: "指差し" },
      raise_hand: { name: "手上げ" },
      think: { name: "考える" },
      mic: { name: "マイク" }
    },
    outfits: {
      usual: { name: "いつもの服" },
      uniform: { name: "制服" },
      casual: { name: "水着" }
    }
  };
  setupUI();
}

// UI設定
function setupUI() {
  console.log("🎨 UI設定開始");
  
  // 表情ボタン
  const expressionContainer = document.getElementById('expression-buttons');
  expressionContainer.innerHTML = '';
  Object.entries(presets.expressions).forEach(([key, preset]) => {
    const btn = document.createElement('button');
    btn.className = 'preset-btn';
    btn.textContent = preset.name;
    btn.onclick = () => changeExpression(key);
    if (key === currentState.expression) btn.classList.add('active');
    expressionContainer.appendChild(btn);
  });

  // ポーズボタン
  const poseContainer = document.getElementById('pose-buttons');
  poseContainer.innerHTML = '';
  Object.entries(presets.poses).forEach(([key, preset]) => {
    const btn = document.createElement('button');
    btn.className = 'preset-btn';
    btn.textContent = preset.name;
    btn.onclick = () => changePose(key);
    if (key === currentState.pose) btn.classList.add('active');
    poseContainer.appendChild(btn);
  });

  // 衣装ボタン
  const outfitContainer = document.getElementById('outfit-buttons');
  outfitContainer.innerHTML = '';
  Object.entries(presets.outfits).forEach(([key, preset]) => {
    const btn = document.createElement('button');
    btn.className = 'preset-btn';
    btn.textContent = preset.name;
    btn.onclick = () => changeOutfit(key);
    if (key === currentState.outfit) btn.classList.add('active');
    outfitContainer.appendChild(btn);
  });

  // 音声ボタン
  const speakBtn = document.getElementById('speak-btn');
  speakBtn.onclick = () => {
    const text = document.getElementById('speech-text').value.trim();
    if (text) {
      sendSpeechRequest(text);
    }
  };

  console.log("✅ UI設定完了");
}

// 制御関数
function changeExpression(key) {
  currentState.expression = key;
  updateActiveButtons();
  updatePreviewCharacter();
  sendToServer({action: "change_expression", preset: key});
}

function changePose(key) {
  currentState.pose = key;
  updateActiveButtons();
  updatePreviewCharacter();
  sendToServer({action: "change_pose", preset: key});
}

function changeOutfit(key) {
  currentState.outfit = key;
  updateActiveButtons();
  updatePreviewCharacter();
  sendToServer({action: "change_outfit", preset: key});
}

function sendSpeechRequest(text) {
  const speakBtn = document.getElementById('speak-btn');
  speakBtn.disabled = true;
  speakBtn.textContent = '発話中...';
  
  sendToServer({action: "speak_text", text: text});
  
  // 5秒後にボタンを有効化（音声終了を待たない）
  setTimeout(() => {
    speakBtn.disabled = false;
    speakBtn.textContent = '喋る';
  }, 5000);
}

function testBlink() {
  sendToServer({action: "blink"});
}

function resetCharacter() {
  currentState = {
    expression: "normal",
    pose: "basic",
    outfit: "usual"
  };
  updateActiveButtons();
  updatePreviewCharacter();
  sendToServer({action: "change_expression", preset: "normal"});
  sendToServer({action: "change_pose", preset: "basic"});
  sendToServer({action: "change_outfit", preset: "usual"});
}

// サーバー通信
function sendToServer(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
    console.log("→ サーバー:", data);
  } else {
    console.error("WebSocket未接続");
  }
}

function handleServerMessage(data) {
  console.log("← サーバー:", data);
  
  switch(data.action) {
    case "speech_start":
      document.getElementById('speech-text').value = '';
      break;
    case "speech_end":
      // 特に処理なし
      break;
  }
}

// アクティブボタン更新
function updateActiveButtons() {
  document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
  
  // 表情ボタン
  const expressionBtns = document.querySelectorAll('#expression-buttons .preset-btn');
  const expressionKeys = Object.keys(presets.expressions || {});
  const expressionIndex = expressionKeys.indexOf(currentState.expression);
  if (expressionIndex >= 0 && expressionBtns[expressionIndex]) {
    expressionBtns[expressionIndex].classList.add('active');
  }

  // ポーズボタン
  const poseBtns = document.querySelectorAll('#pose-buttons .preset-btn');
  const poseKeys = Object.keys(presets.poses || {});
  const poseIndex = poseKeys.indexOf(currentState.pose);
  if (poseIndex >= 0 && poseBtns[poseIndex]) {
    poseBtns[poseIndex].classList.add('active');
  }

  // 衣装ボタン
  const outfitBtns = document.querySelectorAll('#outfit-buttons .preset-btn');
  const outfitKeys = Object.keys(presets.outfits || {});
  const outfitIndex = outfitKeys.indexOf(currentState.outfit);
  if (outfitIndex >= 0 && outfitBtns[outfitIndex]) {
    outfitBtns[outfitIndex].classList.add('active');
  }
}

// プレビューキャラクター（簡易実装）
function loadAssets() {
  // 簡易版のアセット読み込み
  console.log("📦 プレビュー用アセット読み込み");
  
  // TODO: 実際のプレビューキャラクター実装
  createSimplePreview();
}

function createSimplePreview() {
  // 簡易プレビュー表示
  const text = new PIXI.Text('ずんだもん\nプレビュー', {
    fontFamily: 'Arial',
    fontSize: 24,
    fill: 0xFFFFFF,
    align: 'center'
  });
  
  text.x = app.view.width / 2;
  text.y = app.view.height / 2;
  text.anchor.set(0.5);
  
  app.stage.addChild(text);
}

function updatePreviewCharacter() {
  // プレビュー更新
  console.log("プレビュー更新:", currentState);
}

// ステータス表示更新
function updateConnectionStatus(status) {
  const element = document.getElementById('connection-status');
  if (element) {
    switch (status) {
      case "connected":
        element.textContent = "WebSocket: 接続済み";
        element.className = "status-item connected";
        break;
      case "disconnected":
        element.textContent = "WebSocket: 切断中";
        element.className = "status-item disconnected";
        break;
      case "error":
        element.textContent = "WebSocket: エラー";
        element.className = "status-item disconnected";
        break;
    }
  }
}

// 初期化
function init() {
  console.log("🚀 管理画面初期化");
  
  // WebSocket接続
  connectWebSocket();
  
  // プリセット読み込み
  loadPresets();
  
  // ステータス初期化
  updateConnectionStatus("disconnected");
}

// ページ読み込み完了後に初期化
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

// Enter キーで音声送信
document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && event.target.id === "speech-text") {
    if (!event.shiftKey) {
      event.preventDefault();
      document.getElementById('speak-btn').click();
    }
  }
});