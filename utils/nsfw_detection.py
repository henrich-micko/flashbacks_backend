from django.conf import settings
import boto3


def _process_result(result):
    nsfw_labels = ["Explicit Nudity", "Suggestive", "Violence", "Drugs"]

    categories = {
        label["ModerationLabel"]["Name"]: label["ModerationLabel"]["Confidence"]
        for label in result["ModerationLabels"]
        if label["ModerationLabel"]["Name"] in nsfw_labels
    }

    is_nsfw = any(confidence > 75 for confidence in categories.values())

    return categories, is_nsfw


def check_nsfw_photo_aws(media_path):
    rekognition = boto3.client(
        'rekognition',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION # Your region
    )

    response = rekognition.detect_moderation_labels(
        Image={"S3Object": {"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Name": media_path}},
        MinConfidence=75  # Adjust threshold as needed
    )

    return _process_result(response)


def start_video_moderation(media_path):
    rekognition = boto3.client(
        'rekognition',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    response = rekognition.start_content_moderation(
        Video={
            'S3Object': {
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Name': media_path
            }
        },
        MinConfidence=75
    )

    return response['JobId']


def get_video_moderation_results(job_id):
    rekognition = boto3.client(
        'rekognition',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    response = rekognition.get_content_moderation(JobId=job_id)

    if response.get("JobStatus") == "SUCCEEDED":
        return _process_result(response)
    return {}, None
