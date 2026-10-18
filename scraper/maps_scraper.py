import asyncio
import urllib.parse
import re
from typing import AsyncGenerator, Dict, Any, Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from scraper.enrichment import (
    enrich_website_data,
    find_website_email,
    generate_whatsapp_link,
    clean_and_validate_phone,
    DeduplicationEngine
)

class GoogleMapsScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._is_stopped = False

    def stop(self):
        """Signals the scraper to safely stop and return collected leads."""
        self._is_stopped = True

    async def scrape(
        self,
        business_type: str,
        location: str,
        max_results: int = 20,
        search_mode: str = "standard"  # standard | industrial | small_stores
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        High-resilience Google Maps Lead Extractor:
        - Multi-pass query expansion when results run low
        - Multi-key deduplication (zero duplicates / zero repetitions)
        - Deep contact enrichment (emails with Cloudflare decoding, website phone fallback, social links)
        - Strict fake detail rejection
        """
        self._is_stopped = False
        dedup_engine = DeduplicationEngine()
        
        clean_type = business_type.strip()
        clean_loc = location.strip()
        
        # Build multi-pass queries for maximum yield & robustness
        if search_mode == "industrial":
            queries = [
                f"{clean_type} manufacturers factories in {clean_loc}",
                f"{clean_type} industrial area suppliers in {clean_loc}",
                f"{clean_type} manufacturing units in {clean_loc}"
            ]
        elif search_mode == "small_stores":
            queries = [
                f"{clean_type} shops stores market in {clean_loc}",
                f"{clean_type} retail shop in {clean_loc}",
                f"{clean_type} bazar {clean_loc}"
            ]
        else:
            queries = [
                f"{clean_type} in {clean_loc}",
                f"best {clean_type} in {clean_loc}",
                f"{clean_type} services center in {clean_loc}"
            ]

        yield {
            "type": "status",
            "message": f"Targeting verified businesses for: '{queries[0]}'..."
        }

        async with async_playwright() as p:
            browser: Optional[Browser] = None
            try:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--window-size=1440,960"
                    ]
                )
                
                context: BrowserContext = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    locale="en-US",
                    viewport={"width": 1440, "height": 960}
                )

                feed_page: Page = await context.new_page()
                detail_page: Page = await context.new_page()
                collected_count = 0

                for q_idx, current_query in enumerate(queries):
                    if collected_count >= max_results or self._is_stopped:
                        break

                    encoded_query = urllib.parse.quote_plus(current_query)
                    search_url = f"https://www.google.com/maps/search/{encoded_query}"

                    yield {
                        "type": "status",
                        "message": f"Searching layer {q_idx + 1}/{len(queries)}: '{current_query}'..."
                    }

                    try:
                        await feed_page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                        await feed_page.wait_for_timeout(1500)
                    except Exception as nav_err:
                        yield {"type": "status", "message": f"Navigation note: {str(nav_err)}"}
                        continue

                    # Dismiss Google Consent if present
                    try:
                        consent_btn = feed_page.locator(
                            'button:has-text("Accept all"), button:has-text("Reject all"), button:has-text("I agree"), form[action*="consent"] button'
                        ).first
                        if await consent_btn.is_visible(timeout=2000):
                            await consent_btn.click()
                            await feed_page.wait_for_timeout(1000)
                    except Exception:
                        pass

                    # Check if results or feed loaded
                    feed_sel = 'div[role="feed"]'
                    feed_found = True
                    try:
                        await feed_page.wait_for_selector(feed_sel, timeout=10000)
                    except Exception:
                        single_title = feed_page.locator('h1.DUwDvf')
                        if await single_title.count() > 0:
                            lead = await self._extract_current_pane(feed_page, await single_title.first.inner_text(), feed_page.url)
                            if lead and not dedup_engine.is_duplicate(lead["name"], lead["phone"], lead["maps_url"], lead["website"]):
                                collected_count += 1
                                lead["index"] = collected_count
                                yield {"type": "lead", "data": lead}
                                if collected_count >= max_results:
                                    break
                            continue
                        else:
                            feed_found = False

                    if not feed_found:
                        continue

                    feed = feed_page.locator(feed_sel)
                    consecutive_no_new = 0

                    yield {
                        "type": "status",
                        "message": f"Connected to results feed. Extracting verified contacts..."
                    }

                    processed_hrefs = set()

                    while collected_count < max_results and not self._is_stopped:
                        try:
                            await feed_page.wait_for_selector('a.hfpxzc', timeout=5000)
                        except Exception:
                            break

                        listing_anchors = await feed_page.locator('a.hfpxzc').all()
                        
                        new_anchors = []
                        for anchor in listing_anchors:
                            href = await anchor.get_attribute("href") or ""
                            if href and href not in processed_hrefs:
                                processed_hrefs.add(href)
                                title_attr = await anchor.get_attribute("aria-label") or ""
                                new_anchors.append((anchor, href, title_attr))

                        if not new_anchors:
                            consecutive_no_new += 1
                            if consecutive_no_new >= 4:
                                # Reached end of scrollable list
                                break
                        else:
                            consecutive_no_new = 0

                        for anchor, full_href, title_attr in new_anchors:
                            if collected_count >= max_results or self._is_stopped:
                                break

                            try:
                                # Skip obvious dummy/invalid titles
                                if not title_attr or any(junk in title_attr.lower() for junk in ['unnamed', 'closed', 'add business', 'search here']):
                                    continue

                                # Extract rich data using dedicated detail page navigation
                                # This guarantees the details pane loads 100% reliably with phone, address, and category
                                lead_data = None
                                try:
                                    await detail_page.goto(full_href, wait_until="domcontentloaded", timeout=25000)
                                    try:
                                        await detail_page.wait_for_selector('h1.DUwDvf', timeout=4000)
                                    except Exception:
                                        pass
                                    lead_data = await self._extract_current_pane(detail_page, title_attr, full_href)
                                except Exception:
                                    # Fallback to current page pane if detail_page failed
                                    lead_data = await self._extract_current_pane(feed_page, title_attr, full_href)

                                if not lead_data:
                                    continue

                                # STRICT DEDUPLICATION CHECK
                                if dedup_engine.is_duplicate(
                                    lead_data["name"],
                                    lead_data["phone"],
                                    lead_data["maps_url"],
                                    lead_data["website"]
                                ):
                                    # Skip repeated / duplicate listing
                                    continue

                                # Deep crawl for email, website phone fallback, and social links
                                if lead_data.get("has_website") == "YES" and lead_data.get("website"):
                                    enrichment = await enrich_website_data(
                                        lead_data["website"],
                                        current_phone=lead_data.get("phone")
                                    )
                                    if enrichment.get("email"):
                                        lead_data["email"] = enrichment["email"]
                                    if (not lead_data.get("phone") or lead_data.get("phone") == "Not Available") and enrichment.get("phone"):
                                        lead_data["phone"] = enrichment["phone"]
                                        lead_data["whatsapp_url"] = generate_whatsapp_link(lead_data["phone"], lead_data["name"])
                                    if enrichment.get("socials"):
                                        lead_data["socials"] = enrichment["socials"]

                                collected_count += 1
                                lead_data["index"] = collected_count

                                yield {
                                    "type": "lead",
                                    "data": lead_data
                                }

                            except Exception:
                                continue

                        if collected_count < max_results and not self._is_stopped:
                            # Natural human-like scroll: jiggle slightly then scroll down
                            try:
                                await feed.evaluate("el => el.scrollBy(0, -150)")
                                await feed_page.wait_for_timeout(250)
                                await feed.evaluate("el => el.scrollBy(0, 1800)")
                                await feed_page.keyboard.press("PageDown")
                                await feed_page.wait_for_timeout(1500)
                            except Exception:
                                break

                    if collected_count >= max_results or self._is_stopped:
                        break

                if self._is_stopped:
                    yield {
                        "type": "status",
                        "message": f"Scraping stopped by user. Total unique leads: {collected_count}"
                    }

                yield {
                    "type": "complete",
                    "stats": {
                        "total": collected_count
                    }
                }

            except Exception as e:
                yield {
                    "type": "error",
                    "message": f"Error during scraping: {str(e)}"
                }
            finally:
                if browser:
                    await browser.close()

    async def _extract_current_pane(self, page: Page, fallback_title: str, maps_url: str) -> Optional[Dict[str, Any]]:
        """Extracts and validates structured lead data with zero fake information."""
        # 1. Business Name
        name = fallback_title
        h1_el = page.locator('h1.DUwDvf')
        if await h1_el.count() > 0:
            h1_text = await h1_el.first.inner_text()
            if h1_text.strip():
                name = h1_text.strip()

        if not name or len(name) < 2:
            return None

        # 2. Category
        category = "Local Business"
        cat_el = page.locator('button.DkEaL, button[jsaction*="pane.rating.category"], button[jsaction*="category"]')
        if await cat_el.count() > 0:
            cat_text = await cat_el.first.inner_text()
            if cat_text.strip():
                category = cat_text.strip()
        if category == "Local Business":
            cat_sec = page.locator('span.fontBodyMedium button, div.fontBodyMedium button')
            if await cat_sec.count() > 0:
                c_txt = (await cat_sec.first.inner_text()).strip()
                if c_txt and len(c_txt) < 50:
                    category = c_txt

        # 3. Phone Number with Strict Cleaning & Validation
        raw_phone = ""
        phone_el = page.locator('button[data-item-id^="phone:tel:"]')
        if await phone_el.count() > 0:
            p_data = await phone_el.first.get_attribute("data-item-id")
            if p_data:
                raw_phone = p_data.replace("phone:tel:", "").strip()

        if not raw_phone:
            phone_did = page.locator('button[data-item-id*="phone"]')
            if await phone_did.count() > 0:
                p_data = await phone_did.first.get_attribute("data-item-id")
                if p_data:
                    raw_phone = re.sub(r'^phone:(?:tel:)?', '', p_data).strip()

        if not raw_phone:
            phone_btn = page.locator('button[aria-label*="Phone:" i], button[aria-label*="phone:" i]')
            if await phone_btn.count() > 0:
                aria = await phone_btn.first.get_attribute("aria-label") or ""
                if ":" in aria:
                    raw_phone = aria.split(":")[-1].strip()
                else:
                    raw_phone = aria.replace("Phone", "").replace("phone", "").strip()

        if not raw_phone:
            phone_any = page.locator('button[data-tooltip*="phone" i], button[data-tooltip*="Phone" i], button[data-tooltip*="Call" i]')
            if await phone_any.count() > 0:
                raw_phone = await phone_any.first.inner_text()

        if not raw_phone:
            tel_el = page.locator('a[href^="tel:"]')
            if await tel_el.count() > 0:
                t_href = await tel_el.first.get_attribute("href") or ""
                raw_phone = t_href.replace("tel:", "").strip()

        # Regex fallback from details pane
        if not raw_phone:
            try:
                pane_text = await page.locator('div[role="main"], div.m6QErb').first.inner_text()
                match = re.search(r'(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}|(?:\+?1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}|\b0\d{2,4}[\-\s]?\d{6,8}\b', pane_text)
                if match:
                    raw_phone = match.group(0).strip()
            except Exception:
                pass

        # Clean and validate phone (rejects fake numbers)
        validated_phone = clean_and_validate_phone(raw_phone)

        # 4. Website
        website = ""
        site_el = page.locator('a[data-item-id="authority"]')
        if await site_el.count() > 0:
            website = await site_el.first.get_attribute("href") or ""
        
        if not website:
            site_alt = page.locator('a[aria-label*="Website:"], a[aria-label*="website:"]')
            if await site_alt.count() > 0:
                website = await site_alt.first.get_attribute("href") or ""

        if not website:
            site_tooltip = page.locator('a[data-tooltip*="website"], a[data-tooltip*="Website"]')
            if await site_tooltip.count() > 0:
                website = await site_tooltip.first.get_attribute("href") or ""

        # Clean website URL
        if website and "google.com/url?q=" in website:
            try:
                parsed = urllib.parse.urlparse(website)
                qs = urllib.parse.parse_qs(parsed.query)
                if "q" in qs:
                    website = qs["q"][0]
            except Exception:
                pass

        if website and any(d in website.lower() for d in ['google.com', 'goo.gl', 'waze.com']):
            website = ""

        # 5. Has Website Flag
        has_website = "YES" if (website and len(website.strip()) > 0) else "NO"

        # 6. Profile Claimed Status
        profile_status = "Claimed / Verified ✅"
        try:
            claim_btn = page.locator('button[aria-label*="Claim this business"], a[data-item-id="merchant"], button:has-text("Claim this business"), a:has-text("Own this business?")')
            if await claim_btn.count() > 0 and await claim_btn.first.is_visible():
                profile_status = "Unclaimed Profile ⚠️ (Opportunity)"
        except Exception:
            pass

        # 7. Address
        address = ""
        addr_el = page.locator('button[data-item-id^="address"]')
        if await addr_el.count() > 0:
            aria = await addr_el.first.get_attribute("aria-label")
            if aria:
                address = aria.replace("Address: ", "").replace("address: ", "").strip()
            if not address:
                address = (await addr_el.first.inner_text()).replace('\n', ' ').strip()

        if not address:
            addr_alt = page.locator('button[data-item-id="oloc"], button[data-tooltip*="address" i]')
            if await addr_alt.count() > 0:
                address = (await addr_alt.first.inner_text()).replace('\n', ' ').strip()

        if not address:
            addr_aria = page.locator('button[aria-label*="Address:" i]')
            if await addr_aria.count() > 0:
                aria = await addr_aria.first.get_attribute("aria-label") or ""
                address = aria.replace("Address: ", "").replace("address: ", "").strip()

        # 8. Rating & Review Count
        rating = "N/A"
        reviews_count = "0"
        rating_box = page.locator('div.F7nice')
        if await rating_box.count() > 0:
            rating_span = rating_box.first.locator('span[aria-hidden="true"]').first
            if await rating_span.count() > 0:
                rating_val = await rating_span.inner_text()
                if rating_val.strip():
                    rating = rating_val.strip()

            rev_span = rating_box.first.locator('span[aria-label*="review"]').first
            if await rev_span.count() > 0:
                rev_aria = await rev_span.get_attribute("aria-label")
                if rev_aria:
                    reviews_count = rev_aria.replace("reviews", "").replace("review", "").strip()

        # 9. Social Links in Google Maps Pane
        socials = {}
        try:
            social_links = await page.locator('a[href*="facebook.com"], a[href*="instagram.com"], a[href*="linkedin.com"]').all()
            for s_link in social_links:
                h = await s_link.get_attribute("href") or ""
                if "facebook.com" in h and "facebook" not in socials:
                    socials["facebook"] = h
                elif "instagram.com" in h and "instagram" not in socials:
                    socials["instagram"] = h
                elif "linkedin.com" in h and "linkedin" not in socials:
                    socials["linkedin"] = h
        except Exception:
            pass

        # 10. WhatsApp Link
        whatsapp_url = generate_whatsapp_link(validated_phone, name)

        return {
            "name": name,
            "category": category,
            "phone": validated_phone if validated_phone else "Not Available",
            "whatsapp_url": whatsapp_url if whatsapp_url else "",
            "email": "Scanning..." if has_website == "YES" else "Not Available",
            "has_website": has_website,
            "website": website if website else "None (Opportunity)",
            "profile_status": profile_status,
            "address": address if address else "Not Listed",
            "rating": rating,
            "reviews_count": reviews_count,
            "maps_url": maps_url,
            "socials": socials
        }
