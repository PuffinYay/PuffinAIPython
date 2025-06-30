from flask import Flask, request, jsonify
import requests, os, json, time

app = Flask(__name__)

# Environment variables (set on Render)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY")
ROBLOX_USER_ID = os.getenv("ROBLOX_USER_ID")

# Roblox Open Cloud base URL
ROBLOX_BASE_URL = "https://apis.roblox.com/assets/v1/"
UPLOAD_PATH = "assets"  # for POST upload
LIST_PATH = "assets"    # for GET list

@app.route("/generate", methods=["POST"])
def generate_and_upload():
    try:
        prompt = request.json.get("prompt")
    except:
        return jsonify({"error": "Invalid JSON body"}), 400
    if not prompt:
        return jsonify({"error": "Missing 'prompt' field"}), 400
    if not (OPENAI_API_KEY and ROBLOX_API_KEY and ROBLOX_USER_ID):
        return jsonify({"error": "Missing environment variables"}), 500

    print("📌 Prompt:", prompt)

    # 1. Generate image from OpenAI (DALL·E 3)
    openai_resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024"
        }
    )

    if openai_resp.status_code != 200:
        return jsonify({
            "error": "OpenAI generation failed",
            "status": openai_resp.status_code,
            "detail": openai_resp.text
        }), 500

    try:
        image_url = openai_resp.json()["data"][0]["url"]
    except Exception as e:
        return jsonify({
            "error": "Failed to parse OpenAI image URL",
            "detail": str(e),
            "raw": openai_resp.text
        }), 500

    image_data = requests.get(image_url).content
    with open("image.png", "wb") as f:
        f.write(image_data)

    # 2. Upload to Roblox
    upload_url = ROBLOX_BASE_URL + UPLOAD_PATH
    with open("image.png", "rb") as f:
        files = {
            "fileContent": ("image.png", f, "image/png"),
            "request": (
                None,
                json.dumps({
                    "assetType": "Decal",
                    "displayName": "AI Decal",
                    "description": prompt,
                    "creationContext": {
                        "creator": {
                            "userId": int(ROBLOX_USER_ID)
                        }
                    }
                }),
                "application/json"
            )
        }

        roblox_resp = requests.post(
            upload_url,
            headers={"x-api-key": ROBLOX_API_KEY},
            files=files
        )

    try:
        upload_data = roblox_resp.json()
    except:
        return jsonify({
            "error": "Roblox upload failed",
            "raw": roblox_resp.text
        }), 500

    print("✅ Upload response:", upload_data)

    # 3. Delay to allow Roblox to register decal
    time.sleep(4)

    # 4. Get latest decal
    list_url = ROBLOX_BASE_URL + LIST_PATH
    assets_resp = requests.get(
        list_url,
        headers={"x-api-key": ROBLOX_API_KEY},
        params={
            "creatorType": "User",
            "creatorTargetId": ROBLOX_USER_ID,
            "assetTypes": "Decal",
            "limit": 1,
            "sortOrder": "Desc"
        }
    )

    try:
        assets_data = assets_resp.json()
        asset_entry = assets_data["data"][0]
        asset_id = asset_entry["id"]
    except Exception as e:
        return jsonify({
            "error": "Could not fetch latest decal",
            "detail": str(e),
            "raw": assets_resp.text
        }), 500

    return jsonify({
        "assetId": asset_id,
        "displayName": asset_entry.get("displayName"),
        "description": asset_entry.get("description")
    })

# For Render hosting
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
