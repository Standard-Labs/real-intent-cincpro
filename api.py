from concurrent.futures import ThreadPoolExecutor
import requests
import datetime
import pandas as pd
from typing import Any

from config import CINC_API_URL
from utils import rate_limited, AuthError
from auth import refresh_token

class CINCProDeliverer():
    """Delivers data to CINCPro CRM."""

    def __init__(
            self, 
            access_token: str, 
            tags: list[str] | None = None,
            add_zip_tags: bool = True,
            primary_agent: str | None = None,
            listing_agent: str | None = None,
            partner: str | None = None,
            base_url: str = CINC_API_URL,
            n_threads: int = 1,
        ):
        """
        Initialize the CINCProDeliverer.

        Args:
            access_token (str): The user's access token for CincPro.
            tags (list[str], optional): A list of tags to be added to the lead. Defaults to None.
            add_zip_tags (bool, optional): Whether to add zip code tags. Defaults to True.
            primary_agent (str, optional): The primary agent to be assigned to the lead. Defaults to None.
            listing_agent (str, optional): The listing agent to be assigned to the lead. Defaults to None.
            partner (str, optional): The partner to be assigned to the lead. Defaults to None.
            base_url (str, optional): The base URL for the CincPro API. Defaults to CINC_API_URL.
            n_threads (int, optional): The number of threads to use for delivering leads. Defaults to 1.
        """
        
        self.access_token: str = access_token
        self.base_url: str = base_url
        self.tags: list[str] = tags or []
        self.add_zip_tags: bool = add_zip_tags
        self.primary_agent: str | None = primary_agent
        self.listing_agent: str | None = listing_agent
        self.partner: str | None = partner
        
        # Keep track of failed leads
        self.failed_leads: list[dict] = []

        # Configuration stuff
        self.n_threads: int = n_threads

        # Make sure API credentials are valid
        if not self._verify_api_credentials():
            raise AuthError("Could not verify credentials for CincPro delivery. Please re-authenticate.")
    
    def get_failure_leads(self) -> list[dict]:
        """
        Get the list of failed leads.

        Returns:
            list[dict]: A list of dictionaries containing information about the failed leads.
        """
        return self.failed_leads    
    
    @property
    def api_headers(self) -> dict:
        """
        Generate the API headers for CINCPro requests.

        Returns:
            dict: A dictionary containing the necessary headers for API requests.
        """
        return {
            "Authorization": f"{self.access_token}",
            "Content-Type": "application/json",
        }
    
    @rate_limited()
    def _verify_api_credentials(self) -> bool:
        """
        Verify that the API credentials are valid. Refresh the token if necessary.

        Returns:
            bool: True if the credentials are valid, False otherwise.
        """
                
        response = requests.get(
            f"{self.base_url}/me",
            headers=self.api_headers
        )
        
        if response.status_code == 401:
            refresh_token()
            response = requests.get(
                f"{self.base_url}/me",
                headers=self.api_headers
            )
            return response.ok
        elif response.ok:
            return True
        else:
            return False
    
    def deliver(self, data: pd.DataFrame) -> list[dict]:
        """
        Deliver the PII data to CINCPro.

        Args:
            pii_md5s (list[MD5WithPII]): A list of MD5WithPII objects containing the PII data to be delivered.

        Returns:
            list[dict]: A list of response dictionaries from the CINCPro API for each delivered event.
        """
        
        with ThreadPoolExecutor(max_workers=self.n_threads) as executor:
            return list(executor.map(self._deliver_single_lead, ((row) for _, row in data.iterrows())))

    def _deliver_single_lead(self, lead: pd.Series) -> dict:
        """
        Deliver a single lead to CINCPro.

        Args:
            lead (pd.Series): A single row of the dataframe containing the PII data.

        Returns:
            dict: A response dictionary from the CINCPro API for the delivered event.
        """
        try:

            event_data = self._prepare_event_data(lead)   
            response = self._send_event(event_data)
            print(
                "trace", 
                (
                    f"Delivered lead: {lead.get("md5")}, "
                    f"response_status: {response.get('status', 'unknown')}"
                )
            )
            return response
        except Exception as e:
            self.failed_leads.append({
                "md5": lead.get("md5"),
                "error": str(e),
            })
            return {
                "status": "failed",
                "error": str(e),
            }

    def _prepare_event_data(self, lead: pd.Series) -> dict:
        """
        Prepare the event data for a single row of the dataframe.

        Args:
            lead (pd.Series): A single row of the dataframe containing the PII data.

        Returns:
            dict: A dictionary containing the prepared event data for the CINCPro API.
        """
                
        # get all the required info
        md5: str | None = lead.get("md5")
        first_name: str | None = lead.get("first_name")
        last_name: str | None = lead.get("last_name")
        email: str | None = lead.get("email_1")
        phone_1: str | None = str(lead.get("phone_1")) if lead.get("phone_1") else None
        phone_2: str | None = str(lead.get("phone_2")) if lead.get("phone_2") else None
        phone_3: str | None = str(lead.get("phone_3")) if lead.get("phone_3") else None
        address: str | None = lead.get("address")
        city: str | None = lead.get("city")
        state: str | None = lead.get("state")
        zip_code: str | None = str(lead.get("zip_code")) if lead.get("zip_code") else None
        insight: str | None = lead.get("insight")
        
        print("trace", f"Preparing event data for MD5: {md5}, first_name: {first_name}, last_name: {last_name}")

        # Prepare contact info
        contact_info: dict[str, Any] = {}
        
        contact_info["first_name"] = first_name
        contact_info["last_name"] = last_name

        if email:        
            contact_info["email"] = email
            contact_info["is_validated_email"] = True

        phone_numbers: dict[str, str | None] = {"cell_phone": phone_1, "home_phone": phone_2, "work_phone": phone_3}
        
        contact_info["phone_numbers"] = phone_numbers
            
        if all([address, city, state, zip_code]):
            contact_info["mailing_address"] = {
                "street": address,
                "city": city,
                "state": state,
                "postal_or_zip": zip_code
            }
        
        # Add Notes (Insight)
        notes: list[dict[str, str]] = []

        if (insight):
            notes.append({
                "content": insight,
                "category": "info",
                "created_by": "Real Intent",
                "created_date": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })  
            
        # Add tags as labels
        if self.tags:
            pass
        if self.add_zip_tags and lead["zip_code"]:
            pass        
            
        # Prepare event data according to CINC API schema
        event_data: dict[str, Any] = {
            "id": md5,
            "registered_date": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),            
            "info":{
                "status": "unworked",
                "source": "Real Intent",
                "contact": contact_info,
            },
            "assigned_agents":{
                "primary_agent": {
                    "id": self.primary_agent,
                },
                "listing_agent": {
                    "id": self.listing_agent,
                },
                "partner": {
                    "id": self.partner,
                },
            },
            "notes": notes,
        }
                        
        return event_data

    @rate_limited()
    def _send_event(self, event_data: dict) -> dict:
        """
        Send an event to the CINCPro API.

        Args:
            event_data (dict): The prepared event data to be sent to the API.

        Returns:
            dict: The response from the CINCPro API, either the JSON response or an ignored status message.

        Raises:
            requests.exceptions.HTTPError: If the API request fails.
        """
        print(
            "trace", 
            (
                f"Sending event to CINCPro API, "
                f"person: {event_data}"
            )
        )

        response = requests.post(
            f"{self.base_url}/leads", 
            json=event_data, 
            headers=self.api_headers
        )
        
        print("trace", f"Raw response: {response.text}, status_code: {response.status_code}")
                
        response.raise_for_status()
        return response.json()
    