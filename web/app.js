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
let presets = {};
let currentState = {
  expression: "normal",
  pose: "basic",
  outfit: "usual",
  position: "center",
  blink: true
};

// プリセット読み込み
async function loadPresets() {
  try {
    const response = await fetch('/config/presets.json');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    presets = await response.json();
    console.log("✅ プリセット読み込み完了:", presets);
  } catch (error) {
    console.error("❌ プリセット読み込みエラー:", error);
    // デフォルトプリセット使用
    presets = {
      expressions: {
        normal: { name: "通常" },
        happy: { name: "喜び" },
        angry: { name: "怒り" },
        sad: { name: "悲しみ" }
      },
      poses: {
        basic: { name: "基本" },
        point: { name: "指差し" },
        raise_hand: { name: "手上げ" },
        think: { name: "考える" }
      },
      outfits: {
        usual: { name: "いつもの服" },
        uniform: { name: "制服" },
        casual: { name: "水着" }
      }
    };
  }
}

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
      startSpeechAnimation(data.text);
      break;
      
    case "volume_level":
      updateMouthByVolume(data.level);
      break;
      
    case "speech_end":
      console.log("音声終了");
      updateDebugStatus("speech-status", "待機中", false);
      resetMouth();
      break;
      
    case "speech_error":
      console.error("音声エラー:", data.error);
      updateDebugStatus("speech-status", "エラー", false);
      resetMouth();
      break;
      
    case "change_expression":
      console.log("表情変更:", data.preset);
      currentState.expression = data.preset;
      updateCharacter();
      break;
      
    case "change_pose":
      console.log("ポーズ変更:", data.preset);
      currentState.pose = data.preset;
      updateCharacter();
      break;
      
    case "change_outfit":
      console.log("衣装変更:", data.preset);
      currentState.outfit = data.preset;
      updateCharacter();
      break;
      
    case "update_character":
      updateCharacter();
      break;
      
    default:
      console.log("未知のメッセージ:", data);
  }
}

// キャラクター更新（完全再構築版）
function updateCharacter() {
  if (zundamonContainer && textures) {
    createCharacter();
    console.log("キャラクター更新:", currentState);
    updateDebugStatus("character-status", `${currentState.expression}/${currentState.pose}/${currentState.outfit}`, true);
  }
}

// プリセットベースのテクスチャ選択
function getCurrentEyeWhite() {
  return presets.expressions?.[currentState.expression]?.eyeWhite || "normal_white_eye";
}

function getCurrentEyeBlack() {
  return presets.expressions?.[currentState.expression]?.eyeBlack || "normal_eye";
}

function getCurrentEyebrow() {
  return presets.expressions?.[currentState.expression]?.eyebrow || "normal_eyebrow";
}

function getCurrentMouth() {
  return presets.expressions?.[currentState.expression]?.mouth || "muhu";
}

function getCurrentRightArm() {
  const armType = presets.poses?.[currentState.pose]?.rightArm || "basic";
  return armType + "_right";
}

function getCurrentLeftArm() {
  const armType = presets.poses?.[currentState.pose]?.leftArm || "basic";
  return armType + "_left";
}

function getCurrentClothes() {
  return presets.outfits?.[currentState.outfit]?.clothes || "usual_clothes";
}

// 音量による口パク
function updateMouthByVolume(volume) {
  if (!sprites.mouth) return;
  
  if (volume > 0.4 && textures["hoa"]) {
    sprites.mouth.texture = textures["hoa"].texture;
  } else if (volume > 0.1 && textures["muhu"]) {
    sprites.mouth.texture = textures["muhu"].texture;
  } else if (textures["muhu"]) {
    sprites.mouth.texture = textures["muhu"].texture;
  }
}

// まばたきアニメーション
function startBlinkAnimation() {
  if (!sprites.eyeWhite || !sprites.eyeBlack || !textures["sleepy_eye"]) return;
  
  // 目を閉じる
  const originalEyeWhite = sprites.eyeWhite.texture;
  const originalEyeBlack = sprites.eyeBlack.visible;
  
  sprites.eyeWhite.texture = textures["sleepy_eye"].texture;
  sprites.eyeBlack.visible = false;
  
  // 150ms後に目を開く
  setTimeout(() => {
    sprites.eyeWhite.texture = originalEyeWhite;
    sprites.eyeBlack.visible = originalEyeBlack;
  }, 150);
}

// アセット読み込み（admin.jsと同じ）
function loadAssets() {
  console.log("📦 アセット読み込み開始");
  
  app.loader
    .add("body", "/assets/zundamon_en/outfit2/body.png")
    .add("swimsuit", "/assets/zundamon_en/outfit2/swimsuit.png")
    .add("usual_clothes", "/assets/zundamon_en/outfit1/usual_clothes.png")
    .add("uniform", "/assets/zundamon_en/outfit1/uniform.png")
    .add("basic_right", "/assets/zundamon_en/outfit1/right_arm/basic.png")
    .add("basic_left", "/assets/zundamon_en/outfit1/left_arm/basic.png")
    .add("point_right", "/assets/zundamon_en/outfit1/right_arm/point.png")
    .add("waist_left", "/assets/zundamon_en/outfit1/left_arm/waist.png")
    .add("raise_hand_right", "/assets/zundamon_en/outfit1/right_arm/raise_hand.png")
    .add("think_left", "/assets/zundamon_en/outfit1/left_arm/think.png")
    .add("mic_right", "/assets/zundamon_en/outfit1/right_arm/mic.png")
    .add("edamame", "/assets/zundamon_en/edamame/edamame_normal.png")
    .add("normal_white_eye", "/assets/zundamon_en/eye/eye_set/normal_white_eye.png")
    .add("sharp_white_eye", "/assets/zundamon_en/eye/eye_set/sharp_white_eye.png")
    .add("normal_eye", "/assets/zundamon_en/eye/eye_set/pupil/normal_eye.png")
    .add("smile_eye", "/assets/zundamon_en/eye/smile_eye.png")
    .add("sharp_eye", "/assets/zundamon_en/eye/sharp_eye.png")
    .add("sleepy_eye", "/assets/zundamon_en/eye/sleepy_eye.png")
    .add("normal_eyebrow", "/assets/zundamon_en/eyebrow/normal_eyebrow.png")
    .add("angry_eyebrow", "/assets/zundamon_en/eyebrow/angry_eyebrow.png")
    .add("troubled_eyebrow1", "/assets/zundamon_en/eyebrow/troubled_eyebrow1.png")
    .add("troubled_eyebrow2", "/assets/zundamon_en/eyebrow/troubled_eyebrow2.png")
    .add("muhu", "/assets/zundamon_en/mouth/muhu.png")
    .add("hoa", "/assets/zundamon_en/mouth/hoa.png")
    .add("triangle", "/assets/zundamon_en/mouth/triangle.png")
    .add("nn", "/assets/zundamon_en/mouth/nn.png")
    .add("nnaa", "/assets/zundamon_en/mouth/nnaa.png")
    .load((loader, resources) => {
      console.log("✅ アセット読み込み完了");
      textures = resources;
      createCharacter();
      updateDebugStatus("character-status", "読み込み完了", true);
    });
}

// キャラクター作成（admin.jsと同じロジック）
function createCharacter() {
  console.log("👤 キャラクター作成開始");
  
  // ステージをクリア
  app.stage.removeChildren();
  
  // 新しいコンテナを作成
  zundamonContainer = new PIXI.Container();
  
  // 全体のスケールと位置を設定
  zundamonContainer.scale.set(0.6);
  zundamonContainer.x = 500;
  zundamonContainer.y = 50;
  
  app.stage.addChild(zundamonContainer);

  // スプライト作成
  sprites = {};
  addSprite("body", "body");
  addSprite("swimsuit", "swimsuit");
  addSprite("clothes", getCurrentClothes());
  addSprite("eyeWhite", getCurrentEyeWhite());
  addSprite("eyeBlack", getCurrentEyeBlack());
  addSprite("eyebrow", getCurrentEyebrow());
  addSprite("mouth", getCurrentMouth());
  addSprite("rightArm", getCurrentRightArm());
  addSprite("leftArm", getCurrentLeftArm());
  addSprite("edamame", "edamame");

  console.log("✅ キャラクター作成完了");
}

function addSprite(name, textureKey) {
  if (textureKey && textures[textureKey]) {
    sprites[name] = new PIXI.Sprite(textures[textureKey].texture);
    sprites[name].x = 0;
    sprites[name].y = 0;
    sprites[name].visible = true;
    zundamonContainer.addChild(sprites[name]);
  } else {
    sprites[name] = new PIXI.Sprite();
    sprites[name].visible = false;
    zundamonContainer.addChild(sprites[name]);
    console.warn(`テクスチャが見つかりません: ${textureKey}`);
  }
}

// デバッグ表示更新
function updateDebugStatus(elementId, text, isGood) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = text;
    element.className = isGood ? "status-item connected" : "status-item disconnected";
  }
}

// 初期化
async function init() {
  console.log("🚀 ずんだもんシステム初期化");
  
  // プリセット読み込み
  await loadPresets();
  
  // WebSocket接続
  connectWebSocket();
  
  // アセット読み込み
  loadAssets();
}

// 音声アニメーション
let speechAnimationInterval = null;

function startSpeechAnimation(text) {
  console.log("口パクアニメーション開始:", text);
  
  if (speechAnimationInterval) {
    clearInterval(speechAnimationInterval);
  }
  
  if (!sprites.mouth) return;
  
  const estimatedDuration = text.length * 150;
  let elapsed = 0;
  
  speechAnimationInterval = setInterval(() => {
    if (elapsed >= estimatedDuration) {
      resetMouth();
      clearInterval(speechAnimationInterval);
      speechAnimationInterval = null;
      return;
    }
    
    const shouldOpen = Math.random() > 0.5;
    if (shouldOpen && textures["hoa"]) {
      sprites.mouth.texture = textures["hoa"].texture;
    } else if (textures["muhu"]) {
      sprites.mouth.texture = textures["muhu"].texture;
    }
    
    elapsed += 200;
  }, 200);
}

function resetMouth() {
  if (speechAnimationInterval) {
    clearInterval(speechAnimationInterval);
    speechAnimationInterval = null;
  }
  if (sprites.mouth && textures["muhu"]) {
    sprites.mouth.texture = textures["muhu"].texture;
  }
}

// ページ読み込み完了後に初期化
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}