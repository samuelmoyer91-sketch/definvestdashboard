"""IST demo content — all fictional, transcribed from 03_Fake-Org/ bibles."""

FOCUS_AREAS = [
    "Microelectronics",
    "Quantum computing",
    "Hypersonics",
    "Alt-PNT",
    "Biomanufacturing",
]

PEOPLE = {
    "leadership": [
        {
            "name": "Dr. Katherine Voss",
            "title": "President & Director",
            "image": "katherine-voss.png",
            "bio": "Former senior official in defense R&D; founded IST to connect frontier technology with national-security strategy.",
        }
    ],
    "fellows": [
        {
            "name": "Dr. Raymond Okafor",
            "title": "Senior Fellow",
            "area": "Microelectronics",
            "image": "raymond-okafor.png",
            "bio": "Expert on semiconductor supply chains and domestic fabrication capacity.",
        },
        {
            "name": "Dr. Priya Nair",
            "title": "Fellow",
            "area": "Quantum computing",
            "image": "priya-nair.png",
            "bio": "Leads research on quantum sensing and near-term quantum advantages for defense.",
        },
        {
            "name": "Dr. Marcus Feld",
            "title": "Senior Fellow",
            "area": "Hypersonics",
            "image": "marcus-feld.png",
            "bio": "Analyzes hypersonic technology development, testing, and operational concepts.",
        },
        {
            "name": "Dr. Sofia Reyes",
            "title": "Fellow",
            "area": "Alt-PNT",
            "image": "sofia-reyes.png",
            "bio": "Researches resilient positioning, navigation, and timing architectures.",
        },
        {
            "name": "Dr. Nathan Cole",
            "title": "Fellow",
            "area": "Biomanufacturing",
            "image": "nathan-cole.png",
            "bio": "Focuses on distributed bioproduction for defense and supply-chain resilience.",
        },
        {
            "name": "Dr. Alan Whitfield",
            "title": "Senior Fellow",
            "area": "Defense industrial base",
            "image": "alan-whitfield.png",
            "bio": "Cross-cutting expert on private-capital financing and industrial capacity.",
        },
    ],
    "visiting": [
        {
            "name": "Lt. Gen. (Ret.) David Hargrove",
            "title": "Visiting Military Fellow",
            "image": "david-hargrove.png",
            "bio": "Former combatant-command tech lead; brings operational perspective to emerging technologies.",
        },
        {
            "name": "Dr. Mei-Ling Chen",
            "title": "Visiting Scholar",
            "image": "mei-ling-chen.png",
            "bio": "University quantum-materials researcher; exploring academic partnerships.",
        },
        {
            "name": "Dr. Tomas Berg",
            "title": "Visiting Scholar",
            "image": "tomas-berg.png",
            "bio": "Former DARPA program manager; advises on technology transition and risk.",
        },
    ],
}

PUBLICATIONS = [
    {
        "title": "Securing the Chip Supply: A National Microelectronics Strategy",
        "type": "Report",
        "topic": "Microelectronics",
        "author": "Dr. Raymond Okafor",
        "date": "March 2026",
        "abstract": "Roadmap for resilient domestic semiconductor capacity.",
        "pdf": "securing-the-chip-supply.pdf",
    },
    {
        "title": "Advanced Packaging and the Next Chip War",
        "type": "Brief",
        "topic": "Microelectronics",
        "author": "Dr. Raymond Okafor",
        "date": "January 2026",
        "abstract": "Why packaging, not just fabrication, decides the edge.",
        "pdf": None,  # placeholder
    },
    {
        "title": "Quantum Sensing for Contested Environments",
        "type": "Report",
        "topic": "Quantum computing",
        "author": "Dr. Priya Nair",
        "date": "February 2026",
        "abstract": "Near-term military payoffs of quantum sensing.",
        "pdf": None,
    },
    {
        "title": "The Cryptographic Cliff: Preparing for Q-Day",
        "type": "Brief",
        "topic": "Quantum computing",
        "author": "Dr. Priya Nair",
        "date": "April 2026",
        "abstract": "Post-quantum migration timelines for DoD.",
        "pdf": None,
    },
    {
        "title": "Hypersonic Test Infrastructure: The Real Bottleneck",
        "type": "Report",
        "topic": "Hypersonics",
        "author": "Dr. Marcus Feld",
        "date": "December 2025",
        "abstract": "Ground/flight test capacity as the limiting factor.",
        "pdf": None,
    },
    {
        "title": "Closing the Hypersonics Gap",
        "type": "Insight",
        "topic": "Hypersonics",
        "author": "Dr. Marcus Feld",
        "date": "May 2026",
        "abstract": "Short take on production scale-up.",
        "pdf": None,
    },
    {
        "title": "Beyond GPS: Building Resilient Alt-PNT",
        "type": "Report",
        "topic": "Alt-PNT",
        "author": "Dr. Sofia Reyes",
        "date": "February 2026",
        "abstract": "A layered architecture for assured PNT.",
        "pdf": None,
    },
    {
        "title": "Jamming, Spoofing, and the Case for Alt-PNT",
        "type": "Insight",
        "topic": "Alt-PNT",
        "author": "Dr. Sofia Reyes",
        "date": "June 2026",
        "abstract": "Why GPS dependence is a strategic liability.",
        "pdf": None,
    },
    {
        "title": "Biomanufacturing for Defense Resilience",
        "type": "Report",
        "topic": "Biomanufacturing",
        "author": "Dr. Nathan Cole",
        "date": "January 2026",
        "abstract": "Distributed bioproduction for supply security.",
        "pdf": None,
    },
    {
        "title": "The Bioeconomy as a National Security Asset",
        "type": "Brief",
        "topic": "Biomanufacturing",
        "author": "Dr. Nathan Cole",
        "date": "March 2026",
        "abstract": "Framing biomanufacturing in strategic terms.",
        "pdf": None,
    },
    {
        "title": "Financing the Defense Tech Transition",
        "type": "Brief",
        "topic": "Microelectronics",  # cross-cutting; map to first area
        "author": "Dr. Alan Whitfield",
        "date": "April 2026",
        "abstract": "How private capital reaches the valley of death.",
        "pdf": None,
    },
    {
        "title": "Midmarket Defense: The Overlooked Engine",
        "type": "Insight",
        "topic": "Microelectronics",
        "author": "Dr. Alan Whitfield",
        "date": "June 2026",
        "abstract": "Why midmarket firms drive real innovation.",
        "pdf": None,
    },
]

SPONSORS = {
    "primes": [
        {"name": "Vantris Aerospace & Defense", "logo": None},
        {"name": "Corven Systems", "logo": None},
        {"name": "Halden Dynamics", "logo": None},
    ],
    "midmarket": [
        {"name": "Ridgecrest Microsystems", "focus_area": "Microelectronics", "logo": None},
        {"name": "Cobalt Semiconductor", "focus_area": "Microelectronics", "logo": None},
        {"name": "Lumary Photonics", "focus_area": "Quantum computing", "logo": None},
        {"name": "Ignis Hypersonics", "focus_area": "Hypersonics", "logo": None},
        {"name": "Northstar Navigation Systems", "focus_area": "Alt-PNT", "logo": None},
        {"name": "Verdant Biosystems", "focus_area": "Biomanufacturing", "logo": None},
    ],
}

TAGLINE = "Where government, industry, and capital shape the technologies that matter."

MISSION = (
    "The Institute for Strategic Technologies is an independent research institute "
    "advancing U.S. national security through rigorous analysis, high-level convening, "
    "and education across the critical and emerging technologies that will define the "
    "future of defense. IST bridges government, industry, and investors — turning "
    "technical insight into strategic advantage."
)
