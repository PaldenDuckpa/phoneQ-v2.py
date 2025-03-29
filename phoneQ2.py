import sys
import json
import requests
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import argparse
from datetime import datetime
import ipaddress  # For IP address validation

# ASCII Art and Tool Information
TOOL_NAME = """
██████╗ ██╗  ██╗ ██████╗ ███╗  ██╗███████╗ ██████╗ 
██╔══██╗██║  ██║██╔═══██╗████╗ ██║██╔════╝██╔═══██╗
██████╔╝███████║██║  ██║██╔██╗ ██║█████╗  ██║  ██║
██╔═══╝ ██╔══██║██║  ██║██║╚██╗██║██╔══╝  ██║  ██║
██║    ██║  ██║╚██████╔╝██║ ╚████║███████╗╚██████╔╝
╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝ ╚═════╝ 
"""

VERSION = "2.0"
AUTHOR = "Your Name"  # Replace with your actual name
DESCRIPTION = "PhoneQ - Advanced Phone Number Intelligence Tool (v2.0)"

# API Keys (Ideally, these should be loaded from a config file or environment variables)
IPINFO_API_KEY = ""  # Replace with your IPinfo.io API key (if you choose to use it)


class PhoneQ:
    """
    A class for investigating phone numbers and IP addresses.
    """

    def __init__(self, target):
        """
        Initializes the PhoneQ object with the target (phone number or IP address).
        """
        self.target = target
        self.target_type = None  # 'phone' or 'ip'
        self.parsed_number = None  # For phone numbers
        self.results = {
            "basic_info": {},
            "carrier_info": {},
            "geolocation": {},
            "ip_info": {},  # Added for IP address information
        }
        self.is_valid = False

    def validate_target(self):
        """
        Validates the target (phone number or IP address) and sets the target type.
        """
        try:
            # Attempt to parse as a phone number first
            self.parsed_number = phonenumbers.parse(self.target, None)
            if phonenumbers.is_valid_number(self.parsed_number):
                self.target_type = "phone"
                self.is_valid = True
                return
        except phonenumbers.phonenumberutil.NumberParseException:
            pass  # Not a valid phone number

        try:
            # Attempt to parse as an IP address
            ipaddress.ip_address(self.target)
            self.target_type = "ip"
            self.is_valid = True
            return
        except ValueError:
            pass  # Not a valid IP address

        self.is_valid = False
        return

    def get_basic_info(self):
        """
        Retrieves basic information about the phone number.
        """
        if self.target_type == "phone" and self.parsed_number:
            self.results["basic_info"] = {
                "international_format": phonenumbers.format_number(
                    self.parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                ),
                "national_format": phonenumbers.format_number(
                    self.parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL
                ),
                "country_code": self.parsed_number.country_code,
                "country": geocoder.description_for_number(self.parsed_number, "en"),
                "timezone": timezone.time_zones_for_number(self.parsed_number),
                "is_possible": phonenumbers.is_possible_number(self.parsed_number),
                "is_valid": phonenumbers.is_valid_number(self.parsed_number),
            }
        elif self.target_type == "ip":
            self.results["basic_info"] = {
                "ip_address": self.target,
            }

    def get_carrier_info(self):
        """
        Retrieves carrier information for the phone number.
        """
        if self.target_type == "phone" and self.parsed_number:
            carrier_name = carrier.name_for_number(self.parsed_number, "en")
            self.results["carrier_info"] = {
                "carrier": carrier_name if carrier_name else "Unknown"
            }

    def get_geolocation(self):
        """
        Retrieves geolocation information using the Nominatim API for both phone numbers and IP addresses.
        """
        if self.target_type == "phone" and self.parsed_number:
            target_for_api = self.target
            region = geocoder.description_for_number(self.parsed_number, "en")
        elif self.target_type == "ip":
            target_for_api = self.target
            region = None

        latitude, longitude = None, None
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={target_for_api}&format=json&limit=1"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data:
                latitude = data[0].get("lat")
                longitude = data[0].get("lon")
        except requests.exceptions.RequestException as e:
            print(f"Geolocation API error: {e}")
        
        self.results["geolocation"] = {
                "region": region,
                "latitude": latitude,
                "longitude": longitude,
                "map_url": f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}" if latitude and longitude else None
            }

    def get_ip_info(self):
        """Retrieves IP address information using ipinfo.io."""
        if self.target_type == "ip":
            try:
                url = f"https://ipinfo.io/{self.target}/json"
                if IPINFO_API_KEY:
                    url += f"?token={IPINFO_API_KEY}"  # Include API key if available
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                self.results["ip_info"] = {
                    "ip": data.get("ip"),
                    "hostname": data.get("hostname"),
                    "city": data.get("city"),
                    "region": data.get("region"),
                    "country": data.get("country"),
                    "loc": data.get("loc"),  # Latitude and longitude
                    "org": data.get("org"),  # ISP
                    "postal": data.get("postal"),
                    "timezone": data.get("timezone"),
                }
            except requests.exceptions.RequestException as e:
                print(f"IPinfo.io API error: {e}")
                self.results["ip_info"] = {"error": "Failed to retrieve IP information"}

    def generate_report(self, output_format="text"):
        """Generates a report in the specified format."""
        if output_format == "json":
            return json.dumps(self.results, indent=2)
        else:
            report = []
            report.append(f"\n{'=' * 50}")
            report.append(f"PhoneQ Report for: {self.target} ({self.target_type.upper()})")
            report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"{'=' * 50}\n")

            for section, data in self.results.items():
                if data:
                    report.append(f"[+] {section.replace('_', ' ').title()}:")
                    for key, value in data.items():
                        report.append(f"  {key.replace('_', ' ').title()}: {value}")
                    report.append("")

            return "\n".join(report)

    def run_all_checks(self):
        """Runs all checks on the target (phone number or IP address)."""
        if not self.validate_target():
            print(f"[-] Invalid target: {self.target}")
            return False

        print(f"[*] Analyzing {self.target_type}: {self.target}")

        self.get_basic_info()
        self.get_carrier_info()  # Only for phone numbers
        self.get_geolocation()
        if self.target_type == "ip":
            self.get_ip_info()  # Only for IP addresses
        return True


def print_banner():
    """Prints the tool banner."""
    print(TOOL_NAME)
    print(f"Version: {VERSION}")
    print(f"Author: {AUTHOR}")
    print(f"Description: {DESCRIPTION}")
    print("-" * 50)


def main():
    """Main function."""
    print_banner()

    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("target", help="Phone number or IP address to investigate")
    parser.add_argument(
        "-o",
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("-f", "--file", help="Save output to file")
    args = parser.parse_args()

    pq = PhoneQ(args.target)

    if not pq.run_all_checks():
        sys.exit(1)

    report = pq.generate_report(args.output)

    if args.file:
        with open(args.file, "w") as f:
            f.write(report)
        print(f"[+] Report saved to: {args.file}")
    else:
        print(report)


if __name__ == "__main__":
    main()
