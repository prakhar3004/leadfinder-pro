import re
import urllib.parse
import urllib.request
import asyncio
import ssl
from typing import Optional, Set, List, Dict, Any

# Strict RFC email pattern
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b')

# Blacklisted dummy/fake domains and keywords
JUNK_EMAIL_DOMAINS = {
    'example.com', 'domain.com', 'test.com', 'sentry.io', 'wixpress.com',
    'wordpress.org', 'wordpress.com', 'cloudflare.com', 'w3.org', 'schema.org',
    'yourname.com', 'email.com', 'mysite.com', 'sample.com', 'godaddy.com',
    'hubspot.com', 'googleapis.com', 'gstatic.com', 'gravatar.com'
}

INVALID_EMAIL_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.woff', '.ico'
}

# Dummy phone sequences to reject
DUMMY_PHONES = {
    '1234567890', '0123456789', '9876543210', '0000000000',
    '1111111111', '2222222222', '3333333333', '4444444444',
    '5555555555', '6666666666', '7777777777', '8888888888',
    '9999999999', '123456789', '987654321'
}

def decode_cloudflare_email(cfemail: str) -> Optional[str]:
    """Decodes Cloudflare obfuscated email addresses (data-cfemail)."""
    try:
        r = int(cfemail[:2], 16)
        email = ''.join([chr(int(cfemail[i:i+2], 16) ^ r) for i in range(2, len(cfemail), 2)])
        if is_valid_email(email):
            return email.lower()
    except Exception:
        pass
    return None

def clean_and_validate_phone(raw_phone: str) -> Optional[str]:
    """
    Cleans raw phone string and rejects fake or dummy numbers.
    Returns cleaned readable phone string if valid, else None.
    """
    if not raw_phone or raw_phone in ("Not Available", "No Phone", "N/A"):
        return None

    # Strip everything except digits and leading +
    digits = re.sub(r'\D', '', raw_phone)
    if not digits:
        return None

    # Length checks
    if len(digits) < 8 or len(digits) > 15:
        return None

    # Check for repeating identical digits (e.g. 0000000000, 9999999999)
    if len(set(digits)) <= 2:
        return None

    # Check known dummy sequences
    if digits in DUMMY_PHONES:
        return None

    # If starts with 0 and length is 11, clean leading 0
    if len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    elif len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]

    # Format cleanly
    if len(digits) == 10 and digits[0] in '6789':
        # Indian mobile format (+91 XXXXX XXXXX)
        return f"+91 {digits[:5]} {digits[5:]}"
    elif len(digits) == 10:
        # US/General format (XXX) XXX-XXXX
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    return raw_phone.strip()

def is_valid_email(email: str) -> bool:
    """Verifies email is genuine and not a dummy/asset/framework email."""
    if not email or '@' not in email:
        return False

    clean = email.strip().lower()

    # Reject invalid file extensions
    if any(clean.endswith(ext) for ext in INVALID_EMAIL_EXTENSIONS):
        return False

    parts = clean.split('@')
    if len(parts) != 2:
        return False

    domain = parts[1]
    if domain in JUNK_EMAIL_DOMAINS:
        return False

    if any(junk in clean for junk in ['sentry', 'example', 'wixpress', 'webpack', 'polyfill', 'bootstrap']):
        return False

    # Check domain has dot and valid TLD
    if '.' not in domain or len(domain.split('.')[-1]) < 2:
        return False

    return True

def extract_phone_from_html(html: str) -> Optional[str]:
    """Scans website HTML for genuine contact numbers (tel: links and patterns)."""
    if not html:
        return None

    # 1. Look for href="tel:..." links first
    tel_links = re.findall(r'href=["\']tel:([^"\']+)["\']', html, re.I)
    for t in tel_links:
        cleaned = clean_and_validate_phone(t)
        if cleaned:
            return cleaned

    # 2. Look for Indian mobile or international numbers in text
    patterns = [
        r'(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}',
        r'\b[6-9]\d{9}\b',
        r'(?:\+?1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}'
    ]
    for p in patterns:
        matches = re.findall(p, html)
        for m in matches:
            cleaned = clean_and_validate_phone(m)
            if cleaned:
                return cleaned

    return None

def extract_social_links(html: str) -> Dict[str, str]:
    """Extracts social media profile links (Instagram, Facebook, LinkedIn) from HTML."""
    socials: Dict[str, str] = {}
    if not html:
        return socials

    # Facebook
    fb_match = re.search(r'https?://(?:www\.)?facebook\.com/([A-Za-z0-9._-]+)', html, re.I)
    if fb_match:
        page = fb_match.group(1).lower()
        if page not in ('sharer', 'share', 'policies', 'pages', 'groups', 'help', 'tr'):
            socials['facebook'] = f"https://facebook.com/{fb_match.group(1)}"

    # Instagram
    ig_match = re.search(r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9._-]+)', html, re.I)
    if ig_match:
        page = ig_match.group(1).lower()
        if page not in ('p', 'explore', 'reel', 'stories', 'legal', 'accounts', 'developer'):
            socials['instagram'] = f"https://instagram.com/{ig_match.group(1)}"

    # LinkedIn
    li_match = re.search(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/([A-Za-z0-9._-]+)', html, re.I)
    if li_match:
        socials['linkedin'] = li_match.group(0)

    return socials

async def enrich_website_data(website_url: str, current_phone: Optional[str] = None, timeout: float = 4.5) -> Dict[str, Any]:
    """
    Crawls website homepage and contact subpages in parallel.
    Extracts:
    - Verified contact email (with Cloudflare de-obfuscation)
    - Fallback phone number if current_phone is missing or invalid
    - Social profile links (Instagram, Facebook, LinkedIn)
    """
    result = {
        "email": None,
        "phone": None,
        "socials": {}
    }

    if not website_url or not website_url.startswith("http"):
        return result

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    def fetch_url_content(target_url: str) -> str:
        try:
            req = urllib.request.Request(target_url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_context, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return ""
                return response.read(400000).decode("utf-8", errors="ignore")
        except Exception:
            return ""

    loop = asyncio.get_running_loop()

    # 1. Fetch homepage
    home_html = await loop.run_in_executor(None, fetch_url_content, website_url)
    all_emails: Set[str] = set()

    def process_html(html: str):
        if not html:
            return
        
        # Cloudflare email decoding
        cf_matches = re.findall(r'data-cfemail=["\']([a-f0-9]+)["\']', html, re.I)
        for cf in cf_matches:
            dec = decode_cloudflare_email(cf)
            if dec:
                all_emails.add(dec)

        # Mailto links
        mailtos = re.findall(r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7})', html, re.I)
        for m in mailtos:
            if is_valid_email(m):
                all_emails.add(m.strip().lower())

        # Regex scan
        matches = EMAIL_REGEX.findall(html)
        for match in matches:
            if is_valid_email(match):
                all_emails.add(match.strip().lower())

        # Phone extraction if needed
        if not result["phone"] and (not current_phone or current_phone in ("Not Available", "No Phone")):
            found_ph = extract_phone_from_html(html)
            if found_ph:
                result["phone"] = found_ph

        # Social links
        soc = extract_social_links(html)
        for k, v in soc.items():
            if k not in result["socials"]:
                result["socials"][k] = v

    process_html(home_html)

    # 2. If no email or missing phone, crawl contact subpages in parallel
    if not all_emails or not result["phone"]:
        try:
            parsed = urllib.parse.urlparse(website_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            contact_paths = [
                f"{base}/contact", 
                f"{base}/contact-us", 
                f"{base}/about-us", 
                f"{base}/about",
                f"{base}/reach-us"
            ]
            
            sub_tasks = [loop.run_in_executor(None, fetch_url_content, cp) for cp in contact_paths]
            results = await asyncio.gather(*sub_tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, str) and res:
                    process_html(res)
                    if all_emails and result["phone"]:
                        break
        except Exception:
            pass

    # Pick best email
    if all_emails:
        priority_order = ["info@", "contact@", "sales@", "hello@", "support@", "care@", "dr", "office@"]
        chosen_email = None
        for prefix in priority_order:
            for em in all_emails:
                if em.startswith(prefix):
                    chosen_email = em
                    break
            if chosen_email:
                break
        result["email"] = chosen_email if chosen_email else next(iter(all_emails))

    return result

async def find_website_email(website_url: str, timeout: float = 4.0) -> Optional[str]:
    """Backwards compatible email scraper helper."""
    data = await enrich_website_data(website_url, timeout=timeout)
    return data.get("email")

def generate_whatsapp_link(clean_phone: Optional[str], business_name: str) -> Optional[str]:
    """Generates direct WhatsApp click-to-chat URL with pre-filled greeting."""
    if not clean_phone:
        return None

    digits = re.sub(r'\D', '', clean_phone)
    if not digits:
        return None

    # If Indian mobile 10 digits
    if len(digits) == 10 and digits[0] in '6789':
        num = f"91{digits}"
    elif len(digits) == 12 and digits.startswith('91'):
        num = digits
    elif len(digits) >= 10:
        num = digits
    else:
        return None

def extract_pincode(address: str, fallback: str = "") -> str:
    """
    Extracts 6-digit Indian PIN codes, US ZIP codes, UK postal codes, and Canadian postal codes
    from raw address strings or Google Maps detail panes.
    """
    if not address and not fallback:
        return ""
    text = f"{address} {fallback}".strip()
    if not text:
        return ""

    # 1. Indian 6-digit PIN code (e.g. 400050, 110001, 201301, 400 050)
    in_match = re.search(r'(?:pin(?:code)?[:\s\-]*)?\b([1-9][0-9]{2})\s?([0-9]{3})\b', text, re.IGNORECASE)
    if in_match:
        digits = in_match.group(1) + in_match.group(2)
        start = in_match.start()
        end = in_match.end()
        before_is_digit = start > 0 and text[start-1].isdigit()
        after_is_digit = end < len(text) and text[end].isdigit()
        if not before_is_digit and not after_is_digit:
            return digits

    # 2. UK Postal Code: e.g. SW1A 1AA, EC1A 1BB
    uk_match = re.search(r'\b([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})\b', text, re.IGNORECASE)
    if uk_match:
        return uk_match.group(1).upper()

    # 3. Canadian Postal Code: e.g. K1A 0B1
    ca_match = re.search(r'\b([A-Z][0-9][A-Z]\s?[0-9][A-Z][0-9])\b', text, re.IGNORECASE)
    if ca_match:
        return ca_match.group(1).upper()

    # 4. US Zip code: e.g. 90210 or 10001-1234
    us_match = re.search(r'\b([0-9]{5}(?:-[0-9]{4})?)\b', text)
    if us_match:
        return us_match.group(1)

    return ""

class DeduplicationEngine:
    """
    Multi-key strict deduplication engine preventing:
    1. Duplicate Place IDs
    2. Identical phone numbers across duplicate listings
    3. Identical normalized names + location
    4. Duplicate website domains
    """
    def __init__(self):
        self.seen_place_ids: Set[str] = set()
        self.seen_phones: Set[str] = set()
        self.seen_names_normalized: Set[str] = set()
        self.seen_domains: Set[str] = set()

    def is_duplicate(self, name: str, phone: Optional[str], maps_url: str, website: str) -> bool:
        # 1. Place ID / Maps Hex ID check
        place_id_match = re.search(r'0x[0-9a-fA-F]+:0x[0-9a-fA-F]+', maps_url)
        if place_id_match:
            pid = place_id_match.group(0).lower()
            if pid in self.seen_place_ids:
                return True
            self.seen_place_ids.add(pid)

        # 2. Strict Phone number deduplication
        if phone:
            digits = re.sub(r'\D', '', phone)
            if digits and len(digits) >= 10:
                core_digits = digits[-10:] # last 10 digits
                if core_digits in self.seen_phones:
                    return True
                self.seen_phones.add(core_digits)

        # 3. Normalized Name check
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
        if len(clean_name) >= 4:
            if clean_name in self.seen_names_normalized:
                return True
            self.seen_names_normalized.add(clean_name)

        # 4. Domain deduplication (for identical websites)
        if website and website.startswith("http") and not any(d in website for d in ['facebook.com', 'instagram.com', 'justdial.com']):
            try:
                domain = urllib.parse.urlparse(website).netloc.lower().replace('www.', '')
                if domain and domain in self.seen_domains:
                    return True
                if domain:
                    self.seen_domains.add(domain)
            except Exception:
                pass

        return False
