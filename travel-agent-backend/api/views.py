import json
import os
import re
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST


@require_GET
def ping(request):
    """Return a lightweight response for frontend connectivity checks."""
    return JsonResponse({"message": "pong"})


@require_GET
def health(request):
    """Report API status and whether MongoDB can be reached."""
    try:
        database = connections["default"]
        database.ensure_connection()
        database.connection.admin.command("ping")
    except Exception:
        return JsonResponse(
            {"status": "error", "database": "disconnected"}, status=503
        )
    return JsonResponse({"status": "ok", "database": "connected"})


def _movement_code(movement):
    movement = movement or {}
    return movement.get("iata") or movement.get("iataCode") or movement.get("icao") or movement.get("icaoCode") or ""


def _movement_name(movement):
    movement = movement or {}
    airport = movement.get("airport")
    if isinstance(airport, dict):
        airport = airport.get("name")
    return airport or movement.get("airportName") or _movement_code(movement)


def _movement_time(movement):
    movement = movement or {}
    return (
        movement.get("actual")
        or movement.get("estimated")
        or movement.get("scheduled")
        or movement.get("scheduledTime")
        or "Time unavailable"
    )


def _flight_payload(flight):
    departure = flight.get("departure") or {}
    arrival = flight.get("arrival") or {}
    airline = flight.get("airline") or {}
    flight_info = flight.get("flight") or {}
    return {
        "airline": airline.get("name") or airline.get("iataCode") or airline.get("iata") or "Airline unavailable",
        "flightNumber": flight_info.get("iata") or flight_info.get("iataNumber") or flight_info.get("number") or "Unknown",
        "departureCode": _movement_code(departure),
        "departure": _movement_name(departure) or "Departure airport",
        "arrivalCode": _movement_code(arrival),
        "arrival": _movement_name(arrival) or "Arrival airport",
        "departureTime": _movement_time(departure),
        "arrivalTime": _movement_time(arrival),
        "confirmation": "Live flight tracking",
        "status": str(flight.get("flight_status") or "Scheduled"),
    }


def _aviationstack_error(payload, http_status=None):
    error = (payload or {}).get("error") or {}
    error_code = error.get("code")
    error_type = str(error.get("type") or "").lower()

    if error_type in {"invalid_access_key", "missing_access_key", "inactive_user"} or error_code in (101, 102):
        return JsonResponse(
            {"error": "Aviationstack rejected the API key. Check AVIATIONSTACK_API_KEY in the backend .env file."},
            status=502,
        )
    if error_type in {"function_access_restricted", "api_feature_restricted"} or error_code == 105:
        return JsonResponse(
            {"error": "Your Aviationstack plan does not include this flight date lookup. The Free plan supports real-time flights; future schedules require a paid plan."},
            status=403,
        )
    if error_type in {"usage_limit_reached", "monthly_limit_reached", "rate_limit_reached"} or error_code in (104, 106):
        return JsonResponse(
            {"error": "Aviationstack request limit reached. Check your monthly quota and try again after it resets."},
            status=429,
        )
    if http_status == 429:
        return JsonResponse({"error": "Aviationstack is rate limiting requests. Try again shortly."}, status=429)
    return JsonResponse(
        {"error": "Aviationstack could not complete the flight lookup. Check the provider response in the account dashboard."},
        status=502,
    )


def _aviationstack_get(endpoint, params):
    api_key = os.getenv("AVIATIONSTACK_API_KEY", "").strip()
    if not api_key:
        return None, JsonResponse(
            {"error": "Flight lookup is not configured. Set AVIATIONSTACK_API_KEY in travel-agent-backend/.env."},
            status=503,
        )

    query = urlencode({**params, "access_key": api_key})
    request = Request(
        f"https://api.aviationstack.com/v1/{endpoint}?{query}",
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            payload = json.loads(error.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        return None, _aviationstack_error(payload, error.code)
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "Could not reach Aviationstack. Check the backend network connection."}, status=502)

    if payload.get("error"):
        return None, _aviationstack_error(payload)
    return payload.get("data") or [], None


@require_POST
def flight_lookup(request):
    """Find a flight by flight number or by an airport pair and local date."""
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Request body must be a JSON object."}, status=400)

    flight_number = str(data.get("flightNumber") or "").strip().upper()
    origin = str(data.get("departure") or "").strip().upper()
    destination = str(data.get("arrival") or "").strip().upper()
    flight_date = str(data.get("date") or "").strip()
    if not flight_date:
        return JsonResponse({"error": "Enter the flight date."}, status=400)
    try:
        date.fromisoformat(flight_date)
    except ValueError:
        return JsonResponse({"error": "Enter a valid date in YYYY-MM-DD format."}, status=400)

    if flight_number and len(flight_number.replace(" ", "")) > 10:
        return JsonResponse({"error": "Flight number must be 10 characters or fewer."}, status=400)
    if not flight_number and (not origin or not destination):
        return JsonResponse({"error": "Enter a flight number, or both departure and arrival airport codes."}, status=400)
    if (origin and len(origin) not in (3, 4)) or (destination and len(destination) not in (3, 4)):
        return JsonResponse({"error": "Use 3-letter IATA or 4-letter ICAO airport codes, such as JFK and LHR."}, status=400)

    # Aviationstack's /flights endpoint is for live flights and history; future
    # schedules use /flightsFuture and require a departure airport code.
    if flight_date > date.today().isoformat():
        if not origin:
            return JsonResponse({"error": "Future flight searches need the departure airport code as well as the flight number."}, status=400)
        params = {"iataCode": origin, "type": "departure", "date": flight_date}
        compact_number = "".join(flight_number.split())
        if compact_number:
            number_parts = re.fullmatch(r"([A-Z0-9]{2,3}?)(\d+[A-Z]?)", compact_number)
            if number_parts:
                airline_code, number = number_parts.groups()
                airline_field = "airline_iata" if len(airline_code) == 2 else "airline_icao"
                params.update({airline_field: airline_code, "flight_number": number})
            else:
                params["flight_number"] = compact_number
        flights, error = _aviationstack_get("flightsFuture", params)
        if error is None and destination:
            flights = [
                flight for flight in flights
                if _movement_code(flight.get("arrival", {})).upper() == destination
            ]
    else:
        params = {"limit": 100}
        if flight_number:
            params["flight_iata"] = "".join(flight_number.split())
        if origin:
            params["dep_iata"] = origin
        if destination:
            params["arr_iata"] = destination
        if flight_date < date.today().isoformat():
            params["flight_date"] = flight_date
        flights, error = _aviationstack_get("flights", params)

    if error:
        return error
    results = [_flight_payload(flight) for flight in (flights or [])]
    if not results:
        return JsonResponse({"flights": [], "message": "No matching flight was found for that date. On the Free plan, live flight data is available on the day of travel; future and historical schedule lookups require a paid plan."})
    return JsonResponse({"flights": results})
