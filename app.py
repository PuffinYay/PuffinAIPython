from flask import Flask, request, jsonify
import requests, os, json, time

app = Flask(__name__)

# Environment variables (set these on Render.com)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY")
ROBLOX_USER_ID = os.getenv("ROBLOX_USER_ID")

@app.route("/generate", methods=["POST"])
def generate_and_upload():
    prompt = request.json.get("prompt", "An OpenAI-generated image")

    # 1. Generate image using OpenAI (DALL·E 3)
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

    try:
        image_url = openai_resp.json()["data"][0]["url"]
    except Exception as e:
        return jsonify({"error": "Failed to generate image", "detail": str(e), "raw": openai_resp.text}), 500

    image_data = requests.get(image_url).content

    # 2. Save image to disk
    with open("image.png", "wb") as f:
        f.write(image_data)

    # 3. Upload to Roblox
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
            "https://apis.roblox.com/assets/v1/assets",
            headers={"x-api-key": ROBLOX_API_KEY},
            files=files
        )

    try:
        upload_data = roblox_resp.json()
    except:
        return jsonify({"error": "Roblox upload failed", "raw": roblox_resp.text}), 500

    # Optional delay to allow Roblox to register the asset
    time.sleep(4)

    # 4. Look up the latest decal asset ID
    assets_resp = requests.get(
        "https://apis.roblox.com/assets/v1/assets",
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
        asset_id = assets_data["data"][0]["id"]
    except Exception as e:
        return jsonify({
            "error": "Could not find uploaded decal",
            "uploadResponse": upload_data,
            "lookupError": str(e),
            "lookupRaw": assets_resp.text
        }), 500

    return jsonify({
        "assetId": asset_id,
        "displayName": assets_data["data"][0].get("displayName"),
        "description": assets_data["data"][0].get("description")
    })

# Required for hosting on Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
