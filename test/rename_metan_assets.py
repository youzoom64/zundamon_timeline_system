#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rename shikoku_metan_en assets to English naming convention"""

import os
import shutil
from pathlib import Path

# Base directory
BASE_DIR = Path("assets/shikoku_metan_en")

# Rename mapping
RENAME_MAP = {
    # Eye files
    "eye/○○.png": "eye/circle_eye.png",
    "eye/eye閉じ.png": "eye/peaceful_eye.png",
    "eye/eye閉じ2.png": "eye/peaceful_eye2.png",
    "eye/ぐるぐる.png": "eye/dizzy_eye.png",
    "eye/見上げ.png": "eye/upward_eye.png",
    "eye/見上げ2.png": "eye/upward_eye2.png",
    "eye/unnamed.png": "eye/blank.png",
    "eye/eye_set/見開きwhiteeye.png": "eye/eye_set/wide_white_eye.png",
    "eye/eye_set/pupil/eyeそらし.png": "eye/eye_set/pupil/look_away.png",
    "eye/eye_set/pupil/eyeそらし2.png": "eye/eye_set/pupil/look_away2.png",
    "eye/eye_set/pupil/normaleye.png": "eye/eye_set/pupil/normal_eye.png",
    "eye/eye_set/pupil/normaleye2.png": "eye/eye_set/pupil/normal_eye2.png",
    "eye/eye_set/pupil/カメラeye線2.png": "eye/eye_set/pupil/camera_gaze2.png",

    # Eyebrow files
    "eyebrow/おこ.png": "eyebrow/angry_eyebrow.png",
    "eyebrow/ごきげん.png": "eyebrow/happy_eyebrow.png",
    "eyebrow/こまり.png": "eyebrow/troubled_eyebrow.png",
    "eyebrow/ややおこ.png": "eyebrow/slight_angry_eyebrow.png",
    "eyebrow/太eyebrowおこ.png": "eyebrow/thick_angry_eyebrow.png",
    "eyebrow/太eyebrowこまり.png": "eyebrow/thick_troubled_eyebrow.png",

    # Face color files
    "face_color/red面.png": "face_color/red_face.png",
    "face_color/かげり.png": "face_color/shadow.png",
    "face_color/青ざめ.png": "face_color/pale.png",

    # Mouth files
    "mouth/△.png": "mouth/triangle_up.png",
    "mouth/▽.png": "mouth/triangle_down.png",
    "mouth/いー.png": "mouth/hee.png",
    "mouth/うえー.png": "mouth/ueh.png",
    "mouth/お.png": "mouth/o.png",
    "mouth/にやり.png": "mouth/grin.png",
    "mouth/ぺろり.png": "mouth/tongue_out.png",
    "mouth/ほほえみ.png": "mouth/smile.png",
    "mouth/む.png": "mouth/mu.png",
    "mouth/もむー.png": "mouth/momu.png",
    "mouth/ゆ.png": "mouth/yu.png",
    "mouth/んー.png": "mouth/nn.png",

    # Outfit1 left arm
    "outfit1/left_arm/mouth元に指.png": "outfit1/left_arm/finger_to_mouth.png",
    "outfit1/left_arm/ひそひそ.png": "outfit1/left_arm/whisper.png",
    "outfit1/left_arm/まんじゅう袋.png": "outfit1/left_arm/manju_bag.png",
    "outfit1/left_arm/抱える.png": "outfit1/left_arm/hold.png",

    # Outfit1 right arm
    "outfit1/right_arm/まんじゅう.png": "outfit1/right_arm/manju.png",
    "outfit1/right_arm/手をかざす.png": "outfit1/right_arm/hold_out_hand.png",

    # Symbols
    "symbols/汗.png": "symbols/sweat.png",
    "symbols/涙.png": "symbols/tear.png",
}

def main():
    """Execute rename operations"""
    renamed_count = 0
    error_count = 0

    print("Starting rename operation for shikoku_metan_en assets...")
    print("Total files to rename: {}".format(len(RENAME_MAP)))
    print()

    for old_path, new_path in RENAME_MAP.items():
        old_full = BASE_DIR / old_path
        new_full = BASE_DIR / new_path

        if not old_full.exists():
            print("[WARN] Source not found: {}".format(old_path))
            error_count += 1
            continue

        if new_full.exists():
            print("[WARN] Destination already exists: {}".format(new_path))
            error_count += 1
            continue

        try:
            # Ensure parent directory exists
            new_full.parent.mkdir(parents=True, exist_ok=True)

            # Rename file
            shutil.move(str(old_full), str(new_full))
            print("[OK] {} -> {}".format(old_path, new_path))
            renamed_count += 1

        except Exception as e:
            print("[ERROR] Error renaming {}: {}".format(old_path, e))
            error_count += 1

    print()
    print("="*60)
    print("Rename operation completed!")
    print("Successfully renamed: {} files".format(renamed_count))
    if error_count > 0:
        print("Errors: {} files".format(error_count))
    print("="*60)

if __name__ == "__main__":
    main()
