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
  createSimplePreview();
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

// プレビューキャラクター（複雑版）
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
      createCharacter();
    });
}

function createCharacter() {
  console.log("👤 キャラクター作成開始");
  
  // ステージを完全にクリア
  app.stage.removeChildren();
  
  // 新しいコンテナを作成
  zundamonContainer = new PIXI.Container();
  
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
  
  // コンテナをステージに追加
  app.stage.addChild(zundamonContainer);
  
  // コンテナのサイズと位置を調整
  zundamonContainer.scale.set(0.5);
  zundamonContainer.x = 70;
  zundamonContainer.y = -20;
  
  console.log("✅ キャラクター作成完了");
  updateCharacterStatus("キャラクター表示完了", true);
}

function addSprite(name, textureKey) {
  if (textureKey && app.loader.resources[textureKey]) {
    sprites[name] = new PIXI.Sprite(app.loader.resources[textureKey].texture);
    sprites[name].x = 0;
    sprites[name].y = 0;
    sprites[name].visible = true;
    zundamonContainer.addChild(sprites[name]);
    console.log(`${name} スプライト追加: ${textureKey}`);
  } else if (textureKey === null) {
    sprites[name] = new PIXI.Sprite();
    sprites[name].visible = false;
    zundamonContainer.addChild(sprites[name]);
    console.log(`${name} スプライト非表示`);
  } else {
    console.warn(`テクスチャが見つかりません: ${textureKey}`);
  }
}

function getCurrentEyeWhite() {
  return presets.expressions[currentState.expression]?.eyeWhite || "normal_white_eye";
}

function getCurrentEyeBlack() {
  return presets.expressions[currentState.expression]?.eyeBlack || "normal_eye";
}

function getCurrentEyebrow() {
  return presets.expressions[currentState.expression]?.eyebrow || "normal_eyebrow";
}

function getCurrentMouth() {
  return presets.expressions[currentState.expression]?.mouth || "muhu";
}

function getCurrentRightArm() {
  return presets.poses[currentState.pose]?.rightArm + "_right" || "basic_right";
}

function getCurrentLeftArm() {
  return presets.poses[currentState.pose]?.leftArm + "_left" || "basic_left";
}

function getCurrentClothes() {
  return presets.outfits[currentState.outfit]?.clothes || "usual_clothes";
}

function updatePreviewCharacter() {
  createCharacter();
}

function createSimplePreview() {
  // 既存のステージをクリア
  app.stage.removeChildren();
  
  // 背景
  const background = new PIXI.Graphics();
  background.beginFill(0x333333);
  background.drawRect(0, 0, 600, 800);
  background.endFill();
  app.stage.addChild(background);
  
  // キャラクター代替表示
  const characterBg = new PIXI.Graphics();
  characterBg.beginFill(0x4CAF50);
  characterBg.drawRoundedRect(150, 200, 300, 400, 20);
  characterBg.endFill();
  app.stage.addChild(characterBg);
  
  // メインテキスト
  const titleText = new PIXI.Text('ずんだもん', {
    fontFamily: 'Arial',
    fontSize: 32,
    fill: 0xFFFFFF,
    fontWeight: 'bold'
  });
  titleText.x = 300;
  titleText.y = 280;
  titleText.anchor.set(0.5);
  app.stage.addChild(titleText);
  
  // 状態表示テキスト
  const statusText = new PIXI.Text('プレビュー表示中\n\n操作は右側のパネルで行えます\n実際の表示は index.html で確認', {
    fontFamily: 'Arial',
    fontSize: 16,
    fill: 0xFFFFFF,
    align: 'center'
  });
  statusText.x = 300;
  statusText.y = 380;
  statusText.anchor.set(0.5);
  app.stage.addChild(statusText);
  
  console.log("✅ 簡易プレビュー作成完了");
  updateCharacterStatus("プレビュー表示完了", true);
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

function updateDebugStatus(elementId, text, isGood) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = text;
    element.className = isGood ? "status-item connected" : "status-item disconnected";
  } else {
    console.log(`[${elementId}] ${text} (${isGood ? 'OK' : 'ERROR'})`);
  }
}

function updateCharacterStatus(text, isGood) {
  const element = document.getElementById('character-status');
  if (element) {
    element.textContent = text;
    element.className = isGood ? "status-item connected" : "status-item disconnected";
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


// まばたきアニメーション実行
function performBlink() {
  if (sprites.eyeWhite && sprites.eyeBlack) {
    // 目を閉じる
    const originalEyeWhite = sprites.eyeWhite.texture;
    const originalEyeBlack = sprites.eyeBlack.visible;
    
    // 閉じた目のテクスチャがある場合
    if (app.loader.resources["sleepy_eye"]) {
      sprites.eyeWhite.texture = app.loader.resources["sleepy_eye"].texture;
      sprites.eyeBlack.visible = false;
    }
    
    // 150ms後に目を開く
    setTimeout(() => {
      sprites.eyeWhite.texture = originalEyeWhite;
      sprites.eyeBlack.visible = originalEyeBlack;
    }, 150);
  } else {
    console.log("👁️ まばたき（簡易プレビューモード）");
  }
}

// 音量による口パク（簡易版）
function updateMouthByVolume(volume) {
  if (sprites.mouth) {
    // 音量に応じて口の形を変える
    if (volume > 0.4 && app.loader.resources["hoa"]) {
      sprites.mouth.texture = app.loader.resources["hoa"].texture;
    } else if (volume > 0.1 && app.loader.resources["muhu"]) {
      sprites.mouth.texture = app.loader.resources["muhu"].texture;
    }
  }
}

function handleServerMessage(data) {
  console.log("← サーバー:", data);
  
  switch(data.action) {
    case "speech_start":
      console.log("音声開始:", data.text);
      document.getElementById('speech-text').value = '';
      // 音声開始時に口パクアニメーション開始
      startSpeechAnimation(data.text);
      break;
      
    case "volume_level":
      console.log("音量レベル:", data.level);
      updateMouthByVolume(data.level);
      break;
      
    case "speech_end":
      console.log("音声終了");
      // 口を閉じる
      resetMouth();
      break;
      
    case "blink":
      console.log("まばたき実行");
      performBlink();
      break;
      
    case "speech_error":
      console.error("音声エラー:", data.error);
      resetMouth();
      break;
      
    default:
      console.log("未知のメッセージ:", data);
  }
}

let speechAnimationInterval = null;

// 音声アニメーション開始
function startSpeechAnimation(text) {
  // 既存のアニメーション停止
  if (speechAnimationInterval) {
    clearInterval(speechAnimationInterval);
  }
  
  // テキストの長さから音声時間を推定（文字数 × 0.15秒）
  const estimatedDuration = text.length * 150;
  let elapsed = 0;
  
  // 0.2秒間隔で口の形を変える
  speechAnimationInterval = setInterval(() => {
    if (elapsed >= estimatedDuration) {
      resetMouth();
      clearInterval(speechAnimationInterval);
      speechAnimationInterval = null;
      return;
    }
    
    // ランダムに口の形を変える
    const mouthStates = ["muhu", "hoa"];
    const randomMouth = mouthStates[Math.floor(Math.random() * mouthStates.length)];
    changeMouthTexture(randomMouth);
    
    elapsed += 200;
  }, 200);
}

// 口のテクスチャを変更
function changeMouthTexture(textureKey) {
  if (sprites.mouth && app.loader.resources[textureKey]) {
    sprites.mouth.texture = app.loader.resources[textureKey].texture;
  }
}

// 口をリセット（閉じた状態）
function resetMouth() {
  if (speechAnimationInterval) {
    clearInterval(speechAnimationInterval);
    speechAnimationInterval = null;
  }
  changeMouthTexture("muhu"); // 閉じた口に戻す
}

// 音量による口パク（リアルタイム版）
function updateMouthByVolume(volume) {
  if (sprites.mouth) {
    if (volume > 0.4) {
      changeMouthTexture("hoa"); // 大きく開く
    } else if (volume > 0.1) {
      changeMouthTexture("muhu"); // 少し開く
    } else {
      changeMouthTexture("muhu"); // 閉じる
    }
  }
}