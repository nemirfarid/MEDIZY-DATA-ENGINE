#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEDIZY / SANTÉ DZ — Parseur d'URLs Google Maps
==============================================
Extraction des coordonnées géographiques (latitude, longitude) depuis différents
formats de liens Google Maps (desktop, mobile, raccourcis, embeds).
"""

import logging
import re
import urllib.request
from typing import Optional, Tuple

logger = logging.getLogger("medizy.url_parser")


def extract_coordinates_from_url(url: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """
    Extrait automatiquement la latitude et la longitude à partir de divers formats d'URL Google Maps :
      1. @36.752887,3.058823,17z
      2. ?q=36.752887,3.058823 ou query=36.752887,3.058823
      3. ?ll=36.752887,3.058823
      4. /place/.../!3d36.752887!4d3.058823
      5. Redirection de lien court (maps.app.goo.gl ou goo.gl/maps)
    """
    if not url:
        return None, None

    url_str = str(url).strip()

    # Si c'est un lien raccourci, tenter de résoudre la redirection
    if "goo.gl" in url_str or "maps.app.goo.gl" in url_str:
        try:
            req = urllib.request.Request(url_str, headers={"User-Agent": "MedizyLinkResolver/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                url_str = resp.geturl()
        except Exception as e:
            logger.debug(f"Impossible de résoudre la redirection {url_str}: {e}")

    # Motif 1 : Format standard @lat,lon
    match_at = re.search(r"@([0-9\.\-]+),([0-9\.\-]+)", url_str)
    if match_at:
        try:
            lat = float(match_at.group(1))
            lon = float(match_at.group(2))
            if 18.0 <= lat <= 38.5 and -9.5 <= lon <= 13.0:
                return lat, lon
        except ValueError:
            pass

    # Motif 2 : Paramètre query ?q=lat,lon, ?q=loc:lat,lon ou query=lat,lon
    match_query = re.search(r"[?&](?:q|query|ll)=(?:loc:)?([0-9\.\-]+),([0-9\.\-]+)", url_str)
    if match_query:
        try:
            lat = float(match_query.group(1))
            lon = float(match_query.group(2))
            if 18.0 <= lat <= 38.5 and -9.5 <= lon <= 13.0:
                return lat, lon
        except ValueError:
            pass

    # Motif 3 : Protobuf embed !3dlat!4dlon
    match_proto = re.search(r"!3d([0-9\.\-]+)!4d([0-9\.\-]+)", url_str)
    if match_proto:
        try:
            lat = float(match_proto.group(1))
            lon = float(match_proto.group(2))
            if 18.0 <= lat <= 38.5 and -9.5 <= lon <= 13.0:
                return lat, lon
        except ValueError:
            pass

    return None, None
