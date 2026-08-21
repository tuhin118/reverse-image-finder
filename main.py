import os
import io
import requests
import imagehash

from PIL import Image
from flask import Flask, request, render_template


app = Flask(__name__)

# Maximum upload size: 30 MB
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

# Only show results with 70% or higher visual similarity
SIMILARITY_THRESHOLD = 70


# =========================================================
# IMAGE SIMILARITY
# =========================================================

def calculate_similarity(source_image, candidate_url):
    try:
        response = requests.get(
            candidate_url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        candidate_image = Image.open(
            io.BytesIO(response.content)
        ).convert("RGB")

        source_hash = imagehash.phash(source_image)
        candidate_hash = imagehash.phash(candidate_image)

        distance = source_hash - candidate_hash

        similarity = (1 - (distance / 64)) * 100

        similarity = max(
            0,
            min(100, similarity)
        )

        return round(similarity, 2)

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

    serpapi_key = os.getenv(
        "SERPAPI_KEY"
    )

    imgbb_key = os.getenv(
        "IMGBB_API_KEY"
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
    # UPLOAD IMAGE TO IMGBB
    # =====================================================

    if (
        uploaded_file
        and uploaded_file.filename
    ):

        if not imgbb_key:

            return render_template(
                "index.html",

                error=(
                    "IMGBB_API_KEY is not configured. "
                    "Add it in Render Environment Variables."
                ),

                searched=True,

                results=[]
            )


        try:

            file_data = uploaded_file.read()


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


            if not upload_data.get(
                "success"
            ):

                return render_template(
                    "index.html",

                    error="Image upload failed.",

                    searched=True,

                    results=[]
                )


            image_url = (
                upload_data
                .get("data", {})
                .get("url", "")
            )


            if not image_url:

                return render_template(
                    "index.html",

                    error=(
                        "Could not create "
                        "a public image URL."
                    ),

                    searched=True,

                    results=[]
                )


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
    # SERPAPI GOOGLE LENS
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
    # DOWNLOAD ORIGINAL IMAGE
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

            error=(
                "Could not process "
                "the uploaded image: "
                + str(e)
            ),

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


        # -------------------------------------------------
        # Calculate real visual similarity
        # -------------------------------------------------

        similarity = 0


        if thumbnail:

            similarity = calculate_similarity(
                source_image,
                thumbnail
            )


        # -------------------------------------------------
        # Apply 70% threshold
        # -------------------------------------------------

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
# ERROR HANDLER - FILE TOO LARGE
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
