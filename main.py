import os
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

# Maximum uploaded image size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


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

        html, body {
            margin: 0;
            padding: 0;
            min-height: 100%;
        }

        body {
            background: #020609;
            color: white;
            font-family: Arial, sans-serif;
            overflow-x: hidden;
        }

        #matrix {
            position: fixed;
            inset: 0;
            width: 100%;
            height: 100%;
            z-index: -3;
            background: #020609;
        }

        .matrix-overlay {
            position: fixed;
            inset: 0;
            z-index: -2;
            pointer-events: none;
            background:
                radial-gradient(
                    circle at center,
                    rgba(0, 100, 255, 0.10),
                    rgba(0, 0, 0, 0.88) 80%
                );
        }

        .scanlines {
            position: fixed;
            inset: 0;
            z-index: -1;
            pointer-events: none;
            background: repeating-linear-gradient(
                to bottom,
                rgba(255,255,255,0.015) 0px,
                rgba(255,255,255,0.015) 1px,
                transparent 1px,
                transparent 4px
            );
        }

        .container {
            width: min(900px, 92%);
            margin: auto;
            padding: 40px 0 70px;
        }

        h1 {
            text-align: center;
            font-size: 36px;
            margin: 0 0 10px;
            text-shadow:
                0 0 10px rgba(0,150,255,.8),
                0 0 25px rgba(0,100,255,.5);
        }

        .subtitle {
            text-align: center;
            color: #9aabba;
            margin-bottom: 30px;
        }

        .box {
            background: rgba(5,15,27,.90);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(0,140,255,.35);
            border-radius: 22px;
            padding: 24px;
            box-shadow:
                0 15px 60px rgba(0,0,0,.60),
                0 0 35px rgba(0,100,255,.10);
        }

        .upload {
            display: block;
            border: 2px dashed #176aa5;
            border-radius: 18px;
            padding: 35px 20px;
            text-align: center;
            cursor: pointer;
            background: rgba(0,30,55,.30);
            transition: .25s;
        }

        .upload:hover {
            border-color: #159cff;
            background: rgba(0,80,140,.18);
            box-shadow: 0 0 25px rgba(0,140,255,.15);
        }

        .upload input {
            display: none;
        }

        .upload-title {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 8px;
        }

        .upload-sub {
            color: #8999af;
        }

        #preview {
            display: none;
            max-width: 100%;
            max-height: 300px;
            margin: 20px auto 0;
            border-radius: 15px;
            border: 1px solid #1e5b8e;
        }

        .url-box {
            margin-top: 20px;
        }

        .url-box input {
            width: 100%;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #29415f;
            background: rgba(3,12,23,.95);
            color: white;
            outline: none;
        }

        .url-box input:focus {
            border-color: #168cff;
            box-shadow: 0 0 15px rgba(22,140,255,.20);
        }

        .search-btn {
            width: 100%;
            margin-top: 20px;
            padding: 15px;
            border: 0;
            border-radius: 12px;
            background: linear-gradient(
                90deg,
                #086fd1,
                #168cff,
                #086fd1
            );
            background-size: 200% 100%;
            color: white;
            font-size: 17px;
            font-weight: bold;
            cursor: pointer;
            transition: .25s;
        }

        .search-btn:hover {
            background-position: 100% 0;
            box-shadow: 0 0 25px rgba(22,140,255,.35);
        }

        .scanner {
            display: none;
            margin-top: 30px;
            text-align: center;
        }

        .scan-frame {
            position: relative;
            width: min(500px,100%);
            height: 330px;
            margin: auto;
            overflow: hidden;
            border: 2px solid #168cff;
            border-radius: 20px;
            background: #020713;
            box-shadow: 0 0 30px rgba(0,140,255,.18);
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
            color: #63bdff;
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
            margin-top: 30px;
        }

        .result {
            background: rgba(7,18,32,.92);
            border: 1px solid #1c3453;
            border-radius: 14px;
            padding: 17px;
            margin-bottom: 12px;
            transition: .2s;
        }

        .result:hover {
            border-color: #168cff;
            transform: translateY(-2px);
            box-shadow: 0 5px 25px rgba(0,100,255,.12);
        }

        .result-title {
            font-weight: bold;
            margin-bottom: 8px;
        }

        .result a {
            color: #55b4ff;
            text-decoration: none;
            word-break: break-word;
        }

        .result a:hover {
            text-decoration: underline;
        }

        .error {
            margin-top: 20px;
            padding: 15px;
            background: rgba(80,15,25,.92);
            border: 1px solid #7e2935;
            border-radius: 12px;
        }

        .empty {
            margin-top: 20px;
            padding: 15px;
            background: rgba(5,30,50,.90);
            border: 1px solid #245b91;
            border-radius: 12px;
            text-align: center;
            color: #9bb3c8;
        }

        .creator-credit {
            position: fixed;
            bottom: 10px;
            left: 0;
            width: 100%;
            text-align: center;
            font-size: 12px;
            color: rgba(120,190,230,.70);
            letter-spacing: 1px;
            z-index: 20;
            pointer-events: none;
            text-shadow: 0 0 8px rgba(0,140,255,.55);
        }

        @media (max-width: 600px) {
            .container {
                padding: 25px 0 65px;
            }

            h1 {
                font-size: 30px;
            }

            .box {
                padding: 18px;
            }
        }
    </style>
</head>

<body>

<canvas id="matrix"></canvas>
<div class="matrix-overlay"></div>
<div class="scanlines"></div>

<div class="container">

    <h1>🔎 Reverse Image Finder</h1>

    <div class="subtitle">
        Find pages and websites where an image appears
    </div>

    <div class="box">

        <form
            method="POST"
            action="/search"
            enctype="multipart/form-data"
            onsubmit="startScan()"
        >

            <label class="upload">

                <div class="upload-title">
                    📷 Upload an image
                </div>

                <div class="upload-sub">
                    Choose an image from your device
                </div>

                <input
                    type="file"
                    name="image"
                    accept="image/*"
                    onchange="previewImage(event)"
                >

            </label>

            <img id="preview" alt="Preview">

            <div class="url-box">

                <input
                    type="url"
                    name="image_url"
                    placeholder="Or paste an image URL here..."
                >

            </div>

            <button
                class="search-btn"
                type="submit"
            >
                🔍 Search Image
            </button>

        </form>

        <div
            class="scanner"
            id="scanner"
        >

            <div class="scan-frame">

                <img
                    id="scanImage"
                    alt="Scanning"
                >

                <div class="scan-line"></div>

            </div>

            <div class="scanning-text">
                Scanning image<span class="dots"></span>
            </div>

        </div>

    </div>

    {% if error %}

        <div class="error">
            ⚠️ {{ error }}
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

                    <a
                        href="{{ result.link }}"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        {{ result.link }}
                    </a>

                </div>

            {% endfor %}

        </div>

    {% elif searched %}

        <div class="empty">
            No visual matches were found for this image.
        </div>

    {% endif %}

</div>

<div class="creator-credit">
    Built by Tuhin
</div>


<script>

function previewImage(event) {

    const file = event.target.files[0];

    if (!file) {
        return;
    }

    const preview = document.getElementById("preview");

    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";

    document.querySelector(
        'input[name="image_url"]'
    ).value = "";
}


function startScan() {

    const fileInput = document.querySelector(
        'input[name="image"]'
    );

    const urlInput = document.querySelector(
        'input[name="image_url"]'
    );

    const scanner = document.getElementById(
        "scanner"
    );

    const scanImage = document.getElementById(
        "scanImage"
    );

    if (fileInput.files.length > 0) {

        scanImage.src = URL.createObjectURL(
            fileInput.files[0]
        );

    } else if (urlInput.value.trim()) {

        scanImage.src = urlInput.value.trim();

    } else {

        return;
    }

    scanner.style.display = "block";
}


const canvas = document.getElementById("matrix");
const ctx = canvas.getContext("2d");

let width;
let height;
let columns;
let drops;

const characters = "TUHIN";


function resizeMatrix() {

    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;

    const fontSize = 16;

    columns = Math.floor(width / fontSize);

    drops = Array(columns).fill(1);
}


function drawMatrix() {

    ctx.fillStyle = "rgba(2,6,9,0.075)";

    ctx.fillRect(
        0,
        0,
        width,
        height
    );

    const fontSize = 16;

    ctx.font = "bold " + fontSize + "px monospace";

    for (let i = 0; i < drops.length; i++) {

        const text = characters.charAt(
            Math.floor(
                Math.random() * characters.length
            )
        );

        ctx.fillStyle =
            Math.random() > 0.90
                ? "#63d4ff"
                : "#087ac1";

        ctx.shadowBlur = 8;
        ctx.shadowColor = "#008cff";

        ctx.fillText(
            text,
            i * fontSize,
            drops[i] * fontSize
        );

        ctx.shadowBlur = 0;

        if (
            drops[i] * fontSize > height &&
            Math.random() > 0.975
        ) {
            drops[i] = 0;
        }

        drops[i]++;
    }
}


resizeMatrix();

window.addEventListener(
    "resize",
    resizeMatrix
);

setInterval(
    drawMatrix,
    45
);

</script>

</body>
</html>
"""


@app.route("/", methods=["GET"])
def home():
    return render_template_string(
        HTML,
        error=None,
        results=None,
        searched=False
    )


@app.route("/search", methods=["POST"])
def search():

    serpapi_key = os.getenv("SERPAPI_KEY")
    imgbb_key = os.getenv("IMGBB_API_KEY")

    image_url = request.form.get(
        "image_url",
        ""
    ).strip()

    uploaded_file = request.files.get("image")


    # Check SerpApi API key
    if not serpapi_key:

        return render_template_string(
            HTML,
            error="SERPAPI_KEY is not configured.",
            results=None,
            searched=False
        )


    # If a file was uploaded
    if uploaded_file and uploaded_file.filename:

        if not imgbb_key:

            return render_template_string(
                HTML,
                error=(
                    "IMGBB_API_KEY is not configured. "
                    "Add it in Render Environment Variables."
                ),
                results=None,
                searched=False
            )

        try:

            file_data = uploaded_file.read()

            if not file_data:

                return render_template_string(
                    HTML,
                    error="The uploaded image is empty.",
                    results=None,
                    searched=False
                )


            upload_response = requests.post(
                "https://api.imgbb.com/1/upload",
                params={
                    "key": imgbb_key
                },
                files={
                    "image": (
                        uploaded_file.filename,
                        file_data,
                        uploaded_file.mimetype
                    )
                },
                timeout=60
            )

            upload_response.raise_for_status()

            upload_data = upload_response.json()


            if not upload_data.get("success"):

                return render_template_string(
                    HTML,
                    error="ImgBB image upload failed.",
                    results=None,
                    searched=False
                )


            image_url = (
                upload_data
                .get("data", {})
                .get("url", "")
            )


            if not image_url:

                return render_template_string(
                    HTML,
                    error=(
                        "ImgBB did not return a public "
                        "image URL."
                    ),
                    results=None,
                    searched=False
                )


        except requests.RequestException as e:

            return render_template_string(
                HTML,
                error=(
                    "Image upload request failed: "
                    + str(e)
                ),
                results=None,
                searched=False
            )


    # If neither upload nor URL was provided
    if not image_url:

        return render_template_string(
            HTML,
            error=(
                "Please upload an image or "
                "provide an image URL."
            ),
            results=None,
            searched=False
        )


    # Google Lens / SerpApi request
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": serpapi_key
    }


    try:

        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()


        if data.get("error"):

            return render_template_string(
                HTML,
                error=data.get(
                    "error",
                    "SerpApi search failed."
                ),
                results=None,
                searched=False
            )


        results = []


        for item in data.get(
            "visual_matches",
            []
        ):

            link = item.get(
                "link",
                ""
            )

            if not link:
                continue

            results.append({
                "title": item.get(
                    "title",
                    "Untitled"
                ),
                "link": link
            })


        return render_template_string(
            HTML,
            error=None,
            results=results,
            searched=True
        )


    except requests.RequestException as e:

        return render_template_string(
            HTML,
            error=(
                "Search request failed: "
                + str(e)
            ),
            results=None,
            searched=False
        )


@app.errorhandler(413)
def file_too_large(error):

    return render_template_string(
        HTML,
        error=(
            "Image is too large. "
            "Maximum allowed size is 10 MB."
        ),
        results=None,
        searched=False
    ), 413


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
