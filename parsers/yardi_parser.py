import json
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from common.models import StatusUpdateQueue

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class YardiParser:
    """
    Parser class for Yardi API responses. Contains methods to parse specific types of responses
    for different Yardi endpoints.
    """

    def __init__(self, system_config_id: str, execution_id: str):
        """
        Initialize YardiParser with configuration data.

        :param config: Configuration dictionary containing metadata for parsing.
        """
        self.system_config_id = system_config_id
        self.execution_id = execution_id
        if not self.system_config_id or not self.execution_id:
            raise ValueError("Both 'system_config_id' and 'execution_id' are required.")

    def parse(self, raw_data: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Parses the raw SOAP responses grouped by endpoint and property_id, filters based on priority, and keeps only the latest status.

        :param raw_data: Dictionary where each key is an endpoint name, and each value is a dictionary
                        of property_id: data.
        :return: List of parsed records grouped by lead_id with the latest status.
        """
        parsed_data = []
        grouped_by_lead = {}

        # Define a priority map for statuses
        priority_map = {
            "valid_lead": 1,
            "tour_scheduled": 2,
            "tour_completed": 3,
            "move_in_commitment": 4,
        }

        for endpoint_name, property_data in raw_data.items():
            for property_id, response in property_data.items():
                if endpoint_name == "GetSeniorProspectActivity_tour_activity":
                    parsed_data.extend(self._parse_tour_activity(response, property_id))
                # elif endpoint_name == "GetSeniorResidentsByStatus":
                #     parsed_data.extend(self._parse_senior_residents(response, property_id))
                elif endpoint_name == "GetSeniorResidentsADTEvents_movein":
                    parsed_data.extend(self._parse_adt_events(response, property_id))
                elif endpoint_name == "GetSeniorProspectActivity_valid_lead":
                    parsed_data.extend(
                        self._parse_prospect_activity(response, property_id)
                    )

        # Group by lead_id and filter for the highest-priority, latest record
        for record in parsed_data:
            lead_id = record.lead_id
            if not lead_id:
                continue

            current_priority = priority_map.get(record.status.lower(), float("inf"))

            if lead_id in grouped_by_lead:
                existing_record = grouped_by_lead[lead_id]
                existing_priority = priority_map.get(
                    existing_record.status.lower(), float("inf")
                )

                # Replace the record if it has a higher priority or the same priority but is more recent
                if current_priority > existing_priority or (
                    current_priority == existing_priority
                ):
                    grouped_by_lead[lead_id] = record
            else:
                grouped_by_lead[lead_id] = record
        # return parsed_data
        return list(grouped_by_lead.values())

    def _parse_tour_activity(
        self, response: str, property_id: str
    ) -> List[StatusUpdateQueue]:
        """
        Parses the 'GetSeniorProspectActivity' response.

        :param response: The raw XML response from 'GetSeniorProspectActivity'.
        :param property_id: The ID of the Yardi property for this response.
        :return: A list of parsed prospect activity records.
        """
        root = ET.fromstring(response)
        tours = []

        for tour in root.findall(".//Prospect"):
            lead_id = tour.findtext("ExtReference")
            activity = tour.find(".//Activity")

            if lead_id and activity is not None:
                result_type = activity.findtext("ActivityResultType")
                activity_type = activity.findtext("ActivityType")
                result_date = activity.findtext("ActivityResultDate")
                start_date = activity.findtext("ActivityStartDate")
                start_time = activity.findtext("ActivityStartTime", "")

                if result_type and "completed" in result_type.lower():
                    status = "tour_completed"
                    notes = (
                        f"Tour completed on {result_date} with result '{result_type}' "
                        f"and type '{activity_type}' for property ID {property_id}."
                    )
                else:
                    status = "tour_scheduled"
                    notes = (
                        f"Tour scheduled on {start_date} {start_time} with "
                        f"type '{activity_type}' for property ID {property_id}."
                    )

                tours.append(
                    StatusUpdateQueue(
                        execution_id=self.execution_id,
                        system_config_id=self.system_config_id,
                        lead_id=lead_id,
                        status=status,
                        sub_status="N/A",
                        notes=notes,
                        lead_json={
                            "lead_id": lead_id,
                            "status": status,
                            "sub_status": "N/A",
                            "notes": notes,
                        },
                    )
                )

        return tours

    # def _parse_senior_residents(self, response: str, property_id: str) -> List[Dict[str, Any]]:
    #     """
    #     Parses the 'GetSeniorResidentsByStatus' response.

    #     :param response: The raw XML response from 'GetSeniorResidentsByStatus'.
    #     :param property_id: The ID of the Yardi property for this response.
    #     :return: A list of parsed senior resident records.
    #     """
    #     root = ET.fromstring(response)
    #     residents = []
    #     for resident in root.findall(".//Resident"):
    #         lead_id=resident.findtext("ExtReference")
    #         if lead_id not in [None, ""]:
    #             residents.append(StatusUpdateQueue(
    #                 system_config_id=self.system_config_id,
    #                 lead_id=lead_id,
    #                 status="move_in_commitment",
    #                 sub_status="",
    #                 notes=f"Resident located at unit {resident.findtext('UnitCode')} for property ID {property_id}",
    #                 lead_json={
    #                     "lead_id": resident.findtext("ExtReference"),
    #                     "status": "move_in_commitment",
    #                     "sub_status": "",
    #                     "notes": f"Resident Moved in on {resident.findtext('MoveInDate')} at unit {resident.findtext('UnitCode')} for property ID {property_id}",
    #                 }
    #             ))
    #     return residents

    def _parse_adt_events(
        self, response: str, property_id: str
    ) -> List[Dict[str, Any]]:
        """
        Parses the 'GetSeniorResidentsADTEvents' response.

        :param response: The raw XML response from 'GetSeniorResidentsADTEvents'.
        :param property_id: The ID of the Yardi property for this response.
        :return: A list of parsed ADT event records.
        """
        root = ET.fromstring(response)
        events = []
        for event in root.findall(".//Resident"):
            lead_id = event.findtext("ExtReference")
            status = (
                "move_in_commitment"
                if event.findtext("EventType") or "status_unknown" == "Move In"
                else ""
            )
            if lead_id not in [None, ""]:
                events.append(
                    StatusUpdateQueue(
                        execution_id=self.execution_id,
                        system_config_id=self.system_config_id,
                        lead_id=lead_id,
                        status=status,
                        sub_status="N/A",
                        notes=f"Prospect Moved In on {event.findtext('ResidentEventDate')} for property ID {property_id}",
                        lead_json={
                            "lead_id": lead_id,
                            "status": status,
                            "sub_status": "N/A",
                            "notes": f"Prospect Moved In on {event.findtext('ResidentEventDate')} for property ID {property_id}",
                        },
                    )
                )
        return events

    def _parse_prospect_activity(
        self, response: str, property_id: str
    ) -> List[StatusUpdateQueue]:
        """
        Parses the 'GetSeniorProspectActivity' response.

        :param response: The raw XML response from 'GetSeniorProspectActivity'.
        :param property_id: The ID of the Yardi property for this response.
        :param activity_result_type: The type of activity result to filter for.
        :return: A list of parsed prospect activity records.
        """
        root = ET.fromstring(response)
        activities = []

        for prospect in root.findall(".//Prospect"):
            lead_id = prospect.findtext("ExtReference")
            activity = prospect.find(".//Activity")
            result_type = (
                activity.findtext("ActivityResultType")
                if activity is not None
                else None
            )

            if lead_id not in [None, ""] and result_type == "Activate":
                activities.append(
                    StatusUpdateQueue(
                        execution_id=self.execution_id,
                        system_config_id=self.system_config_id,
                        lead_id=lead_id,
                        status="valid_lead" if result_type == "Activate" else "",
                        sub_status="timeframe_30",
                        notes=f"Lead status changed to '{result_type}' on {activity.findtext('ActivityResultDate')} for property ID {property_id}",
                        lead_json={
                            "lead_id": lead_id,
                            "status": "valid_lead" if result_type == "Activate" else "",
                            "sub_status": "timeframe_30",
                            "notes": f"Lead status changed to '{result_type}' on {activity.findtext('ActivityResultDate')} for property ID {property_id}",
                        },
                    )
                )

        return activities
