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
let metanContainer;
let zundamonSprites = {};
let metanSprites = {};
let zundamonTextures = {};
let metanTextures = {};
let presets = {};
let activeCharacter = "zundamon"; // 現在話しているキャラクター

let zundamonState = {
  expression: "normal",
  pose: "basic",
  outfit: "usual",
  blink: true
};

let metanState = {
  expression: "normal",
  pose: "basic",
  outfit: "usual",
  blink: true
};

// キャラクター設定
const characters = {
  zundamon: {
    name: "ずんだもん",
    assetPath: "/assets/zundamon_en",
    position: { x: 700, y: 50 } // 右側
  },
  metan: {
    name: "四国めたん",
    assetPath: "/assets/shikoku_metan_en",
    position: { x: 300, y: 50 } // 左側
  }
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
      // キャラクター別まばたき
      const blinkCharacter = data.character || activeCharacter;
      if (blinkCharacter === "zundamon" && zundamonState.blink) {
        startBlinkAnimation("zundamon");
      } else if (blinkCharacter === "metan" && metanState.blink) {
        startBlinkAnimation("metan");
      }
      break;

    case "speech_start":
      console.log("音声開始:", data.text, "キャラ:", data.character);
      const speakingCharacter = data.character || "zundamon";
      activeCharacter = speakingCharacter;
      highlightActiveCharacter(speakingCharacter);
      startSpeechAnimation(speakingCharacter, data.text);
      updateDebugStatus("speech-status", `${speakingCharacter}が話中`, true);
      break;

    case "volume_level":
      const volumeCharacter = data.character || activeCharacter;
      if (volumeCharacter === "zundamon") {
        updateZundamonMouth(data.level);
      } else if (volumeCharacter === "metan") {
        updateMetanMouth(data.level);
      }
      break;

    case "speech_end":
      console.log("音声終了");
      resetMouth(activeCharacter);
      resetCharacterHighlight();
      updateDebugStatus("speech-status", "待機中", false);
      break;

    case "speech_error":
      console.error("音声エラー:", data.error);
      resetMouth(activeCharacter);
      updateDebugStatus("speech-status", "エラー", false);
      break;

    case "change_expression":
      console.log("表情変更:", data.preset);
      const exprCharacter = data.character || activeCharacter;
      if (exprCharacter === "zundamon") {
        zundamonState.expression = data.preset;
      } else if (exprCharacter === "metan") {
        metanState.expression = data.preset;
      }
      updateCharacterState(exprCharacter);
      break;

    case "change_pose":
      console.log("ポーズ変更:", data.preset);
      const poseCharacter = data.character || activeCharacter;
      if (poseCharacter === "zundamon") {
        zundamonState.pose = data.preset;
      } else if (poseCharacter === "metan") {
        metanState.pose = data.preset;
      }
      updateCharacterState(poseCharacter);
      break;

    case "change_outfit":
      console.log("衣装変更:", data.preset);
      const outfitCharacter = data.character || activeCharacter;
      if (outfitCharacter === "zundamon") {
        zundamonState.outfit = data.preset;
      } else if (outfitCharacter === "metan") {
        metanState.outfit = data.preset;
      }
      updateCharacterState(outfitCharacter);
      break;

    case "update_character":
      const updateCharacter = data.character || activeCharacter;
      updateCharacterState(updateCharacter);
      break;

    default:
      console.log("未知のメッセージ:", data);
  }
}

// キャラクター状態更新（個別更新用）
function updateCharacterState(character) {
  console.log(`キャラクター状態更新[${character}]`);

  if (character === "zundamon") {
    createZundamon();
  } else if (character === "metan") {
    createMetan();
  }

  updateDebugStatus("character-status", `${character}更新完了`, true);
}

// キャラクター更新（完全再構築版）
function updateCharacter() {
  if (characterContainer && textures) {
    createCharacter();
    console.log("キャラクター更新:", currentState);
    updateDebugStatus("character-status", `${characters[currentCharacter].name}/${currentState.expression}/${currentState.pose}/${currentState.outfit}`, true);
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

// まばたきアニメーション（キャラクター別）
function startBlinkAnimation(character) {
  if (character === "zundamon") {
    if (!zundamonSprites.eyeWhite || !zundamonSprites.eyeBlack || !zundamonTextures["sleepy_eye"]) return;

    const originalEyeWhite = zundamonSprites.eyeWhite.texture;
    const originalEyeBlack = zundamonSprites.eyeBlack.visible;

    zundamonSprites.eyeWhite.texture = zundamonTextures["sleepy_eye"].texture;
    zundamonSprites.eyeBlack.visible = false;

    setTimeout(() => {
      zundamonSprites.eyeWhite.texture = originalEyeWhite;
      zundamonSprites.eyeBlack.visible = originalEyeBlack;
    }, 150);
  } else if (character === "metan") {
    if (!metanSprites.eyeWhite || !metanSprites.eyeBlack || !metanTextures["peaceful_eye"]) return;

    const originalEyeWhite = metanSprites.eyeWhite.texture;
    const originalEyeBlack = metanSprites.eyeBlack.visible;

    metanSprites.eyeWhite.texture = metanTextures["peaceful_eye"].texture;
    metanSprites.eyeBlack.visible = false;

    setTimeout(() => {
      metanSprites.eyeWhite.texture = originalEyeWhite;
      metanSprites.eyeBlack.visible = originalEyeBlack;
    }, 150);
  }
}

// キャラクター別アセット読み込み
async function loadCharacterAssets(character) {
  console.log(`📦 ${characters[character].name}のアセット読み込み開始`);

  const basePath = characters[character].assetPath;

  // 既存のアセットをクリア
  if (app.loader.resources) {
    for (const key in app.loader.resources) {
      delete app.loader.resources[key];
    }
  }

  // キャラクター別アセット設定
  const assetConfig = getAssetConfig(character, basePath);

  return new Promise((resolve) => {
    app.loader.reset();

    // アセットを動的に追加
    for (const [key, path] of Object.entries(assetConfig)) {
      app.loader.add(key, path);
    }

    app.loader.load((loader, resources) => {
      console.log(`✅ ${characters[character].name}のアセット読み込み完了`);
      textures = resources;
      resolve();
    });
  });
}

// キャラクター別アセット設定
function getAssetConfig(character, basePath) {
  if (character === "metan") {
    // 四国めたんのアセット設定
    return {
      "body": `${basePath}/outfit2/body.png`,
      "swimsuit": `${basePath}/outfit2/swimsuit.png`,
      "bunny_costume": `${basePath}/outfit2/bunny_costume.png`,
      "towel": `${basePath}/outfit2/towel.png`,
      "usual_clothes": `${basePath}/outfit1/uniform.png`,
      "basic_right": `${basePath}/outfit1/right_arm/normal.png`,
      "basic_left": `${basePath}/outfit1/left_arm/normal.png`,
      "point_right": `${basePath}/outfit1/right_arm/point.png`,
      "whisper_left": `${basePath}/outfit1/left_arm/whisper.png`,
      "hold_left": `${basePath}/outfit1/left_arm/hold.png`,
      "finger_to_mouth_left": `${basePath}/outfit1/left_arm/finger_to_mouth.png`,
      "mic_left": `${basePath}/outfit1/left_arm/mic.png`,
      "manju_right": `${basePath}/outfit1/right_arm/manju.png`,
      "hold_out_hand_right": `${basePath}/outfit1/right_arm/hold_out_hand.png`,
      "normal_white_eye": `${basePath}/eye/eye_set/normal_white_eye.png`,
      "wide_white_eye": `${basePath}/eye/eye_set/wide_white_eye.png`,
      "normal_eye": `${basePath}/eye/eye_set/pupil/normal_eye.png`,
      "normal_eye2": `${basePath}/eye/eye_set/pupil/normal_eye2.png`,
      "look_away": `${basePath}/eye/eye_set/pupil/look_away.png`,
      "look_away2": `${basePath}/eye/eye_set/pupil/look_away2.png`,
      "camera_gaze": `${basePath}/eye/eye_set/pupil/camera_gaze.png`,
      "camera_gaze2": `${basePath}/eye/eye_set/pupil/camera_gaze2.png`,
      "peaceful_eye": `${basePath}/eye/peaceful_eye.png`,
      "peaceful_eye2": `${basePath}/eye/peaceful_eye2.png`,
      "dizzy_eye": `${basePath}/eye/dizzy_eye.png`,
      "upward_eye": `${basePath}/eye/upward_eye.png`,
      "upward_eye2": `${basePath}/eye/upward_eye2.png`,
      "normal_eyebrow": `${basePath}/eyebrow/thick_happy_eyebrow.png`,
      "angry_eyebrow": `${basePath}/eyebrow/angry_eyebrow.png`,
      "happy_eyebrow": `${basePath}/eyebrow/happy_eyebrow.png`,
      "troubled_eyebrow": `${basePath}/eyebrow/troubled_eyebrow.png`,
      "slight_angry_eyebrow": `${basePath}/eyebrow/slight_angry_eyebrow.png`,
      "thick_angry_eyebrow": `${basePath}/eyebrow/thick_angry_eyebrow.png`,
      "thick_troubled_eyebrow": `${basePath}/eyebrow/thick_troubled_eyebrow.png`,
      "smile": `${basePath}/mouth/smile.png`,
      "mu": `${basePath}/mouth/mu.png`,
      "hoa": `${basePath}/mouth/hoa.png`,
      "o": `${basePath}/mouth/o.png`,
      "hee": `${basePath}/mouth/hee.png`,
      "yu": `${basePath}/mouth/yu.png`,
      "nn": `${basePath}/mouth/nn.png`,
      "grin": `${basePath}/mouth/grin.png`,
      "tongue_out": `${basePath}/mouth/tongue_out.png`,
      "momu": `${basePath}/mouth/momu.png`,
      "triangle_up": `${basePath}/mouth/triangle_up.png`,
      "triangle_down": `${basePath}/mouth/triangle_down.png`
    };
  } else {
    // ずんだもんのアセット設定（既存）
    return {
      "body": `${basePath}/outfit2/body.png`,
      "swimsuit": `${basePath}/outfit2/swimsuit.png`,
      "usual_clothes": `${basePath}/outfit1/usual_clothes.png`,
      "uniform": `${basePath}/outfit1/uniform.png`,
      "basic_right": `${basePath}/outfit1/right_arm/basic.png`,
      "basic_left": `${basePath}/outfit1/left_arm/basic.png`,
      "point_right": `${basePath}/outfit1/right_arm/point.png`,
      "waist_left": `${basePath}/outfit1/left_arm/waist.png`,
      "raise_hand_right": `${basePath}/outfit1/right_arm/raise_hand.png`,
      "think_left": `${basePath}/outfit1/left_arm/think.png`,
      "mic_right": `${basePath}/outfit1/right_arm/mic.png`,
      "edamame": `${basePath}/edamame/edamame_normal.png`,
      "normal_white_eye": `${basePath}/eye/eye_set/normal_white_eye.png`,
      "sharp_white_eye": `${basePath}/eye/eye_set/sharp_white_eye.png`,
      "normal_eye": `${basePath}/eye/eye_set/pupil/normal_eye.png`,
      "smile_eye": `${basePath}/eye/smile_eye.png`,
      "sharp_eye": `${basePath}/eye/sharp_eye.png`,
      "sleepy_eye": `${basePath}/eye/sleepy_eye.png`,
      "normal_eyebrow": `${basePath}/eyebrow/normal_eyebrow.png`,
      "angry_eyebrow": `${basePath}/eyebrow/angry_eyebrow.png`,
      "troubled_eyebrow1": `${basePath}/eyebrow/troubled_eyebrow1.png`,
      "troubled_eyebrow2": `${basePath}/eyebrow/troubled_eyebrow2.png`,
      "muhu": `${basePath}/mouth/muhu.png`,
      "hoa": `${basePath}/mouth/hoa.png`,
      "triangle": `${basePath}/mouth/triangle.png`,
      "nn": `${basePath}/mouth/nn.png`,
      "nnaa": `${basePath}/mouth/nnaa.png`
    };
  }
}

// 両キャラクター初期化
async function loadAssets() {
  console.log("📦 両キャラクターのアセット読み込み開始");

  // ずんだもんのアセット読み込み
  await loadCharacterAssets("zundamon");
  zundamonTextures = { ...textures };

  // 四国めたんのアセット読み込み
  await loadCharacterAssets("metan");
  metanTextures = { ...textures };

  // 両キャラクター作成
  createBothCharacters();

  console.log("✅ 両キャラクター読み込み完了");
  updateDebugStatus("character-status", "両キャラクター読み込み完了", true);
}

// キャラクター作成（admin.jsと同じロジック）
// 両キャラクター作成
function createBothCharacters() {
  console.log("👥 両キャラクター作成開始");

  // ステージをクリア
  app.stage.removeChildren();

  // ずんだもんコンテナ作成
  zundamonContainer = new PIXI.Container();
  zundamonContainer.scale.set(0.6);
  zundamonContainer.x = characters.zundamon.position.x;
  zundamonContainer.y = characters.zundamon.position.y;
  app.stage.addChild(zundamonContainer);

  // 四国めたんコンテナ作成
  metanContainer = new PIXI.Container();
  metanContainer.scale.set(0.6);
  metanContainer.x = characters.metan.position.x;
  metanContainer.y = characters.metan.position.y;
  app.stage.addChild(metanContainer);

  // 各キャラクター構築
  createZundamon();
  createMetan();

  console.log("✅ 両キャラクター作成完了");
}

// ずんだもん専用作成
function createZundamon() {
  console.log("🟢 ずんだもん専用描画開始");

  // コンテナクリア
  zundamonContainer.removeChildren();
  for (const key in zundamonSprites) {
    delete zundamonSprites[key];
  }

  // ずんだもん専用パーツ（edamame含む）
  addZundamonSprite("body", "body");
  addZundamonSprite("swimsuit", "swimsuit");
  addZundamonSprite("clothes", "usual_clothes");
  addZundamonSprite("right_arm", "basic_right");
  addZundamonSprite("left_arm", "basic_left");
  addZundamonSprite("edamame", "edamame"); // ずんだもん専用パーツ
  addZundamonSprite("eyeWhite", "normal_white_eye");
  addZundamonSprite("eyeBlack", "normal_eye");
  addZundamonSprite("eyebrow", "normal_eyebrow");
  addZundamonSprite("mouth", "muhu");

  console.log("✅ ずんだもん描画完了");
}

// 四国めたん専用作成
function createMetan() {
  console.log("🔵 四国めたん専用描画開始");

  // コンテナクリア
  metanContainer.removeChildren();
  for (const key in metanSprites) {
    delete metanSprites[key];
  }

  // 四国めたん専用パーツ
  addMetanSprite("body", "body");
  addMetanSprite("swimsuit", "swimsuit");
  addMetanSprite("clothes", "usual_clothes");
  addMetanSprite("right_arm", "basic_right");
  addMetanSprite("left_arm", "basic_left");
  addMetanSprite("eyeWhite", "normal_white_eye");
  addMetanSprite("eyeBlack", "normal_eye");
  addMetanSprite("eyebrow", "normal_eyebrow");
  addMetanSprite("mouth", "smile");

  console.log("✅ 四国めたん描画完了");
}

// ずんだもん専用スプライト追加
function addZundamonSprite(name, textureName) {
  if (zundamonTextures[textureName]) {
    zundamonSprites[name] = new PIXI.Sprite(zundamonTextures[textureName].texture);
    zundamonContainer.addChild(zundamonSprites[name]);
  } else {
    console.warn(`ずんだもんテクスチャなし: ${textureName}`);
  }
}

// 四国めたん専用スプライト追加
function addMetanSprite(name, textureName) {
  if (metanTextures[textureName]) {
    metanSprites[name] = new PIXI.Sprite(metanTextures[textureName].texture);
    metanContainer.addChild(metanSprites[name]);
  } else {
    console.warn(`四国めたんテクスチャなし: ${textureName}`);
  }
}

// 音量による口パク（キャラクター別）
function updateMouthByVolume(volume) {
  // アクティブキャラクターの口パクを更新
  if (activeCharacter === "zundamon" && zundamonSprites.mouth) {
    updateZundamonMouth(volume);
  } else if (activeCharacter === "metan" && metanSprites.mouth) {
    updateMetanMouth(volume);
  }
}

function updateZundamonMouth(volume) {
  if (volume > 0.4 && zundamonTextures["hoa"]) {
    zundamonSprites.mouth.texture = zundamonTextures["hoa"].texture;
  } else if (volume > 0.1 && zundamonTextures["muhu"]) {
    zundamonSprites.mouth.texture = zundamonTextures["muhu"].texture;
  } else if (zundamonTextures["muhu"]) {
    zundamonSprites.mouth.texture = zundamonTextures["muhu"].texture;
  }
}

function updateMetanMouth(volume) {
  if (volume > 0.4 && metanTextures["hoa"]) {
    metanSprites.mouth.texture = metanTextures["hoa"].texture;
  } else if (volume > 0.1 && metanTextures["muhu"]) {
    metanSprites.mouth.texture = metanTextures["muhu"].texture;
  } else if (metanTextures["muhu"]) {
    metanSprites.mouth.texture = metanTextures["muhu"].texture;
  }
}

// キャラクターハイライト機能
function highlightActiveCharacter(character) {
  // 全キャラクターを通常の明度に
  if (zundamonContainer) zundamonContainer.alpha = 0.6;
  if (metanContainer) metanContainer.alpha = 0.6;

  // アクティブキャラクターをハイライト
  if (character === "zundamon" && zundamonContainer) {
    zundamonContainer.alpha = 1.0;
  } else if (character === "metan" && metanContainer) {
    metanContainer.alpha = 1.0;
  }
}

function resetCharacterHighlight() {
  // 全キャラクターを通常の明度に戻す
  if (zundamonContainer) zundamonContainer.alpha = 1.0;
  if (metanContainer) metanContainer.alpha = 1.0;
}

// 旧関数（互換性のため残す）
function createCharacter() {
  createBothCharacters();

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
    characterContainer.addChild(sprites[name]);
  } else {
    sprites[name] = new PIXI.Sprite();
    sprites[name].visible = false;
    characterContainer.addChild(sprites[name]);
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

// 音声アニメーション（キャラクター別）
let zundamonSpeechInterval = null;
let metanSpeechInterval = null;

function startSpeechAnimation(character, text) {
  console.log(`口パクアニメーション開始[${character}]:`, text);

  if (character === "zundamon") {
    if (zundamonSpeechInterval) {
      clearInterval(zundamonSpeechInterval);
    }

    if (!zundamonSprites.mouth) return;

    const estimatedDuration = text.length * 150;
    let elapsed = 0;

    zundamonSpeechInterval = setInterval(() => {
      if (elapsed >= estimatedDuration) {
        resetMouth("zundamon");
        clearInterval(zundamonSpeechInterval);
        zundamonSpeechInterval = null;
        return;
      }

      const shouldOpen = Math.random() > 0.5;
      if (shouldOpen && zundamonTextures["hoa"]) {
        zundamonSprites.mouth.texture = zundamonTextures["hoa"].texture;
      } else if (zundamonTextures["muhu"]) {
        zundamonSprites.mouth.texture = zundamonTextures["muhu"].texture;
      }

      elapsed += 200;
    }, 200);
  } else if (character === "metan") {
    if (metanSpeechInterval) {
      clearInterval(metanSpeechInterval);
    }

    if (!metanSprites.mouth) return;

    const estimatedDuration = text.length * 150;
    let elapsed = 0;

    metanSpeechInterval = setInterval(() => {
      if (elapsed >= estimatedDuration) {
        resetMouth("metan");
        clearInterval(metanSpeechInterval);
        metanSpeechInterval = null;
        return;
      }

      const shouldOpen = Math.random() > 0.5;
      if (shouldOpen && metanTextures["hoa"]) {
        metanSprites.mouth.texture = metanTextures["hoa"].texture;
      } else if (metanTextures["mu"]) {
        metanSprites.mouth.texture = metanTextures["mu"].texture;
      }

      elapsed += 200;
    }, 200);
  }
}

function resetMouth(character) {
  if (character === "zundamon") {
    if (zundamonSpeechInterval) {
      clearInterval(zundamonSpeechInterval);
      zundamonSpeechInterval = null;
    }
    if (zundamonSprites.mouth && zundamonTextures["muhu"]) {
      zundamonSprites.mouth.texture = zundamonTextures["muhu"].texture;
    }
  } else if (character === "metan") {
    if (metanSpeechInterval) {
      clearInterval(metanSpeechInterval);
      metanSpeechInterval = null;
    }
    if (metanSprites.mouth && metanTextures["smile"]) {
      metanSprites.mouth.texture = metanTextures["smile"].texture;
    }
  }
}

// ページ読み込み完了後に初期化
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}