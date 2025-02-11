import os

# Initialize the S3 client
# s3_client = boto3.client('s3')


def generate_s3_key(
    bucket_name: str,
    system_name: str,
    endpoint: str,
    file_name: str,
    property_id: str = None,
) -> str:
    """
    Generates the S3 key for the file path based on the system and endpoint requirements.

    :param bucket_name: Name of the S3 bucket.
    :param system_name: Name of the system (e.g., "yardi").
    :param endpoint: The specific endpoint name.
    :param file_name: The file name with extension (e.g., "data.xml").
    :param property_id: Optional property ID. Used if available.
    :return: Full S3 key path.
    """
    # Base path for the system and endpoint
    base_path = f"{bucket_name}/raw/{system_name}/{endpoint}"

    # Add property ID if provided
    if property_id:
        s3_key = f"{base_path}/{property_id}/{file_name}"
    else:
        s3_key = f"{base_path}/{file_name}"

    return s3_key
