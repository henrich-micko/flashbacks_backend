from google.cloud import vision
import io


def check_nsfw_google(image_path):
    client = vision.ImageAnnotatorClient()
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.safe_search_detection(image=image)
    safe = response.safe_search_annotation

    categories = {
        "adult": safe.adult,
        "spoof": safe.spoof,
        "medical": safe.medical,
        "violence": safe.violence,
        "racy": safe.racy,
    }

    return categories, 5 in categories.values() or 4 in categories.values()

