"""
Scrapes only the most recent FIFA men's ranking snapshot and saves it to
data/raw/fifa_rankings/scraped_data/.

Run: python3 src/scrape_latest_rankings.py

Reuses the same Selenium approach as notebooks/01_FIFA_Rankings_Data_Acquisition_Preparation.ipynb.
"""

import json
import time
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
SCRAPED_DIR = ROOT / "data" / "raw" / "fifa_rankings" / "scraped_data"
HOME_PAGE = "https://www.fifa.com/fifa-world-ranking/ranking-table/men/"
BASE_URL = "https://inside.fifa.com/fifa-world-ranking/men"
WAIT = 15


def make_driver() -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("ignore-certificate-errors")
    return webdriver.Chrome(options=opts)


def get_latest_date_row(driver) -> dict:
    """Load the FIFA rankings homepage and return the most recent date entry."""
    driver.get(HOME_PAGE)
    driver.implicitly_wait(WAIT)
    try:
        driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
    except Exception:
        pass

    next_data = json.loads(
        driver.find_element(By.ID, "__NEXT_DATA__").get_attribute("textContent")
    )
    ranking = next_data["props"]["pageProps"]["pageData"]["ranking"]

    rows = []
    for year_block in ranking["dates"]:
        year = int(year_block["year"])
        for d in year_block["dates"]:
            rows.append({
                "year": year,
                "date_label": d.get("dateText", ""),
                "date_id": d["id"],
                "iso": d.get("iso"),
                "match_window_end_date": d.get("matchWindowEndDate"),
                "url": f"{BASE_URL}?{urlencode({'dateId': d['id'], 'gender': 'men'})}",
            })

    df = pd.DataFrame(rows).sort_values(["year", "iso"], ascending=[False, False])
    latest = df.iloc[0].to_dict()
    print(f"Most recent ranking on FIFA.com: {latest['date_label']} {latest['year']}  "
          f"(match_window_end_date={latest['match_window_end_date']})")
    return latest


def scrape_ranking_page(driver, url: str, snapshot_date: str) -> pd.DataFrame:
    """Scrape a single FIFA ranking page and return a DataFrame."""
    driver.get(url)
    driver.implicitly_wait(WAIT)
    try:
        driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
    except Exception:
        pass

    try:
        show_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Show full rankings']"))
        )
        driver.execute_script("arguments[0].click();", show_btn)
        time.sleep(1.5)
    except TimeoutException:
        pass

    WebDriverWait(driver, WAIT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr"))
    )

    rows = []
    for elem in driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr"):
        try:
            rank = elem.find_element(
                By.CSS_SELECTOR, "h3.custom-rank-cell_rankNumber__RORLl"
            ).text.strip()
            points = elem.find_element(
                By.CSS_SELECTOR, "h4.custom-points-cell_points__Lt6_7 span"
            ).text.strip().replace(",", "")
            try:
                country = elem.find_element(
                    By.CSS_SELECTOR, "a.custom-team-cell_teamName__c_tEs"
                ).text.strip()
            except Exception:
                country = elem.find_element(
                    By.CSS_SELECTOR, "td.scrollable-column img"
                ).get_attribute("alt").strip()
            if rank and country and points:
                rows.append({"rank": rank, "country": country, "points": points,
                              "date": snapshot_date})
        except Exception:
            continue

    return pd.DataFrame(rows)


def main():
    driver = make_driver()
    try:
        latest = get_latest_date_row(driver)

        snapshot_date = latest["match_window_end_date"]
        date_label = latest["date_label"].replace(" ", "_").replace(",", "")
        year = latest["year"]
        out_path = SCRAPED_DIR / f"Rankings_{year}_{date_label}.csv"

        if out_path.exists():
            print(f"Already exists: {out_path}")
            print("Delete it first if you want to re-scrape.")
            return

        print(f"Scraping {latest['url']} ...")
        df = scrape_ranking_page(driver, latest["url"], snapshot_date)

        if df.empty:
            print("ERROR: scraped 0 rows. Check CSS selectors or page load.")
            return

        df.to_csv(out_path, index=False)
        print(f"Saved {len(df)} teams → {out_path}")

        # Quick sanity check
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
        top5 = df.nsmallest(5, "rank")[["rank", "country", "points", "date"]]
        print("\nTop 5:")
        print(top5.to_string(index=False))

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
