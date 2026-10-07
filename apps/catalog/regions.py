"""
The browsing region a country falls in by default, keyed by ISO 3166-1 alpha-2
code. Used only to suggest a region when a destination is created for a
country the catalogue has not seen before; editors can change it on the
destination form, and the seeded countries keep the regions they were given.

East Africa is split from the rest of Africa because the site sells it as its
own product line (Kenya · Tanzania · Uganda · Rwanda safaris).
"""

_GROUPS = {
    'east-africa': 'KE TZ UG RW BI SS ET SO DJ ER',
    'africa': (
        'DZ AO BJ BW BF CM CV CF TD KM CG CD CI EG GQ GA GM GH GN GW LS LR LY MG MW ML MR MU YT MA MZ '
        'NA NE NG RE SH ST SN SC SL ZA SD SZ TG TN EH ZM ZW'
    ),
    'europe': (
        'AD AL AT AX BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GG GI GR HR HU IE IM IS IT JE LI LT LU '
        'LV MC MD ME MK MT NL NO PL PT RO RS RU SE SI SJ SK SM UA VA'
    ),
    'middle-east': 'AE BH IL IQ IR JO KW LB OM PS QA SA SY TR YE',
    'asia': (
        'AF AM AZ BD BN BT CC CN CX GE HK ID IN IO JP KG KH KP KR KZ LA LK MM MN MO MV MY NP PH PK SG TH '
        'TJ TL TM TW UZ VN'
    ),
    'oceania': 'AS AU CK FJ FM GU HM KI MH MP NC NF NR NU NZ PF PG PN PW SB TK TO TV UM VU WF WS',
    'americas': (
        'AG AI AR AW BB BL BM BO BQ BR BS BV BZ CA CL CO CR CU CW DM DO EC FK GD GF GL GP GS GT GY HN HT '
        'JM KN KY LC MF MQ MS MX NI PA PE PM PR PY SR SV SX TC TT US UY VC VE VG VI'
    ),
}

REGION_BY_CODE = {code: region for region, codes in _GROUPS.items() for code in codes.split()}


def default_region(code: str) -> str:
    return REGION_BY_CODE.get(code.upper(), 'other')
