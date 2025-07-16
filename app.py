from flask import Flask, request, jsonify
import requests, os, json

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY")
ROBLOX_USER_ID = os.getenv("ROBLOX_USER_ID")

@app.route("/generate", methods=["POST","GET"])
def generate_and_upload():
    prompt = request.json.get("prompt", "An OpenAI-generated image")
    # Generate image from OpenAI
    response = requests.post(
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
    image_url = response.json()["data"][0]["url"]
    image_data = requests.get(image_url).content

    with open("image.png", "wb") as f:
        f.write(image_data)

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
                        "creator": {"userId": int(ROBLOX_USER_ID)}
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
    if roblox_resp.status_code != 200:
        return jsonify({"error": "upload_failed", "detail": data}), 500
    data = roblox_resp.json()
    
    asset_path = data['path']
    roblox_resp2 = requests.get(
            "https://apis.roblox.com/assets/v1/"+asset_path,
            headers={"x-api-key": ROBLOX_API_KEY}
    )
    if roblox_resp2.status_code != 200:
        return jsonify({"error": "upload_failed", "detail": data}), 500
    return roblox_resp2

# ✅ This fixes the Render port issue:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
