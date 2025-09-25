console.log("✅ ずんだもんシステム app.js 読み込み開始");

// PixiJSアプリケーション初期化
let app = new PIXI.Application({
  width: 1200,
  height: 800,
  transparent: true,
  forceCanvas: false,
  powerPreference: "high-performance"
});
document.body.appendChild(app.view);

// WebSocket接続
let ws = null;
let wsReconnectTimer = null;

function connectWebSocket() {
  ws = new WebSocket("ws://localhost:8767");
  
  ws.onopen = () => {
    console.log("✅ WebSocket接続完了");
    updateDebugStatus("ws-status", "接続済み", true);
    clearTimeout(wsReconnectTimer);
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleServerMessage(data);
    } catch (e) {
      console.error("WebSocketメッセージ解析エラー:", e);
    }
  };
  
  ws.onclose = () => {
    console.log("⚠️ WebSocket切断");
    updateDebugStatus("ws-status", "切断中", false);
    // 自動再接続
    wsReconnectTimer = setTimeout(connectWebSocket, 3000);
  };
  
  ws.onerror = (error) => {
    console.error("WebSocketエラー:", error);
    updateDebugStatus("ws-status", "エラー", false);
  };
}

// グローバル変数
let zundamonContainer;
let sprites = {};
let textures = {};
let eyeTextures = {};
let mouthTextures = {};
let currentState = {
  expression: "normal",
  pose: "basic",
  outfit: "usual",
  position: "center",
  blink: true
};

// サーバーメッセージ処理
function handleServerMessage(data) {
  console.log("[WebSocket受信]", data);
  
  switch(data.action) {
    case "blink":
      if (currentState.blink) {
        startBlinkAnimation();
      }
      break;
      
    case "speech_start":
      console.log("🎤 音声開始:", data.text);
      updateDebugStatus("speech-status", "発話中", true);
      startSpeechAnimation(data.text);
      break;
      
    case "volume_level":
      updateMouthByVolume(data.level);
      break;
      
    case "speech_end":
    console.log("🎤 音声終了");
    updateDebugStatus("speech-status", "待機中", false);
    if (sprites.mouth && mouthTextures.closed) {
        sprites.mouth.texture = mouthTextures.closed;
    }
    break;
      
    case "speech_error":
      console.error("🎤 音声エラー:", data.error);
      updateDebugStatus("speech-status", "エラー", false);
      break;
      
    case "update_character":
    case "change_expression":
    case "change_pose":
    case "change_outfit":
      updateCharacter(data);
      break;
      
    default:
      console.log("未知のメッセージ:", data);
  }
}

// 音量による口パク
function updateMouthByVolume(volume) {
  if (!sprites.mouth) return;
  
  if (volume > 0.4) {
    if (mouthTextures.open2) sprites.mouth.texture = mouthTextures.open2;
  } else if (volume > 0.1) {
    if (mouthTextures.open1) sprites.mouth.texture = mouthTextures.open1;
  } else {
    if (mouthTextures.closed) sprites.mouth.texture = mouthTextures.closed;
  }
}

// まばたきアニメーション
function startBlinkAnimation() {
  if (!sprites.eyeWhite || !sprites.eyeBlack || !eyeTextures.closed) return;
  
  // 目を閉じる
  sprites.eyeWhite.texture = eyeTextures.closed;
  sprites.eyeBlack.visible = false;
  
  // 150ms後に目を開く
  setTimeout(() => {
    if (sprites.eyeWhite && eyeTextures.whiteOpen) {
      sprites.eyeWhite.texture = eyeTextures.whiteOpen;
    }
    if (sprites.eyeBlack) {
      sprites.eyeBlack.visible = true;
    }
  }, 150);
}

// キャラクター状態更新
function updateCharacter(data) {
  if (data.expression) currentState.expression = data.expression;
  if (data.pose) currentState.pose = data.pose;
  if (data.outfit) currentState.outfit = data.outfit;
  if (data.position) currentState.position = data.position;
  if (data.blink !== undefined) currentState.blink = data.blink;
  
  // 実際の表示更新
  refreshCharacterDisplay();
  
  console.log("キャラクター更新:", currentState);
  updateDebugStatus("character-status", `${currentState.expression}/${currentState.pose}`, true);
}

// キャラクター表示更新
function refreshCharacterDisplay() {
  if (!zundamonContainer || !textures) return;
  
  // 表情更新
  updateFacialExpression();
  
  // ポーズ更新
  updatePose();
  
  // 衣装更新
  updateOutfit();
  
  // 位置更新
  updatePosition();
}

function updateFacialExpression() {
  // TODO: プリセットから表情情報取得して更新
  // 現在は簡易実装
}

function updatePose() {
  // TODO: プリセットからポーズ情報取得して更新
  // 現在は簡易実装
}

function updateOutfit() {
  // TODO: プリセットから衣装情報取得して更新
  // 現在は簡易実装
}

function updatePosition() {
  if (!zundamonContainer) return;
  
  switch (currentState.position) {
    case "left":
      zundamonContainer.x = 200;
      break;
    case "right":
      zundamonContainer.x = 800;
      break;
    case "center":
    default:
      zundamonContainer.x = 500;
      break;
  }
}

// アセット読み込み
function loadAssets() {
  console.log("📦 アセット読み込み開始");
  
  app.loader
    .add("body", "/assets/zundamon_en/outfit2/body.png")
    .add("swimsuit", "/assets/zundamon_en/outfit2/swimsuit.png")
    .add("clothes", "/assets/zundamon_en/outfit1/usual_clothes.png")
    .add("rightArm", "/assets/zundamon_en/outfit1/right_arm/basic.png")
    .add("leftArm", "/assets/zundamon_en/outfit1/left_arm/basic.png")
    .add("edamame", "/assets/zundamon_en/edamame/edamame_normal.png")
    
    // 口テクスチャ
    .add("mouthClosed", "/assets/zundamon_en/mouth/muhu.png")
    .add("mouthOpen1", "/assets/zundamon_en/mouth/hoa.png")
    .add("mouthOpen2", "/assets/zundamon_en/mouth/hoaa.png")
    
    // 目テクスチャ
    .add("eyeWhiteOpen", "/assets/zundamon_en/eye/eye_set/normal_white_eye.png")
    .add("eyeBlackOpen", "/assets/zundamon_en/eye/eye_set/pupil/normal_eye.png")
    .add("eyeClosed", "/assets/zundamon_en/eye/sleepy_eye.png")
    .add("eyebrow", "/assets/zundamon_en/eyebrow/normal_eyebrow.png")
    
    .load((loader, resources) => {
      console.log("✅ アセット読み込み完了");
      
      // テクスチャ保存
      textures = resources;
      
      eyeTextures.whiteOpen = resources.eyeWhiteOpen.texture;
      eyeTextures.blackOpen = resources.eyeBlackOpen.texture;
      eyeTextures.closed = resources.eyeClosed.texture;
      
      mouthTextures.closed = resources.mouthClosed.texture;
      mouthTextures.open1 = resources.mouthOpen1.texture;
      mouthTextures.open2 = resources.mouthOpen2.texture;

      // キャラクター作成
      createCharacter();
      updateDebugStatus("character-status", "読み込み完了", true);
    });
}

// キャラクター作成
function createCharacter() {
  console.log("👤 キャラクター作成開始");
  
  // コンテナ作成
  zundamonContainer = new PIXI.Container();
  
  // 全体のスケールと位置を設定
  zundamonContainer.scale.set(0.6);
  zundamonContainer.x = 500;  // 中央
  zundamonContainer.y = 50;   // 上部余白
  
  app.stage.addChild(zundamonContainer);

  // スプライト作成（レイヤー順序）
  sprites.body = createSprite("body");
  sprites.swimsuit = createSprite("swimsuit");
  sprites.clothes = createSprite("clothes");
  
  // 目
  sprites.eyeWhite = new PIXI.Sprite(eyeTextures.whiteOpen);
  sprites.eyeWhite.x = 0;
  sprites.eyeWhite.y = 0;
  zundamonContainer.addChild(sprites.eyeWhite);
  
  sprites.eyeBlack = new PIXI.Sprite(eyeTextures.blackOpen);
  sprites.eyeBlack.x = 0;
  sprites.eyeBlack.y = 0;
  zundamonContainer.addChild(sprites.eyeBlack);
  
  sprites.eyebrow = createSprite("eyebrow");
  
  // 口
  sprites.mouth = new PIXI.Sprite(mouthTextures.closed);
  sprites.mouth.x = 0;
  sprites.mouth.y = 0;
  zundamonContainer.addChild(sprites.mouth);
  
  sprites.rightArm = createSprite("rightArm");
  sprites.leftArm = createSprite("leftArm");
  sprites.edamame = createSprite("edamame");

  console.log("✅ キャラクター作成完了");
}

function createSprite(textureName) {
  if (textures[textureName] && textures[textureName].texture) {
    const sprite = new PIXI.Sprite(textures[textureName].texture);
    sprite.x = 0;
    sprite.y = 0;
    zundamonContainer.addChild(sprite);
    return sprite;
  }
  console.warn(`テクスチャが見つかりません: ${textureName}`);
  return null;
}

// デバッグ表示更新
function updateDebugStatus(elementId, text, isGood) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = text;
    element.className = isGood ? "status-item connected" : "status-item disconnected";
  }
}

// デバッグ表示切り替え
function toggleDebug() {
  const debug = document.getElementById("debug");
  if (debug) {
    debug.style.display = debug.style.display === "none" ? "block" : "none";
  }
}

// キーボードショートカット
document.addEventListener("keydown", (event) => {
  if (event.key === "F12") {
    event.preventDefault();
    toggleDebug();
  }
});

// 初期化
function init() {
  console.log("🚀 ずんだもんシステム初期化");
  
  // WebSocket接続
  connectWebSocket();
  
  // アセット読み込み
  loadAssets();
  
  // 定期まばたき（サーバー側で制御されるが、念のため）
  setInterval(() => {
    if (currentState.blink && Math.random() < 0.3) {
      startBlinkAnimation();
    }
  }, 8000);
}

// ページ読み込み完了後に初期化
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

// サーバーメッセージ処理
function handleServerMessage(data) {
  console.log("[WebSocket受信]", data);
  
  switch(data.action) {
    case "blink":
      if (currentState.blink) {
        startBlinkAnimation();
      }
      break;
      
    case "speech_start":
      console.log("音声開始:", data.text);
      updateDebugStatus("speech-status", "発話中", true);
      // 音声開始時に口パクアニメーション開始
      startSpeechAnimation(data.text);
      break;
      
    case "volume_level":
      updateMouthByVolume(data.level);
      break;
      
    case "speech_end":
      console.log("音声終了");
      updateDebugStatus("speech-status", "待機中", false);
      // 口を閉じる
      resetMouth();
      break;
      
    case "speech_error":
      console.error("音声エラー:", data.error);
      updateDebugStatus("speech-status", "エラー", false);
      resetMouth();
      break;
      
    case "update_character":
    case "change_expression":
    case "change_pose":
    case "change_outfit":
      updateCharacter(data);
      break;
      
    default:
      console.log("未知のメッセージ:", data);
  }
}


let speechAnimationInterval = null;

// 音声アニメーション開始
function startSpeechAnimation(text) {
  console.log("口パクアニメーション開始:", text);
  
  if (speechAnimationInterval) {
    clearInterval(speechAnimationInterval);
  }
  
  if (!sprites.mouth) {
    console.warn("sprites.mouth が見つかりません");
    return;
  }
  
  const estimatedDuration = text.length * 150;
  let elapsed = 0;
  
  speechAnimationInterval = setInterval(() => {
    if (elapsed >= estimatedDuration) {
      resetMouth();
      clearInterval(speechAnimationInterval);
      speechAnimationInterval = null;
      console.log("口パクアニメーション終了");
      return;
    }
    
    // ランダムに口の形を変える
    const shouldOpen = Math.random() > 0.5;
    if (shouldOpen && mouthTextures.open1) {
      sprites.mouth.texture = mouthTextures.open1;
    } else if (mouthTextures.closed) {
      sprites.mouth.texture = mouthTextures.closed;
    }
    
    elapsed += 200;
  }, 200);
}

// 口をリセット
function resetMouth() {
  if (speechAnimationInterval) {
    clearInterval(speechAnimationInterval);
    speechAnimationInterval = null;
  }
  if (sprites.mouth && mouthTextures.closed) {
    sprites.mouth.texture = mouthTextures.closed;
  }
}