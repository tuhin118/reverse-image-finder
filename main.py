
import os
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reverse Image Finder</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            background: #050b18;
            color: white;
            font-family: Arial, sans-serif;
        }

        .container {
            width: min(900px, 92%);
            margin: auto;
            padding: 45px 0;
        }

        h1 {
            text-align: center;
            font-size: 34px;
            margin-bottom: 10px;
        }

        .subtitle {
            text-align: center;
            color: #9aa8bd;
            margin-bottom: 35px;
        }

        .box {
            background: #0b1426;
            border: 1px solid #1b3152;
            border-radius: 22px;
            padding: 25px;
            box-shadow: 0 15px 50px rgba(0,0,0,.35);
        }

        .upload {
            border: 2px dashed #245b91;
            border-radius: 18px;
            padding: 35px 20px;
            text-align: center;
            cursor: pointer;
        }

        .upload:hover {
            border-color: #168cff;
        }

        .upload input {
            display: none;
        }

        .upload-title {
            font-size: 20px;
            margin-bottom: 8px;
        }

        .upload-sub {
            color: #8999af;
        }

        .url-box {
            margin-top: 20px;
        }

        .url-box input {
            width: 100%;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #29415f;
            background: #07101f;
            color: white;
            outline: none;
        }

        .search-btn {
            width: 100%;
            margin-top: 20px;
            padding: 15px;
            border: 0;
            border-radius: 12px;
            background: #168cff;
            color: white;
            font-size: 17px;
            font-weight: bold;
            cursor: pointer;
        }

        .search-btn:hover {
            background: #0877df;
        }

        #preview {
            display: none;
            max-width: 100%;
            max-height: 300px;
            margin: 20px auto 0;
            border-radius: 15px;
        }

        .scanner {
            display: none;
            margin-top: 30px;
            text-align: center;
        }

        .scan-frame {
            position: relative;
            width: min(500px, 100%);
            height: 330px;
            margin: auto;
            overflow: hidden;
            border: 2px solid #168cff;
            border-radius: 20px;
            background: #020713;
        }

        .scan-frame img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .scan-line {
            position: absolute;
            left: 0;
            width: 100%;
            height: 3px;
            background: #18a8ff;
            box-shadow: 0 0 18px #18a8ff;
            animation: scan 2s linear infinite;
        }

        @keyframes scan {
            0% { top: 0; }
            50% { top: calc(100% - 3px); }
            100% { top: 0; }
        }

        .scanning-text {
            margin-top: 18px;
            font-size: 20px;
        }

        .dots::after {
            content: "";
            animation: dots 1.5s infinite;
        }

        @keyframes dots {
            0% { content: ""; }
            33% { content: "."; }
            66% { content: ".."; }
            100% { content: "..."; }
        }

        .results {
            margin-top: 35px;
        }

        .result {
            background: #0b1426;
            border: 1px solid #1c3453;
            border-radius: 14px;
            padding: 17px;
            margin-bottom: 12px;
        }

        .result a {
            color: #55b4ff;
            text-decoration: none;
            word-break: break-word;
        }

        .result-title {
            font-weight: bold;
            margin-bottom: 8px;
        }

        .error {
            margin-top: 20px;
            padding: 15px;
            background: #39151b;
            border: 1px solid #7e2935;
            border-radius: 12px;
        }
    </style>
</head>

<body>

<div class="container">

    <h1>Reverse Image Finder</h1>
    <div class="subtitle">
        Find pages and websites where an image appears
    </div>

    <div class="box">

        <form method="POST" action="/search" onsubmit="startScan()">

            <label class="upload">
                <div class="upload-title">📷 Upload an image</div>
                <div class="upload-sub">Choose an image from your device</div>
                <input type="file" accept="image/*" onchange="previewImage(event)">
            </label>

            <img id="preview">

            <div class="url-box">
                <input
                    type="url"
                    name="image_url"
                    placeholder="Or paste an image URL here..."
                    required
                >
            </div>

            <button class="search-btn" type="submit">
                🔍 Search Image
            </button>

        </form>

        <div class="scanner" id="scanner">

            <div class="scan-frame">
                <img id="scanImage">
                <div class="scan-line"></div>
            </div>

            <div class="scanning-text">
                Scanning image<span class="dots"></span>
            </div>

        </div>

    </div>

    {% if error %}
        <div class="error">
            {{ error }}
        </div>
    {% endif %}

    {% if results %}
        <div class="results">

            <h2>🔎 Search Results</h2>

            {% for result in results %}
                <div class="result">

                    <div class="result-title">
                        {{ loop.index }}. {{ result.title }}
                    </div>

                    <a href="{{ result.link }}" target="_blank" rel="noopener">
                        {{ result.link }}
                    </a>

                </div>
            {% endfor %}

        </div>
    {% endif %}

</div>

<script>

function previewImage(event) {
    const file = event.target.files[0];

    if (!file) return;

    const preview = document.getElementById("preview");
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";

    document.querySelector('input[name="image_url"]').required = false;
}

function startScan() {

    const url = document.querySelector('input[name="image_url"]').value;
    const preview = document.getElementById("preview");

    const scanner = document.getElementById("scanner");
    const scanImage = document.getElementById("scanImage");

    if (preview.src) {
        scanImage.src = preview.src;
    } else if (url) {
        scanImage.src = url;
    }

    scanner.style.display = "block";
}

</script>

</body>
</html>
"""


@app.route("/", methods=["GET"])
def home():
    return render_template_string(HTML)


@app.route("/search", methods=["POST"])
def search():

    api_key = os.getenv("SERPAPI_KEY")
    image_url = request.form.get("image_url", "").strip()

    if not api_key:
        return render_template_string(
            HTML,
            error="SERPAPI_KEY is not configured."
        )

    if not image_url:
        return render_template_string(
            HTML,
            error="Please provide an image URL."
        )

    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": api_key
    }

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        results = []

        for item in data.get("visual_matches", []):
            results.append({
                "title": item.get("title", "Untitled"),
                "link": item.get("link", "")
            })

        return render_template_string(
            HTML,
            results=results
        )

    except requests.RequestException as e:
        return render_template_string(
            HTML,
            error=f"Search request failed: {e}"
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
