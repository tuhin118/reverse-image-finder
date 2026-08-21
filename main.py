import io
import os
import requests
import imagehash

from PIL import Image, UnidentifiedImageError
from flask import Flask, request, render_template


app = Flask(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

# Maximum browser upload size = 30 MB
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

# Minimum visual similarity
SIMILARITY_THRESHOLD = 70

# External request timeout
REQUEST_TIMEOUT = 60

# User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


# =========================================================
# HELPER: RENDER ERROR
# =========================================================

def render_error(message):
    return render_template(
        "index.html",
        error=message,
        searched=True,
        results=[]
    )


# =========================================================
# IMAGE SIMILARITY
# =========================================================

def calculate_similarity(source_image, candidate_url):

    if not candidate_url:
        return 0

    try:

        response = requests.get(
            candidate_url,
            timeout=15,
            headers={
                "User-Agent": USER_AGENT
            }
        )

        response.raise_for_status()

        candidate_image = Image.open(
            io.BytesIO(response.content)
        ).convert("RGB")

        source_hash = imagehash.phash(
            source_image
        )

        candidate_hash = imagehash.phash(
            candidate_image
        )

        distance = (
            source_hash -
            candidate_hash
        )

        similarity = (
            1 -
            distance / 64
        ) * 100

        return round(
            max(
                0,
                min(
                    100,
                    similarity
                )
            ),
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

    # -----------------------------------------------------
    # SERPAPI KEY
    # -----------------------------------------------------

    serpapi_key = (
        request.form.get("serpapi_key")
        or os.environ.get("SERPAPI_KEY")
    )

    if not serpapi_key:

        return render_error(
            "SERPAPI_KEY is not configured. "
            "Please add your SerpApi key to the environment variables."
        )


    # -----------------------------------------------------
    # GET IMAGE URL
    # -----------------------------------------------------

    image_url = request.form.get(
        "image_url",
        ""
    ).strip()


    # -----------------------------------------------------
    # GET UPLOADED FILE
    # -----------------------------------------------------

    uploaded_file = request.files.get(
        "image"
    )


    # -----------------------------------------------------
    # CHECK UPLOADED IMAGE
    # -----------------------------------------------------

    if (
        uploaded_file
        and uploaded_file.filename
    ):

        try:

            # Read file
            file_data = uploaded_file.read()


            if not file_data:

                return render_error(
                    "The selected image is empty."
                )


            # -------------------------------------------------
            # FILE SIZE CHECK
            # -------------------------------------------------

            if len(file_data) > 30 * 1024 * 1024:

                return render_error(
                    "Image is too large. "
                    "Maximum upload size is 30 MB."
                )


            # -------------------------------------------------
            # CHECK THAT FILE IS ACTUALLY AN IMAGE
            # -------------------------------------------------

            try:

                test_image = Image.open(
                    io.BytesIO(file_data)
                )

                test_image.verify()

            except (
                UnidentifiedImageError,
                OSError,
                ValueError
            ):

                return render_error(
                    "The selected file is not a valid image."
                )


            # -------------------------------------------------
            # PICRD UPLOAD
            # -------------------------------------------------

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

                headers={
                    "User-Agent": USER_AGENT
                },

                timeout=REQUEST_TIMEOUT
            )


            # -------------------------------------------------
            # PARSE PICRD RESPONSE
            # -------------------------------------------------

            try:

                upload_data = (
                    upload_response.json()
                )

            except ValueError:

                upload_data = {}


            # -------------------------------------------------
            # CHECK PICRD RESPONSE
            # -------------------------------------------------

            if upload_response.status_code not in (
                200,
                201
            ):

                error_message = (
                    upload_data.get("error")
                    or upload_data.get("message")
                    or (
                        "Picrd returned HTTP "
                        + str(
                            upload_response.status_code
                        )
                    )
                )

                return render_error(
                    "Image upload failed: "
                    + error_message
                )


            # -------------------------------------------------
            # GET IMAGE URL
            # -------------------------------------------------

            image_url = (
                upload_data.get("image_url")
                or upload_data.get("url")
            )


            if not image_url:

                return render_error(
                    "Image upload failed. "
                    "The image hosting service did not return "
                    "a public image URL."
                )


        except requests.Timeout:

            return render_error(
                "Image upload timed out. "
                "Please try again."
            )


        except requests.RequestException as e:

            return render_error(
                "Image upload failed: "
                + str(e)
            )


        except Exception as e:

            return render_error(
                "Unexpected upload error: "
                + str(e)
            )


    # =====================================================
    # IMAGE URL CHECK
    # =====================================================

    if not image_url:

        return render_error(
            "Please upload an image "
            "or provide an image URL."
        )


    # =====================================================
    # GOOGLE LENS / SERPAPI
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

            headers={
                "User-Agent": USER_AGENT
            },

            timeout=REQUEST_TIMEOUT
        )


        # -------------------------------------------------
        # HTTP STATUS
        # -------------------------------------------------

        response.raise_for_status()


        # -------------------------------------------------
        # JSON
        # -------------------------------------------------

        try:

            data = response.json()

        except ValueError:

            return render_error(
                "SerpApi returned an invalid response."
            )


        # -------------------------------------------------
        # SERPAPI ERROR
        # -------------------------------------------------

        if data.get("error"):

            return render_error(
                "SerpApi search failed: "
                + str(
                    data.get(
                        "error"
                    )
                )
            )


    except requests.Timeout:

        return render_error(
            "Search request timed out. "
            "Please try again."
        )


    except requests.RequestException as e:

        return render_error(
            "Search request failed: "
            + str(e)
        )


    except Exception as e:

        return render_error(
            "Unexpected search error: "
            + str(e)
        )


    # =====================================================
    # DOWNLOAD SOURCE IMAGE
    # =====================================================

    try:

        source_response = requests.get(

            image_url,

            timeout=30,

            headers={
                "User-Agent": USER_AGENT
            }
        )


        source_response.raise_for_status()


        # -------------------------------------------------
        # CHECK CONTENT
        # -------------------------------------------------

        if not source_response.content:

            return render_error(
                "The image URL returned an empty file."
            )


        # -------------------------------------------------
        # OPEN IMAGE
        # -------------------------------------------------

        source_image = Image.open(

            io.BytesIO(
                source_response.content
            )

        ).convert("RGB")


    except requests.Timeout:

        return render_error(
            "Could not download the uploaded image "
            "from the image host."
        )


    except requests.RequestException as e:

        return render_error(
            "Could not download source image: "
            + str(e)
        )


    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ) as e:

        return render_error(
            "The image URL does not contain "
            "a valid image: "
            + str(e)
        )


    except Exception as e:

        return render_error(
            "Could not process image: "
            + str(e)
        )


    # =====================================================
    # PROCESS VISUAL MATCHES
    # =====================================================

    results = []


    visual_matches = data.get(
        "visual_matches",
        []
    )


    if not isinstance(
        visual_matches,
        list
    ):

        visual_matches = []


    for item in visual_matches:

        if not isinstance(
            item,
            dict
        ):
            continue


        # -------------------------------------------------
        # RESULT LINK
        # -------------------------------------------------

        link = item.get(
            "link",
            ""
        )


        if not link:
            continue


        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title = item.get(
            "title",
            "Untitled"
        )


        if not title:

            title = "Untitled"


        # -------------------------------------------------
        # THUMBNAIL
        # -------------------------------------------------

        thumbnail = item.get(
            "thumbnail",
            ""
        )


        # -------------------------------------------------
        # SIMILARITY
        # -------------------------------------------------

        similarity = 0


        if thumbnail:

            similarity = calculate_similarity(

                source_image,

                thumbnail

            )


        # -------------------------------------------------
        # ADD RESULT
        # -------------------------------------------------

        if (
            similarity >=
            SIMILARITY_THRESHOLD
        ):

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

        key=lambda x:
        x.get(
            "similarity",
            0
        ),

        reverse=True

    )


    # =====================================================
    # SHOW RESULTS
    # =====================================================

    return render_template(

        "index.html",

        results=results,

        searched=True,

        error=None

    )


# =========================================================
# FILE TOO LARGE
# =========================================================

@app.errorhandler(413)
def request_entity_too_large(error):

    return render_error(
        "Image is too large. "
        "Maximum upload size is 30 MB."
    ), 413


# =========================================================
# GENERAL SERVER ERROR
# =========================================================

@app.errorhandler(500)
def internal_server_error(error):

    return render_error(
        "Server error occurred while processing "
        "the image. Please try again."
    ), 500


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
