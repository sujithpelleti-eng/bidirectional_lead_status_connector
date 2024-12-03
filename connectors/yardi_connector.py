import logging
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Dict, List

from connectors.base_soap_connector import BaseSOAPConnector
from parsers.yardi_parser import YardiParser

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class YardiConnector(BaseSOAPConnector):
    def __init__(self, config: dict):
        """
        Initializes the YardiConnector with configuration parameters and sets up the parser.

        :param config: Configuration dictionary containing API URL, _credentials, and namespace.
        """
        super().__init__(config)
        self._api_url = config.get("api_url")
        self._credentials = config.get("credentials")
        self._namespace = config.get("namespace")
        self._base_url = config.get("base_url")

        # self._api_url = config.get('api_url')
        # self._credentials = config.get('_credentials')  # Ensure this is properly set
        # self._base_url = config.get('base_url')
        # self._namespace = config.get('namespace')

        # Check if credentials or other required fields are None
        if not all([self._credentials, self._api_url, self._namespace]):
            raise ValueError("Missing configuration parameters.")

        logger.info("YardiConnector initialized with provided configuration.")

    def build_request(self, method: str, body_content: str) -> str:
        """
        Constructs a SOAP request envelope for the specified method.

        :param method: The SOAP method to call.
        :param body_content: The body content specific to the SOAP action.
        :return: The SOAP request XML as a string.
        """
        return f"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <{method} xmlns="{self._namespace}">
              {body_content}
            </{method}>
          </soap:Body>
        </soap:Envelope>
        """

    def _send_request(self, method: str, body_content: str, soap_action: str) -> Any:
        """
        Sends a SOAP request to the specified endpoint and parses the response.

        :param method: The SOAP method name.
        :param body_content: The XML body content for the request.
        :param soap_action: The SOAP action header value.
        :return: Parsed response data.
        """
        logger.info(f"Sending request for {method} with SOAP action: {soap_action}")
        headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": soap_action}
        request_xml = self.build_request(method, body_content)
        response = self._send_soap_request(self._base_url, headers, request_xml)
        logger.debug(f"Received response for {method}")
        return response

    def fetch_raw_data(
        self, from_date: str = "", to_date: str = "", full_refresh: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetches raw data from multiple Yardi endpoints for each YardiPropertyId.

        :param from_date: Start date for fetching data (YYYY-MM-DD).
        :param to_date: End date for fetching data (YYYY-MM-DD).
        :param full_refresh: If True, fetch data for the last year.
        :return: A dictionary where each key is an endpoint name, and the value is a dictionary of property_id: data.
        """
        # Validate provided dates
        if not from_date or not to_date:
            raise ValueError("Both 'from_date' and 'to_date' must be provided.")

        logger.info(
            f"Fetching raw data from {from_date} to {to_date} for all YardiPropertyIds."
        )
        raw_data = {
            "GetSeniorProspectActivity_tour_activity": {},
            # "GetSeniorResidentsByStatus": {},
            "GetSeniorResidentsADTEvents_movein": {},
            "GetSeniorProspectActivity_valid_lead": {},
        }

        for yardi_property_id in self._credentials["YardiPropertyId"]:
            logger.info(f"Processing YardiPropertyId: {yardi_property_id}")
            raw_data["GetSeniorProspectActivity_tour_activity"][
                yardi_property_id
            ] = self._fetch_tour_activity(
                yardi_property_id=yardi_property_id,
                activity_categoty="Tours",
                from_date=from_date,
                to_date=to_date,
            )
            raw_data["GetSeniorResidentsADTEvents_movein"][
                yardi_property_id
            ] = self._fetch_adt_events(
                yardi_property_id=yardi_property_id,
                event_type="Move In",
                from_date=from_date,
                to_date=to_date,
            )
            raw_data["GetSeniorProspectActivity_valid_lead"][
                yardi_property_id
            ] = self._fetch_lead_status_change(
                yardi_property_id=yardi_property_id,
                activity_categoty="Status Change",
                from_date=from_date,
                to_date=to_date,
            )

        return raw_data

    def _fetch_tour_activity(
        self,
        yardi_property_id: str,
        activity_categoty: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict[str, Any]]:
        return self._fetch_senior_prospect_activity(
            yardi_property_id=yardi_property_id,
            activity_categoty=activity_categoty,
            from_date=from_date,
            to_date=to_date,
        )

    def _fetch_lead_status_change(
        self,
        yardi_property_id: str,
        activity_categoty: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict[str, Any]]:
        return self._fetch_senior_prospect_activity(
            yardi_property_id=yardi_property_id,
            activity_categoty=activity_categoty,
            from_date=from_date,
            to_date=to_date,
        )

    def _fetch_senior_prospect_activity(
        self,
        yardi_property_id: str,
        activity_categoty: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetches prospect activities for a given Yardi property ID and activity result type.

        :param yardi_property_id: The Yardi property ID.
        :param activity_result_type: The ActivityResultType to filter (e.g., 'Activate', 'Tours').
        :return: List of parsed activities.
        """
        body_content = f"""
            <UserName>{self._credentials['username']}</UserName>
            <Password>{self._credentials['password']}</Password>
            <ServerName>{self._credentials['ServerName']}</ServerName>
            <Database>{self._credentials['Database']}</Database>
            <Platform>SQL Server</Platform>
            <InterfaceEntity>{self._credentials['InterfaceEntity']}</InterfaceEntity>
            <InterfaceLicense>{self._credentials['license']}</InterfaceLicense>
            <YardiPropertyId>{yardi_property_id}</YardiPropertyId>
            <ProspectExtReference></ProspectExtReference>
            <ProspectID></ProspectID>
            <ContactExtReference></ContactExtReference>
            <ContactID></ContactID>
            <Email></Email>
            <FromDate>{from_date}</FromDate>
            <Todate>{to_date}</Todate>
            <SourceName>Caring.com</SourceName>
            <YardiProspectId></YardiProspectId>
            <ActivityCategory>{activity_categoty}</ActivityCategory>
        """
        return self._send_request(
            "GetSeniorProspectActivity",
            body_content,
            f"{self._namespace}/GetSeniorProspectActivity",
        )

    def _fetch_senior_residents_by_status(
        self, yardi_property_id, status: str = ""
    ) -> List[Dict[str, Any]]:
        body_content = f"""
            <UserName>{self._credentials['username']}</UserName>
            <Password>{self._credentials['password']}</Password>
            <ServerName>{self._credentials['ServerName']}</ServerName>
            <Database>{self._credentials['Database']}</Database>
            <Platform>SQL Server</Platform>
            <InterfaceEntity>{self._credentials['InterfaceEntity']}</InterfaceEntity>
            <InterfaceLicense>{self._credentials['license']}</InterfaceLicense>
            <YardiPropertyId>{yardi_property_id}</YardiPropertyId>
            <Status>{status}</Status>
            <AsofDate></AsofDate>
            <SourceName></SourceName>
        """
        return self._send_request(
            "GetSeniorResidentsByStatus",
            body_content,
            f"{self._namespace}/GetSeniorResidentsByStatus",
        )
        # return self._parser.parse(response, "Yardi", "GetSeniorResidentsByStatus")

    def _fetch_adt_events(
        self,
        yardi_property_id,
        event_type: str = "",
        from_date: str = "",
        to_date: str = "",
    ) -> List[Dict[str, Any]]:
        body_content = f"""
            <UserName>{self._credentials['username']}</UserName>
            <Password>{self._credentials['password']}</Password>
            <ServerName>{self._credentials['ServerName']}</ServerName>
            <Database>{self._credentials['Database']}</Database>
            <Platform>SQL Server</Platform>
            <InterfaceEntity>{self._credentials['InterfaceEntity']}</InterfaceEntity>
            <InterfaceLicense>{self._credentials['license']}</InterfaceLicense>
            <YardiPropertyId>{yardi_property_id}</YardiPropertyId>
            <EventType>{event_type}</EventType>
            <SourceName></SourceName>
            <FromDate>{from_date}</FromDate>
            <Todate>{to_date}</Todate>
        """
        return self._send_request(
            "GetSeniorResidentsADTEvents",
            body_content,
            f"{self._namespace}/GetSeniorResidentsADTEvents",
        )
        # return self._parser.parse(response, "Yardi", "GetSeniorResidentsADTEvents")


if __name__ == "__main__":
    config = {
        "api_url": "https://www.yardipcv.com/8223tp7s7snr/WebServices/ItfSeniorResidentData.asmx",
        "credentials": {
            "username": "caringws",
            "password": "W!tLUk22oMZJEXb",
            "license": "MIIBEAYJKwYBBAGCN1gDoIIBATCB/gYKKwYBBAGCN1gDAaCB7zCB7AIDAgABAgJoAQICAIAEAAQQ/zrUM5V4Qr2KBVWEc5edvQSByGh5TyWjIKGTM+lVzCjVodDBj+t6QaGH/Sm+Rg4dq8hF6VyrBtoHAR2DUFTAAuVNws/mRdtWozYBDQ6FgDbnpsLJ+jcEpv+FYYtZWWRS0lpkH9DUxMN4OSvGB98kQwzBlKVeSWRGlxJZhG6YAvCbHudnl25BeDFjFKuzq3rov+yKGpYpCEdIKxbn+Pl7sTd1GrpKg8Rf5G1zjkbAiiTNybK0iI+KV6xv08ZX5YkTpm938cmnYgFYCo3OKO5TA2pIjpGeWg2qNgbc",
            "ServerName": "afqoml_senior_itf",
            "Database": "afqoml_senior_itf",
            "InterfaceEntity": "Caring.com",
            "YardiPropertyId": ["c1233"],
        },
        "base_url": "https://www.yardipcv.com/8223tp7s7snr/WebServices/ItfSeniorResidentData.asmx",
        "namespace": "http://tempuri.org/YSI.Senior.SeniorInterface.WebServices/ItfSeniorResidentData",
    }

    yc = YardiConnector(config)
    results = yc.fetch_raw_data(from_date="2024-12-01", to_date="2024-12-03")
    # results = yc.fetch_raw_data(full_refresh=True)
    # results = yc.fetch_raw_data()
    # print(results)
    yp = YardiParser(1, "65865858585")
    final_result = yp.parse(results)
    print(final_result)
