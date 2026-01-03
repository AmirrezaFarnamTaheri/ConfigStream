
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

# Mock Proxy class (simplified)
class Proxy(BaseModel):
    details: Dict[str, Any] = Field(default_factory=dict)
    country_code: str = ""
    country: str = ""
    config: str = ""
    protocol: str = ""
    address: str = ""
    port: int = 80

def reproduce():
    # Simulate the washer logic
    relay = Proxy(protocol="vmess", address="1.2.3.4", port=443, country_code="US", country="United States")
    origin_dict = relay.model_dump(mode="json")

    # Simulate the revived proxy
    p = Proxy(
        details={
            "origin_proxy": origin_dict
        }
    )

    # Simulate the consumer logic that fails
    try:
        origin = p.details.get("origin_proxy")
        if origin:
            print(f"Origin found: {type(origin)}")
            # This line should fail
            p.country_code = origin.country_code
            p.country = origin.country
            print("Successfully set country info")
    except AttributeError as e:
        print(f"Caught expected error: {e}")
    except Exception as e:
        print(f"Caught unexpected error: {e}")

if __name__ == "__main__":
    reproduce()
