import io
import requests
import imagehash

from PIL import Image
from flask import Flask, request, render_template

app = Flask(__name__)

# Maximum upload size: 30 MB
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

# Minimum visual similarity
SIMILARITY_THRESHOLD = 70


# =========================================================
# IMAGE SIMILARITY
# =========================================================

def calculate_similarity(source_image, candidate_url):
    try:
        response = requests.get(
            candidate_url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        response.raise_for_status()

        candidate_image = Image.open(
            io.BytesIO(response.content)
        ).convert("RGB")

        source_hash = imagehash.phash(source_image)
        candidate_hash = imagehash.phash(candidate_image)

        distance = source_hash - candidate_hash

        similarity = (1 - distance / 64) * 100

        return round(
            max(0, min(100, similarity)),
            2
        )

    except Exception:
        return 0


# =========================================================
# HOME
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return render_template(
        "index.html",
        searched=False,
        results=[]
    )


# =========================================================
# SEARCH
# =========================================================

@app.route("/search", methods=["POST"])
def search():

    serpapi_key = request.form.get(
        "serpapi_key"
    ) or __import__("os").environ.get(
        "SERPAPI_KEY"
    )

    image_url = request.form.get(
        "image_url",
        ""
    ).strip()

    uploaded_file = request.files.get(
        "image"
    )


    # =====================================================
    # SERPAPI KEY
    # =====================================================

    if not serpapi_key:

        return render_template(
            "index.html",
            error="SERPAPI_KEY is not configured.",
            searched=True,
            results=[]
        )


    # =====================================================
    # UPLOAD IMAGE TO PICRD
    # =====================================================

    if (
        uploaded_file
        and uploaded_file.filename
    ):

        try:

            file_data = uploaded_file.read()

            if not file_data:

                return render_template(
                    "index.html",
                    error="The selected image is empty.",
                    searched=True,
                    results=[]
                )


            # Picrd maximum upload size = 10 MB
            if len(file_data) > 10 * 1024 * 1024:

                return render_template(
                    "index.html",
                    error=(
                        "This image is larger than 10 MB. "
                        "Please choose an image under 10 MB."
                    ),
                    searched=True,
                    results=[]
                )


            upload_response = requests.post(

                "https://picrd.com/api/upload",

                files={
                    "file": (
                        uploaded_file.filename,
                        file_data,
                        uploaded_file.mimetype
                    )
                },

                data={
                    "visibility": "unlisted"
                },

                timeout=60
            )


            try:
                upload_data = upload_response.json()

            except ValueError:

                upload_data = {}


            if (
                upload_response.status_code != 200
                or not upload_data.get("image_url")
            ):

                error_message = (
                    upload_data
                    .get("error")
                    or "Image upload failed."
                )

                return render_template(
                    "index.html",
                    error=f"Image upload failed: {error_message}",
                    searched=True,
                    results=[]
                )


            image_url = upload_data["image_url"]


        except requests.RequestException as e:

            return render_template(
                "index.html",
                error=f"Image upload failed: {e}",
                searched=True,
                results=[]
            )


    # =====================================================
    # IMAGE URL CHECK
    # =====================================================

    if not image_url:

        return render_template(
            "index.html",
            error=(
                "Please upload an image "
                "or provide an image URL."
            ),
            searched=True,
            results=[]
        )


    # =====================================================
    # GOOGLE LENS - SERPAPI
    # =====================================================

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


    # =====================================================
    # DOWNLOAD SOURCE IMAGE
    # =====================================================

    try:

        source_response = requests.get(
            image_url,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        source_response.raise_for_status()

        source_image = Image.open(
            io.BytesIO(
                source_response.content
            )
        ).convert("RGB")


    except Exception as e:

        return render_template(
            "index.html",
            error=f"Could not process image: {e}",
            searched=True,
            results=[]
        )


    # =====================================================
    # PROCESS VISUAL MATCHES
    # =====================================================

    results = []


    for item in data.get(
        "visual_matches",
        []
    ):

        link = item.get(
            "link",
            ""
        )

        title = item.get(
            "title",
            "Untitled"
        )

        thumbnail = item.get(
            "thumbnail",
            ""
        )


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


    # =====================================================
    # SORT RESULTS
    # =====================================================

    results.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )


    # =====================================================
    # SHOW RESULTS
    # =====================================================

    return render_template(
        "index.html",
        results=results,
        searched=True
    )


# =========================================================
# FILE TOO LARGE
# =========================================================

@app.errorhandler(413)
def request_entity_too_large(error):

    return render_template(
        "index.html",
        error=(
            "Image is too large. "
            "Maximum upload size is 30 MB."
        ),
        searched=True,
        results=[]
    ), 413


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    import os

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
            )
