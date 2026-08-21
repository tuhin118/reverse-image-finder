import os
import io
import requests
import imagehash

from PIL import Image
from flask import Flask, request, render_template

app = Flask(__name__)

# 30 MB maximum upload
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

# Minimum visual similarity
SIMILARITY_THRESHOLD = 70


def calculate_similarity(source_image, candidate_url):
    try:
        r = requests.get(
            candidate_url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()

        candidate = Image.open(
            io.BytesIO(r.content)
        ).convert("RGB")

        source_hash = imagehash.phash(source_image)
        candidate_hash = imagehash.phash(candidate)

        distance = source_hash - candidate_hash
        similarity = (1 - distance / 64) * 100

        return round(max(0, min(100, similarity)), 2)

    except Exception:
        return 0


@app.route("/", methods=["GET"])
def home():
    return render_template(
        "index.html",
        searched=False,
        results=[]
    )


@app.route("/search", methods=["POST"])
def search():

    serpapi_key = os.getenv("SERPAPI_KEY")
    imgbb_key = os.getenv("IMGBB_API_KEY")

    image_url = request.form.get(
        "image_url", ""
    ).strip()

    uploaded_file = request.files.get("image")


    # Check SerpApi key
    if not serpapi_key:
        return render_template(
            "index.html",
            error="SERPAPI_KEY is not configured.",
            searched=True,
            results=[]
        )


    # Upload local image to ImgBB
    if uploaded_file and uploaded_file.filename:

        if not imgbb_key:
            return render_template(
                "index.html",
                error="IMGBB_API_KEY is not configured.",
                searched=True,
                results=[]
            )

        try:
            file_data = uploaded_file.read()

            if not file_data:
                return render_template(
                    "index.html",
                    error="The selected image is empty.",
                    searched=True,
                    results=[]
                )

            response = requests.post(
                "https://api.imgbb.com/1/upload",
                params={"key": imgbb_key},
                files={
                    "image": (
                        uploaded_file.filename,
                        file_data
                    )
                },
                timeout=60
            )

            # Read JSON safely
            try:
                data = response.json()
            except ValueError:
                data = {}

            if response.status_code != 200 or not data.get("success"):
                message = data.get(
                    "error", {}
                ).get(
                    "message",
                    "ImgBB upload failed."
                )

                return render_template(
                    "index.html",
                    error=f"Image upload failed: {message}",
                    searched=True,
                    results=[]
                )

            image_url = (
                data.get("data", {})
                .get("url", "")
            )

            if not image_url:
                return render_template(
                    "index.html",
                    error="ImgBB did not return an image URL.",
                    searched=True,
                    results=[]
                )

        except requests.RequestException as e:
            return render_template(
                "index.html",
                error=f"ImgBB connection failed: {e}",
                searched=True,
                results=[]
            )


    # Need image URL
    if not image_url:
        return render_template(
            "index.html",
            error="Please upload an image or provide an image URL.",
            searched=True,
            results=[]
        )


    # Google Lens through SerpApi
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
            return render_template(
                "index.html",
                error=data.get(
                    "error",
                    "SerpApi search failed."
                ),
                searched=True,
                results=[]
            )

    except requests.RequestException as e:
        return render_template(
            "index.html",
            error=f"Search request failed: {e}",
            searched=True,
            results=[]
        )


    # Download source image
    try:
        source_response = requests.get(
            image_url,
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        source_response.raise_for_status()

        source_image = Image.open(
            io.BytesIO(source_response.content)
        ).convert("RGB")

    except Exception as e:
        return render_template(
            "index.html",
            error=f"Could not process image: {e}",
            searched=True,
            results=[]
        )


    # Process matches
    results = []

    for item in data.get("visual_matches", []):

        link = item.get("link", "")
        title = item.get("title", "Untitled")
        thumbnail = item.get("thumbnail", "")

        if not link:
            continue

        similarity = 0

        if thumbnail:
            similarity = calculate_similarity(
                source_image,
                thumbnail
            )

        if similarity >= SIMILARITY_THRESHOLD:
            results.append({
                "title": title,
                "link": link,
                "thumbnail": thumbnail,
                "similarity": similarity
            })


    # Highest similarity first
    results.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )


    return render_template(
        "index.html",
        results=results,
        searched=True
    )


# File too large
@app.errorhandler(413)
def request_entity_too_large(error):

    return render_template(
        "index.html",
        error="Image is too large. Maximum size is 30 MB.",
        searched=True,
        results=[]
    ), 413


# Local server
if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
