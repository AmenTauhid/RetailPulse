"""Generate synthetic local events for Canadian cities."""

import random
from datetime import date, timedelta

from data.scripts.db.models import Event

# Recurring event templates per city
EVENT_TEMPLATES: list[dict] = [
    # Toronto
    {
        "name": "Toronto Raptors vs {opponent}",
        "event_type": "sports",
        "city": "Toronto",
        "venue": "Scotiabank Arena",
        "attendance_range": (18000, 20000),
        "season": "nba",
    },
    {
        "name": "Toronto Maple Leafs vs {opponent}",
        "event_type": "sports",
        "city": "Toronto",
        "venue": "Scotiabank Arena",
        "attendance_range": (18500, 19800),
        "season": "nhl",
    },
    {
        "name": "Toronto FC vs {opponent}",
        "event_type": "sports",
        "city": "Toronto",
        "venue": "BMO Field",
        "attendance_range": (15000, 28000),
        "season": "mls",
    },
    {
        "name": "Caribbean Carnival Parade",
        "event_type": "festival",
        "city": "Toronto",
        "venue": "Lakeshore Blvd",
        "attendance_range": (100000, 200000),
        "season": "summer_fest",
    },
    {
        "name": "Canadian National Exhibition",
        "event_type": "festival",
        "city": "Toronto",
        "venue": "Exhibition Place",
        "attendance_range": (50000, 80000),
        "season": "cne",
    },
    {
        "name": "Toronto Christmas Market",
        "event_type": "festival",
        "city": "Toronto",
        "venue": "Distillery District",
        "attendance_range": (15000, 30000),
        "season": "xmas_market",
    },
    # Vancouver
    {
        "name": "Vancouver Canucks vs {opponent}",
        "event_type": "sports",
        "city": "Vancouver",
        "venue": "Rogers Arena",
        "attendance_range": (17500, 18900),
        "season": "nhl",
    },
    {
        "name": "Celebration of Light Fireworks",
        "event_type": "festival",
        "city": "Vancouver",
        "venue": "English Bay",
        "attendance_range": (200000, 400000),
        "season": "summer_fest",
    },
    {
        "name": "Vancouver Folk Music Festival",
        "event_type": "concert",
        "city": "Vancouver",
        "venue": "Jericho Beach Park",
        "attendance_range": (10000, 15000),
        "season": "summer_fest",
    },
    # Calgary
    {
        "name": "Calgary Flames vs {opponent}",
        "event_type": "sports",
        "city": "Calgary",
        "venue": "Scotiabank Saddledome",
        "attendance_range": (17000, 19300),
        "season": "nhl",
    },
    {
        "name": "Calgary Stampede",
        "event_type": "festival",
        "city": "Calgary",
        "venue": "Stampede Park",
        "attendance_range": (80000, 150000),
        "season": "stampede",
    },
    {
        "name": "Calgary Folk Music Festival",
        "event_type": "concert",
        "city": "Calgary",
        "venue": "Prince's Island Park",
        "attendance_range": (8000, 14000),
        "season": "summer_fest",
    },
    # Montreal
    {
        "name": "Montreal Canadiens vs {opponent}",
        "event_type": "sports",
        "city": "Montreal",
        "venue": "Bell Centre",
        "attendance_range": (20000, 21300),
        "season": "nhl",
    },
    {
        "name": "Montreal Jazz Festival",
        "event_type": "concert",
        "city": "Montreal",
        "venue": "Place des Arts",
        "attendance_range": (50000, 100000),
        "season": "summer_fest",
    },
    {
        "name": "Just for Laughs Festival",
        "event_type": "festival",
        "city": "Montreal",
        "venue": "Various Venues",
        "attendance_range": (20000, 50000),
        "season": "summer_fest",
    },
    {
        "name": "Igloofest Electronic Music",
        "event_type": "concert",
        "city": "Montreal",
        "venue": "Old Port",
        "attendance_range": (8000, 15000),
        "season": "winter_fest",
    },
    # Ottawa
    {
        "name": "Ottawa Senators vs {opponent}",
        "event_type": "sports",
        "city": "Ottawa",
        "venue": "Canadian Tire Centre",
        "attendance_range": (15000, 18600),
        "season": "nhl",
    },
    {
        "name": "Winterlude Festival",
        "event_type": "festival",
        "city": "Ottawa",
        "venue": "Rideau Canal",
        "attendance_range": (30000, 60000),
        "season": "winter_fest",
    },
    {
        "name": "Ottawa Bluesfest",
        "event_type": "concert",
        "city": "Ottawa",
        "venue": "LeBreton Flats",
        "attendance_range": (15000, 30000),
        "season": "summer_fest",
    },
]

NHL_OPPONENTS = [
    "Bruins",
    "Rangers",
    "Penguins",
    "Lightning",
    "Panthers",
    "Capitals",
    "Devils",
    "Islanders",
    "Red Wings",
    "Sabres",
    "Hurricanes",
    "Blue Jackets",
]
NBA_OPPONENTS = [
    "Celtics",
    "76ers",
    "Knicks",
    "Bucks",
    "Heat",
    "Cavaliers",
    "Nets",
    "Hawks",
    "Bulls",
    "Pacers",
    "Magic",
    "Pistons",
]
MLS_OPPONENTS = [
    "CF Montreal",
    "Columbus Crew",
    "Inter Miami",
    "NYCFC",
    "Atlanta United",
    "Nashville SC",
    "Charlotte FC",
    "Chicago Fire",
    "New England Revolution",
]


def _generate_nhl_games(template: dict, year: int, rng: random.Random) -> list[dict]:
    """Generate ~41 home games per NHL team for a season (Oct-Apr)."""
    events = []
    season_start = date(year, 10, 5)
    season_end = date(year + 1, 4, 15)

    game_dates = []
    current = season_start
    while current <= season_end:
        if rng.random() < 41 / 190:  # ~41 home games in ~190 days
            game_dates.append(current)
        current += timedelta(days=1)

    for game_date in game_dates[:41]:
        opponent = rng.choice(NHL_OPPONENTS)
        events.append(
            {
                "name": template["name"].format(opponent=opponent),
                "event_type": template["event_type"],
                "city": template["city"],
                "venue": template["venue"],
                "start_date": game_date,
                "end_date": None,
                "estimated_attendance": rng.randint(*template["attendance_range"]),
                "source": "synthetic",
            }
        )
    return events


def _generate_nba_games(template: dict, year: int, rng: random.Random) -> list[dict]:
    """Generate ~41 home games for Raptors (Oct-Apr)."""
    events = []
    season_start = date(year, 10, 20)
    season_end = date(year + 1, 4, 10)

    game_dates = []
    current = season_start
    while current <= season_end:
        if rng.random() < 41 / 170:
            game_dates.append(current)
        current += timedelta(days=1)

    for game_date in game_dates[:41]:
        opponent = rng.choice(NBA_OPPONENTS)
        events.append(
            {
                "name": template["name"].format(opponent=opponent),
                "event_type": template["event_type"],
                "city": template["city"],
                "venue": template["venue"],
                "start_date": game_date,
                "end_date": None,
                "estimated_attendance": rng.randint(*template["attendance_range"]),
                "source": "synthetic",
            }
        )
    return events


def _generate_mls_games(template: dict, year: int, rng: random.Random) -> list[dict]:
    """Generate ~17 home games for TFC (Mar-Oct)."""
    events = []
    season_start = date(year, 3, 1)
    season_end = date(year, 10, 15)

    game_dates = []
    current = season_start
    while current <= season_end:
        if rng.random() < 17 / 225:
            game_dates.append(current)
        current += timedelta(days=1)

    for game_date in game_dates[:17]:
        opponent = rng.choice(MLS_OPPONENTS)
        events.append(
            {
                "name": template["name"].format(opponent=opponent),
                "event_type": template["event_type"],
                "city": template["city"],
                "venue": template["venue"],
                "start_date": game_date,
                "end_date": None,
                "estimated_attendance": rng.randint(*template["attendance_range"]),
                "source": "synthetic",
            }
        )
    return events


def _generate_festival(template: dict, year: int, rng: random.Random) -> list[dict]:
    """Generate a multi-day festival event."""
    season = template["season"]
    if season == "summer_fest":
        start = date(year, rng.randint(6, 8), rng.randint(1, 20))
        duration = rng.randint(3, 10)
    elif season == "cne":
        start = date(year, 8, 16)
        duration = 18
    elif season == "stampede":
        start = date(year, 7, rng.randint(4, 8))
        duration = 10
    elif season == "xmas_market":
        start = date(year, 11, rng.randint(15, 25))
        duration = rng.randint(25, 35)
    elif season == "winter_fest":
        start = date(year, rng.randint(1, 2), rng.randint(1, 15))
        duration = rng.randint(3, 14)
    else:
        return []

    return [
        {
            "name": template["name"],
            "event_type": template["event_type"],
            "city": template["city"],
            "venue": template["venue"],
            "start_date": start,
            "end_date": start + timedelta(days=duration),
            "estimated_attendance": rng.randint(*template["attendance_range"]),
            "source": "synthetic",
        }
    ]


def generate_events(start_date: date, end_date: date) -> list[Event]:
    """Generate synthetic events for all cities within the date range."""
    rng = random.Random(42)
    raw_events: list[dict] = []

    start_year = start_date.year
    end_year = end_date.year

    for template in EVENT_TEMPLATES:
        season = template["season"]
        for year in range(start_year, end_year + 1):
            if season == "nhl":
                raw_events.extend(_generate_nhl_games(template, year, rng))
            elif season == "nba":
                raw_events.extend(_generate_nba_games(template, year, rng))
            elif season == "mls":
                raw_events.extend(_generate_mls_games(template, year, rng))
            else:
                raw_events.extend(_generate_festival(template, year, rng))

    # Filter to date range
    events: list[Event] = []
    for e in raw_events:
        if e["start_date"] < start_date or e["start_date"] > end_date:
            continue
        events.append(
            Event(
                name=e["name"],
                event_type=e["event_type"],
                city=e["city"],
                venue=e["venue"],
                start_date=e["start_date"],
                end_date=e["end_date"],
                estimated_attendance=e["estimated_attendance"],
                source=e["source"],
            )
        )

    return events
