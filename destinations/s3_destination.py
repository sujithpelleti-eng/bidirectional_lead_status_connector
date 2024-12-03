import boto3
import gzip
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, Union
import os

logger = logging.getLogger(__name__)

class S3Destination:
    def __init__(self, bucket_name: str):
        # Check if LocalStack endpoint is specified
        endpoint_url = os.getenv("AWS_S3_ENDPOINT_URL", None)
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,  # Use LocalStack endpoint if specified
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "dummy"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "dummy"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN", "dummy"),
        )
        self.bucket_name = bucket_name

    def send(self, data: Dict[str, Any], provider: str, partner_id: str, file_type: str = "json"):
        """
        Sends data to S3 dynamically creating file paths and filenames based on the structure of the data.

        :param data: The data dictionary to be sent.
        :param prefix: The S3 prefix for organization.
        :param file_type: The file type to save the data as ('json' or 'xml').
        """
        try:
            if file_type not in ["json", "xml"]:
                raise ValueError(f"Unsupported file type: {file_type}")
                    
            # Validate data type for the specified file type
            if file_type == "xml" and not isinstance(data, (str, bytes, dict, ET.Element)):
                raise ValueError("Invalid data type for XML file type")

            s3_paths = self._generate_s3_paths(data, provider, partner_id, file_type)

            for s3_path, content in s3_paths.items():
                body = self._prepare_body(content, file_type)
                self._upload_to_s3(s3_path, body)

        except Exception as e:
            logger.error(f"Error writing to S3: {str(e)}")
            raise Exception(f"S3Destination send error: {str(e)}")

    def _prepare_body(self, content: Union[str, Dict[str, Any], ET.Element, bytes], file_type: str) -> bytes:
        """
        Prepares the body content for uploading to S3 by converting it to bytes.

        :param content: Content to prepare (JSON, XML, or already-encoded bytes).
        :param file_type: The type of file ("json" or "xml").
        :return: The content as bytes.
        """
        if file_type == "json":
            if isinstance(content, (dict, list)):
                return gzip.compress(json.dumps(content).encode("utf-8"))
            elif isinstance(content, str):
                return gzip.compress(content.encode("utf-8"))
            else:
                raise ValueError(f"Unsupported content type for JSON: {type(content)}")

        elif file_type == "xml":
            if isinstance(content, bytes):  # If already bytes, return directly
                return content
            elif isinstance(content, str):  # If string, encode to bytes
                return content.encode("utf-8")
            elif isinstance(content, dict):  # If dict, convert to XML and encode
                root = self._dict_to_et(content)
                return ET.tostring(root, encoding="utf-8")
            elif isinstance(content, ET.Element):  # If XML Element, serialize to bytes
                return ET.tostring(content, encoding="utf-8")
            else:
                raise ValueError(f"Unsupported content type for XML: {type(content)}")

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _upload_to_s3(self, s3_path: str, body: bytes):
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_path,
                Body=body,
            )
            logger.info(f"Successfully uploaded file to S3: {s3_path}, Size: {len(body)} bytes")
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {s3_path}, Error: {str(e)}")
            raise

    def _dict_to_et(self, data: Dict[str, Any], root_name: str = "root") -> ET.Element:
        root = ET.Element(root_name)
        for key, value in data.items():
            child = ET.SubElement(root, key)
            if isinstance(value, dict):
                child.append(self._dict_to_et(value))
            else:
                child.text = str(value)
        return root
    
    def _generate_s3_paths(self, data: Dict[str, Any], provider: str, partner_id: str, file_type: str) -> Dict[str, Union[str, Dict]]:
        """
        Generates S3 paths for the data based on the specified partitioning structure.

        :param data: Data dictionary containing endpoint and content.
        :param provider: The provider name for the S3 path.
        :param partner_id: The partner_id for the partition structure.
        :param file_type: The file type to be used for extension (e.g., "json" or "xml").
        :return: Dictionary mapping S3 paths to their content.
        """
        s3_paths = {}
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_hour = datetime.now().strftime("%H")
        run_date = current_date.replace("-", "")
        extension = "json.gz" if file_type == "json" else "xml"

        for endpoint, content in data.items():
            if isinstance(content, dict):
                for property_id, property_data in content.items():
                    # Define the S3 path
                    s3_path = (
                        f"raw/{provider}/partner_id={partner_id}/run_date={current_date}/hour={current_hour}/"
                        f"{endpoint}/{partner_id}_{run_date}{current_hour}.{extension}"
                    )
                    s3_paths[s3_path] = property_data
            else:
                # Handle cases where content is not nested by property_id
                s3_path = (
                    f"raw/{provider}/partner_id={partner_id}/run_date={current_date}/hour={current_hour}/"
                    f"{endpoint}/{partner_id}_{run_date}{current_hour}.{extension}"
                )
                s3_paths[s3_path] = content

        return s3_paths


    # def _generate_s3_paths(self, data: Dict[str, Any], prefix: str, file_type: str) -> Dict[str, Union[str, Dict]]:
    #     s3_paths = {}
    #     current_date = datetime.now().strftime("%Y-%m-%d")
    #     current_hour = datetime.now().strftime("%H")
    #     base_path = f"{prefix}/run_date={current_date}/hour={current_hour}" if prefix else f"run_date={current_date}/hour={current_hour}"
    #     extension = "json.gz" if file_type == "json" else "xml"

    #     for endpoint, content in data.items():
    #         timestamp = datetime.now().strftime("%Y%m%d%H")  # Format to include only the hour
    #         if isinstance(content, dict):
    #             for property_id, property_data in content.items():
    #                 filename = f"{property_id}_{timestamp}.{extension}"
    #                 s3_paths[f"{base_path}/{endpoint}/{filename}"] = property_data
    #         else:
    #             filename = f"{endpoint}_{timestamp}.{extension}"
    #             s3_paths[f"{base_path}/{filename}"] = content

    #     return s3_paths


if __name__ == "__main__":
    data = {
        "GetSeniorTourActivity": {
            "Property1": {"lead_id": "123", "status": "tour_completed"},
            "Property2": {"lead_id": "456", "status": "tour_scheduled"},
        },
        "GetSeniorResidentsByStatus": {"lead_id": "789", "status": "current_resident"},
    }

    s3 = S3Destination(bucket_name="provider-integration")
    s3.send(data, prefix="yardi-data", file_type="json")

    xml_data = {
        "GetSeniorTourActivity": {
            "Property1": "<TourActivity><ID>123</ID></TourActivity>",
            "Property2": "<TourActivity><ID>456</ID></TourActivity>",
        },
    }

    s3 = S3Destination(bucket_name="provider-integration")
    s3.send(xml_data, prefix="yardi-data", file_type="xml")

