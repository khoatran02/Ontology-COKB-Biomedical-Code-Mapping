from urllib.parse import quote

BASE_RESOURCE = "https://w3id.org/vn-ts-cokb/resource"


def resource_uri(kind: str, *parts: str) -> str:
    encoded = "/".join(quote(str(part), safe="") for part in parts)
    return f"{BASE_RESOURCE}/{kind}/{encoded}"
