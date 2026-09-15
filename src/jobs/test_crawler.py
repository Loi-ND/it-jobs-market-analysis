import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import json
import time
from datetime import datetime
import os

BASE_URL = "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257"
AIRFLOW_HOME="sample"

def set_url(page: int):
    return f"https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257?sort=new&type_keyword=1&disable_auto_detect_type_keyword=1&page={page}&category_family=r257&saturday_status=0"

def create_driver():
    options = uc.ChromeOptions()

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # giảm khả năng Chrome crash trong container
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")

    driver = uc.Chrome(
        options=options,
        version_main=152,
        use_subprocess=False
    )

    return driver

def processing_job_item(job_item: WebElement, driver: uc.Chrome):
    time_published_txt = job_item.find_element(
        by=By.CSS_SELECTOR,
        value="div.icon > label"
    ).get_attribute("data-original-title")

    tag = job_item.find_element(
        by=By.CSS_SELECTOR,
        value="div.box-icon > div.tag"
    )
    tag_values = []

    for item in tag.find_elements(By.CSS_SELECTOR, "span"):
        value = (
            item.get_attribute("data-original-title")
            or item.get_attribute("textContent")
            or item.text
        ).strip()

        if value:
            tag_values.append(value)

    tag_txt = ", ".join(tag_values)

    next_button = job_item.find_element(
        by=By.CSS_SELECTOR,
        value="p.quick-view-job-detail"
    )

    time.sleep(0.5)
    box_view_job_detail = None

    while True:
        try:

            ActionChains(driver)\
                .move_to_element(next_button)\
                .click()\
                .perform()

            box_view_job_detail = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.box-view-job-detail")
                )
            )

            print("Đã lấy được box-view-job-detail")
            break

        except Exception as e:
            print(f"Không tìm thấy box-view-job-detail, retry...")


        time.sleep(1)
    contents = box_view_job_detail.find_elements(
        By.CSS_SELECTOR,
        "div.box-job-info > div.content-tab"
    )

    titles = [
        "Mô tả công việc",
        "Yêu cầu ứng viên",
        "Quyền lợi"
    ]

    job_description_txt = "\n\n".join(
        f"{title}:\n{content.text.strip()}"
        for title, content in zip(titles, contents[:3])
    )

    title_txt = box_view_job_detail.find_element(
        by=By.CSS_SELECTOR,
        value="div.box-header h2.title"
    ).text

    salary_txt = box_view_job_detail.find_elements(
        by=By.CSS_SELECTOR,
        value="div.box-info-header"
    )[0].find_element(
        by=By.CSS_SELECTOR,
        value="div.box-item-value"
    ).text

    company_txt = driver.find_element(
        by=By.CSS_SELECTOR,
        value="a.name"
    ).text

    created_date_txt = datetime.today().date().strftime("%Y-%m-%d")

    address_items = driver.find_elements(
        by=By.CSS_SELECTOR,
        value="div.box-address > div > div"
    )
    
    address_txt = " | ".join(item.text.strip() for item in address_items)

    link_description_txt = job_item.find_element(
        by=By.CSS_SELECTOR,
        value="div.title-block > div > h3.title > a"
    ).get_attribute("href")

    return {
        "created_date": created_date_txt,
        "job_title": title_txt,
        "company": company_txt,
        "salary": salary_txt,
        "address": address_txt,
        "link_description": link_description_txt,
        "tag": tag_txt,
        "job_description": job_description_txt,
        "time_published": time_published_txt
    }

def main():
    driver = create_driver()
    os.makedirs(
        AIRFLOW_HOME, 
        exist_ok=True
    )

    try:
        driver.get(f"{BASE_URL}?page=1")
        time.sleep(1)

        pagination = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.ID, "job-listing-paginate-text")
            )
        )

        pagination_text = pagination.text

        total_pages = int(
            pagination_text
            .split("/")[1]
            .strip()
            .split()[0]
        )

        print("Pagination:", pagination_text)
        print("Total pages:", total_pages)

    except Exception:
        driver.close()

    for page in range(1, total_pages + 1):
        result = []
        print()
        print("=" * 50)
        print(f"Processing page {page}/{total_pages}")
        print("=" * 50)

        
        url = set_url(page=page)
        print("URL:", url)
        driver.get(url)
        time.sleep(3)

        job_items = driver.find_elements(
            by=By.CSS_SELECTOR,
            value="div.job-item-search-result"
        )

        for i, job_item in enumerate(job_items):
            print(f"{page} - {i}")
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'start'});",
                job_item
            )
            result.append(
                processing_job_item(
                    job_item=job_item, 
                    driver=driver
                )
            )

        with open(f"{AIRFLOW_HOME}/res_{page}.json", "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=4)
        time.sleep(0.5)

        print("Current URL:", driver.current_url)
        print("Title:", driver.title)


        time.sleep(1)

    driver.close()
    print("\nDone.")

if __name__ == "__main__":
    main()