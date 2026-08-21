import io
import os
import base64
import requests

from PIL import Image, UnidentifiedImageError
from flask import Flask, request, render_template


app = Flask(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

# Maximum browser upload size
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

SERPAPI_URL = "https://serpapi.com/search.json"

REQUEST_TIMEOUT = 60

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/120 Safari/537.36"
)


# =========================================================
# ERROR PAGE
# =========================================================

def render_error(message):

    return render_template(
        "index.html",
        error=message,
        searched=True,
        results=[]
    )


# =========================================================
# COMPRESS IMAGE FOR SERPAPI
# =========================================================

def prepare_image(file_data):

    try:

        image = Image.open(
            io.BytesIO(file_data)
        )

        image.load()

        # Convert unusual formats to RGB
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Resize large images
        max_size = 1600

        image.thumbnail(
            (max_size, max_size),
            Image.Resampling.LANCZOS
        )

        output = io.BytesIO()

        # JPEG keeps memory and upload size low
        if image.mode == "L":
            image = image.convert("RGB")

        image.save(
            output,
            format="JPEG",
            quality=85,
            optimize=True
        )

        return output.getvalue()

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ):

        return None

    except Exception:

        return None


# =========================================================
# SERPAPI IMAGE SEARCH
# =========================================================

def search_with_serpapi(
    image_data,
    serpapi_key
):

    try:

        # Convert image to base64
        encoded_image = base64.b64encode(
            image_data
        ).decode("utf-8")

        # SerpApi Google Lens can receive an image URL.
        # We use a data URL here.
        data_url = (
            "data:image/jpeg;base64,"
            + encoded_image
        )

        params = {

            "engine": "google_lens",

            "url": data_url,

            "api_key": serpapi_key,

            "hl": "en",

            "country": "us"

        }

        response = requests.get(

            SERPAPI_URL,

            params=params,

            headers={
                "User-Agent": USER_AGENT
            },

            timeout=REQUEST_TIMEOUT

        )

        response.raise_for_status()

        try:

            data = response.json()

        except ValueError:

            return None, "SerpApi returned an invalid response."

        if data.get("error"):

            return None, str(
                data.get(
                    "error"
                )
            )

        return data, None

    except requests.Timeout:

        return None, (
            "SerpApi request timed out. "
            "Please try again."
        )

    except requests.RequestException as e:

        return None, (
            "SerpApi request failed: "
            + str(e)
        )

    except Exception as e:

        return None, (
            "Unexpected search error: "
            + str(e)
        )


# =========================================================
# HOME
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return render_template(

        "index.html",

        searched=False,

        results=[],

        error=None

    )


# =========================================================
# SEARCH
# =========================================================

@app.route(
    "/search",
    methods=["POST"]
)
def search():

    # -----------------------------------------------------
    # SERPAPI KEY
    # -----------------------------------------------------

    serpapi_key = (

        request.form.get(
            "serpapi_key"
        )

        or os.environ.get(
            "SERPAPI_KEY"
        )

    )


    if not serpapi_key:

        return render_error(

            "SERPAPI_KEY is not configured. "
            "Please add SERPAPI_KEY in Render Environment Variables."

        )


    # -----------------------------------------------------
    # GET UPLOADED FILE
    # -----------------------------------------------------

    uploaded_file = request.files.get(
        "image"
    )


    # -----------------------------------------------------
    # GET IMAGE URL
    # -----------------------------------------------------

    image_url = request.form.get(
        "image_url",
        ""
    ).strip()


    image_data = None


    # =====================================================
    # OPTION 1: UPLOADED IMAGE
    # =====================================================

    if (
        uploaded_file
        and uploaded_file.filename
    ):

        try:

            original_data = uploaded_file.read()

            if not original_data:

                return render_error(
                    "The selected image is empty."
                )


            # -------------------------------------------------
            # SIZE CHECK
            # -------------------------------------------------

            if (
                len(original_data)
                > 30 * 1024 * 1024
            ):

                return render_error(
                    "Image is too large. "
                    "Maximum size is 30 MB."
                )


            # -------------------------------------------------
            # PREPARE IMAGE
            # -------------------------------------------------

            image_data = prepare_image(
                original_data
            )


            if not image_data:

                return render_error(
                    "The selected file is not a valid image."
                )


        except Exception as e:

            return render_error(
                "Could not process uploaded image: "
                + str(e)
            )


    # =====================================================
    # OPTION 2: IMAGE URL
    # =====================================================

    elif image_url:

        try:

            response = requests.get(

                image_url,

                headers={
                    "User-Agent": USER_AGENT
                },

                timeout=30

            )

            response.raise_for_status()

            if not response.content:

                return render_error(
                    "The image URL returned an empty file."
                )


            if (
                len(response.content)
                > 30 * 1024 * 1024
            ):

                return render_error(
                    "The remote image is larger than 30 MB."
                )


            image_data = prepare_image(
                response.content
            )


            if not image_data:

                return render_error(
                    "The provided URL does not contain a valid image."
                )


        except requests.Timeout:

            return render_error(
                "Downloading the image timed out."
            )


        except requests.RequestException as e:

            return render_error(
                "Could not download image: "
                + str(e)
            )


        except Exception as e:

            return render_error(
                "Could not process image: "
                + str(e)
            )


    # =====================================================
    # NOTHING PROVIDED
    # =====================================================

    else:

        return render_error(

            "Please upload an image "
            "or provide an image URL."

        )


    # =====================================================
    # GOOGLE LENS SEARCH
    # =====================================================

    data, error = search_with_serpapi(

        image_data,

        serpapi_key

    )


    # Release image memory
    image_data = None


    if error:

        return render_error(
            error
        )


    if not data:

        return render_error(
            "No search data was returned."
        )


    # =====================================================
    # PROCESS RESULTS
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


    # Limit results to keep Render memory low
    visual_matches = visual_matches[:20]


    for item in visual_matches:

        if not isinstance(
            item,
            dict
        ):

            continue


        link = item.get(
            "link",
            ""
        )


        if not link:

            continue


        title = item.get(
            "title",
            "Untitled"
        )


        thumbnail = item.get(
            "thumbnail",
            ""
        )


        # SerpApi already provides
        # visual search results.
        # No extra imagehash processing.


        results.append({

            "title": title,

            "link": link,

            "thumbnail": thumbnail,

            "similarity": "—"

        })


    # =====================================================
    # EXACT MATCHES
    # =====================================================

    exact_matches = data.get(
        "exact_matches",
        []
    )


    if isinstance(
        exact_matches,
        list
    ):

        for item in exact_matches[:10]:

            if not isinstance(
                item,
                dict
            ):

                continue


            link = item.get(
                "link",
                ""
            )


            if not link:

                continue


            title = item.get(
                "title",
                "Exact Match"
            )


            thumbnail = item.get(
                "thumbnail",
                ""
            )


            results.append({

                "title": title,

                "link": link,

                "thumbnail": thumbnail,

                "similarity": "Exact"

            })


    # =====================================================
    # REMOVE DUPLICATE LINKS
    # =====================================================

    unique_results = []

    seen_links = set()


    for result in results:

        link = result.get(
            "link"
        )


        if link in seen_links:

            continue


        seen_links.add(
            link
        )


        unique_results.append(
            result
        )


    results = unique_results[:30]


    # =====================================================
    # RETURN RESULTS
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
# GENERAL ERROR
# =========================================================

@app.errorhandler(500)
def internal_server_error(error):

    return render_error(

        "Server error occurred. "
        "Please try again."

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
