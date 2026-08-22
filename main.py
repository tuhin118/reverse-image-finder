import io
import os
import requests

from PIL import Image, UnidentifiedImageError
from flask import Flask, request, render_template
from visitor_counter import add_visit, get_visits


app = Flask(__name__)

# =========================================================
# CONFIGURATION
# =========================================================

# Browser upload limit = 30 MB
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"
SERPAPI_IMAGE_URL = "https://serpapi.com/image"

REQUEST_TIMEOUT = 60

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
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
# PREPARE UPLOADED IMAGE
# =========================================================

def prepare_image(file_data):

    try:

        image = Image.open(
            io.BytesIO(file_data)
        )

        image.load()

        # Convert to RGB
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Prevent extremely large images
        max_dimension = 1400

        image.thumbnail(
            (max_dimension, max_dimension),
            Image.Resampling.LANCZOS
        )

        # Try several JPEG qualities until <= 500 KB
        for quality in (80, 70, 60, 50, 40, 30):

            output = io.BytesIO()

            image.save(
                output,
                format="JPEG",
                quality=quality,
                optimize=True
            )

            result = output.getvalue()

            if len(result) <= 500 * 1024:

                return result

        # If still too large, resize further
        for dimension in (1100, 900, 700, 500):

            small_image = image.copy()

            small_image.thumbnail(
                (dimension, dimension),
                Image.Resampling.LANCZOS
            )

            output = io.BytesIO()

            small_image.save(
                output,
                format="JPEG",
                quality=35,
                optimize=True
            )

            result = output.getvalue()

            if len(result) <= 500 * 1024:

                return result

        return None

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ):

        return None

    except Exception:

        return None


# =========================================================
# UPLOAD IMAGE TO SERPAPI IMAGE API
# =========================================================

def upload_image_to_serpapi(
    image_data,
    serpapi_key
):

    try:

        response = requests.post(

            SERPAPI_IMAGE_URL,

            files={
                "image": (
                    "image.jpg",
                    image_data,
                    "image/jpeg"
                )
            },

            data={
                "api_key": serpapi_key
            },

            headers={
                "User-Agent": USER_AGENT
            },

            timeout=REQUEST_TIMEOUT
        )

        # Try JSON first
        try:

            data = response.json()

        except ValueError:

            data = {}

        # HTTP error
        if not response.ok:

            error_message = (
                data.get("error")
                or data.get("message")
                or (
                    "SerpApi Image API returned HTTP "
                    + str(response.status_code)
                )
            )

            return None, error_message

        # SerpApi API error
        if data.get("error"):

            return None, str(
                data.get("error")
            )

        image_id = data.get(
            "image_id"
        )

        if not image_id:

            return None, (
                "SerpApi did not return an image_id."
            )

        return image_id, None

    except requests.Timeout:

        return None, (
            "Image upload to SerpApi timed out."
        )

    except requests.RequestException as e:

        return None, (
            "Could not upload image to SerpApi: "
            + str(e)
        )

    except Exception as e:

        return None, (
            "Unexpected image upload error: "
            + str(e)
        )


# =========================================================
# GOOGLE LENS SEARCH USING IMAGE ID
# =========================================================

def search_with_image_id(
    image_id,
    serpapi_key
):

    try:

        params = {

            "engine": "google_lens",

            "image_id": image_id,

            "api_key": serpapi_key,

            "hl": "en",

            "country": "us"

        }

        response = requests.get(

            SERPAPI_SEARCH_URL,

            params=params,

            headers={
                "User-Agent": USER_AGENT
            },

            timeout=REQUEST_TIMEOUT
        )

        try:

            data = response.json()

        except ValueError:

            return None, (
                "SerpApi returned an invalid response."
            )

        if not response.ok:

            error_message = (
                data.get("error")
                or (
                    "SerpApi returned HTTP "
                    + str(response.status_code)
                )
            )

            return None, error_message

        if data.get("error"):

            return None, str(
                data.get("error")
            )

        return data, None

    except requests.Timeout:

        return None, (
            "Google Lens search timed out. "
            "Please try again."
        )

    except requests.RequestException as e:

        return None, (
            "Google Lens request failed: "
            + str(e)
        )

    except Exception as e:

        return None, (
            "Unexpected Google Lens error: "
            + str(e)
        )


# =========================================================
# GOOGLE LENS SEARCH USING PUBLIC URL
# =========================================================

def search_with_url(
    image_url,
    serpapi_key
):

    try:

        params = {

            "engine": "google_lens",

            "url": image_url,

            "api_key": serpapi_key,

            "hl": "en",

            "country": "us"

        }

        response = requests.get(

            SERPAPI_SEARCH_URL,

            params=params,

            headers={
                "User-Agent": USER_AGENT
            },

            timeout=REQUEST_TIMEOUT
        )

        try:

            data = response.json()

        except ValueError:

            return None, (
                "SerpApi returned an invalid response."
            )

        if not response.ok:

            error_message = (
                data.get("error")
                or (
                    "SerpApi returned HTTP "
                    + str(response.status_code)
                )
            )

            return None, error_message

        if data.get("error"):

            return None, str(
                data.get("error")
            )

        return data, None

    except requests.Timeout:

        return None, (
            "Google Lens search timed out. "
            "Please try again."
        )

    except requests.RequestException as e:

        return None, (
            "Google Lens request failed: "
            + str(e)
        )

    except Exception as e:

        return None, (
            "Unexpected Google Lens error: "
            + str(e)
        )


# =========================================================
# PROCESS SERPAPI RESULTS
# =========================================================

def process_results(data):

    results = []

    # -----------------------------------------------------
    # VISUAL MATCHES
    # -----------------------------------------------------

    visual_matches = data.get(
        "visual_matches",
        []
    )

    if not isinstance(
        visual_matches,
        list
    ):

        visual_matches = []

    for item in visual_matches[:20]:

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

        results.append({

            "title": title or "Untitled",

            "link": link,

            "thumbnail": thumbnail,

            "similarity": "—"

        })

    # -----------------------------------------------------
    # EXACT MATCHES
    # -----------------------------------------------------

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

                "title": title or "Exact Match",

                "link": link,

                "thumbnail": thumbnail,

                "similarity": "Exact"

            })

    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    unique_results = []

    seen_links = set()

    for result in results:

        link = result.get(
            "link"
        )

        if not link:

            continue

        if link in seen_links:

            continue

        seen_links.add(
            link
        )

        unique_results.append(
            result
        )

    return unique_results[:30]


# =========================================================
# VISITOR SETTINGS
# =========================================================

@app.route(
    "/visitor-settings",
    methods=["GET"]
)
def visitor_settings():

    visits = get_visits()

    return render_template(

        "visitor-settings.html",

        today=visits["today"],

        total=visits["total"]

    )


# =========================================================
# HOME
# =========================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    # Count one visit when the homepage is opened
    add_visit()

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
    # GET FILE
    # -----------------------------------------------------

    uploaded_file = request.files.get(
        "image"
    )


    # -----------------------------------------------------
    # GET URL
    # -----------------------------------------------------

    image_url = request.form.get(
        "image_url",
        ""
    ).strip()


    # =====================================================
    # UPLOADED IMAGE
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

            # 30 MB maximum
            if len(original_data) > (
                30 * 1024 * 1024
            ):

                return render_error(
                    "Image is too large. "
                    "Maximum size is 30 MB."
                )

            # Compress to <= 500 KB
            image_data = prepare_image(
                original_data
            )

            # Release original image data
            original_data = None

            if not image_data:

                return render_error(
                    "Could not compress the image "
                    "to the required size."
                )

        except Exception as e:

            return render_error(
                "Could not process uploaded image: "
                + str(e)
            )


        # -------------------------------------------------
        # SERPAPI IMAGE API
        # -------------------------------------------------

        image_id, error = (
            upload_image_to_serpapi(
                image_data,
                serpapi_key
            )
        )

        # Release image memory
        image_data = None

        if error:

            return render_error(
                "Image upload failed: "
                + error
            )


        # -------------------------------------------------
        # GOOGLE LENS
        # -------------------------------------------------

        data, error = search_with_image_id(

            image_id,

            serpapi_key

        )


    # =====================================================
    # IMAGE URL
    # =====================================================

    elif image_url:

        # Public URL goes directly to Google Lens.
        data, error = search_with_url(

            image_url,

            serpapi_key

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
    # CHECK SEARCH ERROR
    # =====================================================

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

    results = process_results(
        data
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
        "Maximum size is 30 MB."

    ), 413


# =========================================================
# GENERAL SERVER ERROR
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
