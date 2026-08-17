import time
from typing import Dict, Set

# In-memory tracking: {user_id: {ip_address: last_seen_timestamp}}
ACTIVE_USER_IPS: Dict[str, Dict[str, float]] = {}
IP_TIMEOUT_SECONDS = 60

def extract_real_ip(headers: dict, fallback_client_ip: str) -> str:
    # Check Cloudflare real client IP header
    cf_ip = headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    
    # Check X-Forwarded-For
    xff = headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    
    return fallback_client_ip

def check_and_track_connection(user_id: str, client_ip: str, max_concurrent: int) -> bool:
    if max_concurrent <= 0:
        return True  # Unlimited

    current_time = time.time()
    user_sessions = ACTIVE_USER_IPS.setdefault(user_id, {})
    
    # Purge stale sessions
    stale_ips = [ip for ip, last_seen in user_sessions.items() if current_time - last_seen > IP_TIMEOUT_SECONDS]
    for ip in stale_ips:
        del user_sessions[ip]
    
    # Check active distinct IPs count
    if client_ip not in user_sessions and len(user_sessions) >= max_concurrent:
        return False  # Max concurrent distinct IPs exceeded
    
    # Refresh active timestamp
    user_sessions[client_ip] = current_time
    return True
