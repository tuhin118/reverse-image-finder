import os
import requests


def main():
    api_key = os.getenv("SERPAPI_KEY")

    if not api_key:
        print("Error: SERPAPI_KEY is not configured.")
        return

    image_url = input("Enter image URL: ").strip()

    if not image_url:
        print("Error: Image URL is required.")
        return

    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": api_key,
    }

    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        print("\nReverse Image Search Results:\n")

        visual_matches = data.get("visual_matches", [])

        if not visual_matches:
            print("No matching results found.")
            return

        for i, result in enumerate(visual_matches, 1):
            title = result.get("title", "No title")
            link = result.get("link", "No link")

            print(f"{i}. {title}")
            print(f"   {link}\n")

    except requests.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
