import boto3
import ffmpeg
import os
import uuid
import io

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile


def generate_video_thumbnail(video_path):
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_DEFAULT_REGION
    )

    signed_url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': video_path
        },
        ExpiresIn=3600
    )

    thumbnail_path = f"media/private/flashback/{uuid.uuid4()}.jpg"
    temp_file_path = f"{settings.DATAFILES_DIR}/{uuid.uuid4()}.jpg"

    try: ffmpeg.input(signed_url, ss=0).output(temp_file_path, vframes=1, format='image2', update=1).run()
    except Exception as e:
        print("Exception while generating thumbnail: ", e)

    upload_image: InMemoryUploadedFile

    try:
        with open(temp_file_path, 'rb') as img_file:
            image_data = img_file.read()
            image_in_memory = io.BytesIO(image_data)

            uploaded_image = InMemoryUploadedFile(
                image_in_memory,
                None,
                thumbnail_path,
                'image/jpeg',  # Mime type
                len(image_data),  # File size
                None  # Charset
            )
    except Exception as e:
        print("Exception while reading thumbnail: ", e)

    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)

    return uploaded_image
