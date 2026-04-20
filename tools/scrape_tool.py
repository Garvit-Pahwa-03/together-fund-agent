import requests
from bs4 import BeautifulSoup
from crewai_tools import BaseTool, SerperDevTool
from tools.validator import url_is_reachable


class SmartScrapeTool(BaseTool):
    name: str = "smart_scrape_tool"
    description: str = (
        "Visits a startup website and extracts its content. "
        "Automatically falls back to web search if the URL is unreachable. "
        "Input format: 'StartupName | https://website.com'"
    )

    def _run(self, input_str: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        try:
            parts = str(input_str).split("|")
            startup_name = parts[0].strip() if parts else "Unknown"
            url = parts[1].strip() if len(parts) > 1 else ""
        except Exception:
            startup_name = str(input_str)
            url = ""

        if not url:
            return self._fallback_search(startup_name)

        reachable, reason = url_is_reachable(url)

        if not reachable:
            print(
                f"[SmartScrape] '{url}' not reachable "
                f"({reason}). Using search fallback."
            )
            return self._fallback_search(startup_name)

        try:
            response = requests.get(
                url, headers=headers, timeout=10
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(
                ["script", "style", "nav",
                 "footer", "header", "aside"]
            ):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            content = text[:3000]
            print(f"[SmartScrape] Scraped {url} ({len(content)} chars)")
            return content
        except Exception as e:
            print(f"[SmartScrape] Failed: {e}. Using search fallback.")
            return self._fallback_search(startup_name)

    def _fallback_search(self, startup_name: str) -> str:
        try:
            serper = SerperDevTool()
            query = (
                f"{startup_name} AI startup "
                f"founders product technology 2024"
            )
            result = serper.run(search_query=query)
            return f"[Web search fallback]\n{result}"
        except Exception as e:
            return f"Search fallback also failed: {str(e)}"