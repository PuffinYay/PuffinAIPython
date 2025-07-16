from flask import Flask, request, jsonify
import requests, os, json, time

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY")
ROBLOX_USER_ID = os.getenv("ROBLOX_USER_ID")  # Make sure this is your numeric user ID

@app.route("/generate", methods=["POST"])
def generate_and_upload():
    prompt = request.json.get("prompt", "An OpenAI-generated image")

    # 1️⃣ Generate image from OpenAI
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

    # 2️⃣ Upload image to Roblox
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
                        "creator": { "userId": int(ROBLOX_USER_ID) }
                    }
                }),
                "application/json"
            )
        }
        roblox_resp = requests.post(
            "https://apis.roblox.com/assets/v1/assets",
            headers={ "x-api-key": ROBLOX_API_KEY },
            files=files
        )

    if roblox_resp.status_code != 200:
        return jsonify({ "error": "upload_failed", "details": roblox_resp.text }), 500

    # 3️⃣ Poll operation path for result
    data = roblox_resp.json()
    operation_path = data.get("path")
    if not operation_path:
        return jsonify({ "error": "no_operation_path", "details": data }), 500

    operation_url = "https://apis.roblox.com" + operation_path

    for attempt in range(10):  # Try for up to 10 seconds
        op_check = requests.get(operation_url, headers={"x-api-key": ROBLOX_API_KEY})
        op_data = op_check.json()

        if op_check.status_code == 200 and "assetId" in op_data:
            asset_id = op_data["assetId"]
            return jsonify({
                "success": True,
                "prompt": prompt,
                "imageUrl": image_url,
                "assetId": asset_id,
                "rbxAssetId": f"rbxassetid://{asset_id}"
            })

        time.sleep(1)  # wait 1 second before retry

    return jsonify({ "error": "asset_timeout", "details": op_data }), 500

# ✅ Render fix
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
