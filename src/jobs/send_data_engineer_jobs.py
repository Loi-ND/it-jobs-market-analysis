import mysql.connector
from google import genai
from google.genai import types
from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed
from dotenv import load_dotenv
from io import BytesIO
from datetime import date, timedelta
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
import os


AIRFLOW_HOME=os.environ.get("AIRFLOW_HOME")
load_dotenv(os.path.join(
    AIRFLOW_HOME,
    "..",
    ".env"
))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
MODEL_API_KEY = os.environ.get("MODEL_API_KEY")
client = genai.Client(
    api_key=MODEL_API_KEY
)

processing_date = datetime.today().date().strftime(f"%Y-%m-%d")
prev_date = (datetime.today().date() - timedelta(days=1)).strftime(f"%Y-%m-%d")


def get_jobs(processing_date=None):
    if processing_date is None:
        processing_date = date.today()

    if isinstance(processing_date, str):
        processing_date = date.fromisoformat(processing_date)

    prev_date = processing_date - timedelta(days=1)

    conn = mysql.connector.connect(
        host="mysql",
        port=3306,
        user="mysql",
        password="mysql",
        database="jobs_db"
    )

    query_1 = """
        SELECT
            created_date,
            job_title,
            company,
            address,
            salary,
            link_description,
            city,
            district,
            min_salary,
            max_salary,
            salary_unit,
            tag,
            job_description,
            time_published
        FROM (
            SELECT
                j.*,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        j.job_title,
                        j.company,
                        j.address
                    ORDER BY j.created_date DESC
                ) AS rn
            FROM jobs AS j
            WHERE (
                FIND_IN_SET(
                    'Data Analyst',
                    REPLACE(j.tag, ', ', ',')
                ) > 0
                OR
                FIND_IN_SET(
                    'Data Engineer',
                    REPLACE(j.tag, ', ', ',')
                ) > 0
                OR
                FIND_IN_SET(
                    'Data Scientist',
                    REPLACE(j.tag, ', ', ',')
                ) > 0
            )
            AND j.time_published = 'Đăng hôm nay'
            AND DATE(j.created_date) = %s
        ) AS t
        WHERE rn = 1;
    """

    query_2 = """
        SELECT
            a.created_date,
            a.job_title,
            a.company,
            a.address,
            a.salary,
            a.link_description,
            a.city,
            a.district,
            a.min_salary,
            a.max_salary,
            a.salary_unit,
            a.tag,
            a.job_description,
            a.time_published
        FROM (
            SELECT
                j.*,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        j.job_title,
                        j.company,
                        j.address
                    ORDER BY j.created_date DESC
                ) AS rn
            FROM jobs AS j
            WHERE (
                FIND_IN_SET(
                    'Data Analyst',
                    REPLACE(j.tag, ', ', ',')
                ) > 0
                OR
                FIND_IN_SET(
                    'Data Engineer',
                    REPLACE(j.tag, ', ', ',')
                ) > 0
                OR
                FIND_IN_SET(
                    'Data Scientist',
                    REPLACE(j.tag, ', ', ',')
                ) > 0
            )
            AND j.time_published = 'Đăng 1 ngày trước'
            AND DATE(j.created_date) = %s
        ) AS a
        WHERE a.rn = 1
        AND NOT EXISTS (
            SELECT 1
            FROM jobs_sent AS b
            WHERE (
                FIND_IN_SET(
                    'Data Analyst',
                    REPLACE(b.tag, ', ', ',')
                ) > 0
                OR
                FIND_IN_SET(
                    'Data Engineer',
                    REPLACE(b.tag, ', ', ',')
                ) > 0
                OR
                FIND_IN_SET(
                    'Data Scientist',
                    REPLACE(b.tag, ', ', ',')
                ) > 0
            )
            AND b.time_published = 'Đăng hôm nay'
            AND DATE(b.created_date) = %s
            AND b.company = a.company
            AND b.job_title = a.job_title
        );
    """

    insert_query = """
        INSERT INTO jobs_sent (
            created_date,
            job_title,
            company,
            address,
            salary,
            link_description,
            city,
            district,
            min_salary,
            max_salary,
            salary_unit,
            tag,
            job_description,
            time_published
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        );
    """

    try:
        cursor = conn.cursor(dictionary=True)

        # Job đăng hôm nay
        cursor.execute(
            query_1,
            (processing_date,)
        )
        jobs_current_date = cursor.fetchall()

        # Job đăng 1 ngày trước nhưng chưa có trong jobs_sent
        cursor.execute(
            query_2,
            (
                processing_date,
                prev_date
            )
        )
        jobs_prev_date = cursor.fetchall()

        # Gộp hai danh sách
        jobs = jobs_current_date + jobs_prev_date

        # Chuẩn bị dữ liệu để INSERT
        values = [
            (
                job["created_date"],
                job["job_title"],
                job["company"],
                job["address"],
                job["salary"],
                job["link_description"],
                job["city"],
                job["district"],
                job["min_salary"],
                job["max_salary"],
                job["salary_unit"],
                job["tag"],
                job["job_description"],
                job["time_published"],
            )
            for job in jobs
        ]

        # INSERT vào jobs_sent
        if values:
            cursor.executemany(insert_query, values)
            conn.commit()

        cursor.close()

        return jobs

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def format_job(job, index):
    title = job.get("job_title") or "Không có tiêu đề"
    company = job.get("company") or "Không có thông tin"
    address = job.get("address") or "Không có thông tin"
    salary = job.get("salary") or "Thỏa thuận"
    url = job.get("link_description")
    job_description = job.get("job_description") or "Không có mô tả"

    prompt = f"""
Bạn là trợ lý AI chuyên tóm tắt tin tuyển dụng IT.

Hãy đọc nội dung tuyển dụng bên dưới và tóm tắt thành 4-5 ý chính,
giúp người đọc nhanh chóng hiểu công việc mà không cần đọc toàn bộ tin tuyển dụng.

YÊU CẦU:

1. Chỉ sử dụng thông tin thực sự xuất hiện trong nội dung tuyển dụng.
2. Không được tự suy đoán, bổ sung hoặc bịa thêm thông tin.
3. Không sao chép nguyên văn dài dòng. Hãy viết lại ngắn gọn.
4. Ưu tiên những thông tin quan trọng nhất đối với ứng viên.
5. Mỗi ý phải bắt đầu bằng một trong các nhãn:
   - "Trách nhiệm công việc:"
   - "Kỹ năng & chuyên môn:"
   - "Yêu cầu ứng viên:"
   - "Quyền lợi:"
   - "Thông tin khác:"
6. Chỉ sử dụng những nhãn thực sự có thông tin trong tin tuyển dụng.
7. Tổng cộng phải có 4-5 ý.
8. Mỗi ý dài khoảng 1-2 câu.
9. Không sử dụng emoji.
10. Không sử dụng Markdown.
11. Không thêm lời mở đầu hoặc giải thích.
12. Chỉ trả về JSON array gồm các string.

Ví dụ:

[
    "Trách nhiệm công việc: Thiết kế, xây dựng và tối ưu cơ sở dữ liệu; phát triển và bảo trì quy trình ETL từ nhiều nguồn dữ liệu.",
    "Kỹ năng & chuyên môn: Thành thạo SQL/PLSQL, NoSQL hoặc Java; có kinh nghiệm với các công cụ ETL và hệ thống báo cáo.",
    "Yêu cầu ứng viên: Tốt nghiệp Đại học trở lên các chuyên ngành Công nghệ thông tin, Khoa học máy tính hoặc các ngành liên quan.",
    "Quyền lợi: Được hưởng đầy đủ chế độ phúc lợi, bảo hiểm và có cơ hội phát triển trong môi trường chuyên nghiệp."
]

NỘI DUNG TUYỂN DỤNG:

{job_description}
"""

    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=list[str],
        ),
    )

    summary = response.parsed

    summary_text = "\n".join(
        f"• **{item.split(':', 1)[0]}:**{item.split(':', 1)[1]}"
        if ":" in item
        else f"• {item}"
        for item in summary
    )

    if url:
        link = f"[🔗 Xem job]({url})"
    else:
        link = "🔗 Không có link"

    return (
        f"**{index}. {title}**\n"
        f"🏢 {company}\n"
        f"📍 {address}\n"
        f"💰 {salary}\n"
        f"🧠 **AI Summary:**\n"
        f"{summary_text}\n"
        f"{link}"
    )


def send_to_discord(jobs, processing_date):
    if not jobs:
        print("Không có Data Engineer job.")
        return

    # Format từng job bằng Gemini
    formatted_jobs = []

    for index, job in enumerate(jobs, start=1):
        try:
            formatted_job = format_job(job, index)
            formatted_jobs.append(formatted_job)

        except Exception as e:
            print(
                f"Lỗi khi format job {index}: {e}"
            )

            # Nếu Gemini lỗi thì vẫn gửi job
            title = job.get("job_title") or "Không có tiêu đề"
            company = job.get("company") or "Không có thông tin"
            address = job.get("address") or "Không có thông tin"
            salary = job.get("salary") or "Thỏa thuận"
            url = job.get("link_description")

            link = (
                f"🔗 [Xem job]({url})"
                if url
                else "🔗 Không có link"
            )

            formatted_jobs.append(
                f"**{index}. {title}**\n"
                f"🏢 {company}\n"
                f"📍 {address}\n"
                f"💰 {salary}\n"
                f"{link}"
            )

    # Header
    header = (
        f"🔥 **New Data jobs** 🔥\n\n"
        f"📅 {processing_date}\n"
        f"📊 **{len(jobs)} jobs mới**\n\n"
    )

    # Discord Embed description tối đa 4096 ký tự.
    # Chia thành nhiều message nếu quá dài.
    chunks = []
    current_chunk = header

    for formatted_job in formatted_jobs:
        # +2 cho \n\n
        if len(current_chunk) + len(formatted_job) + 2 > 3800:
            chunks.append(current_chunk)
            current_chunk = formatted_job
        else:
            if current_chunk:
                current_chunk += "\n\n"

            current_chunk += formatted_job

    if current_chunk:
        chunks.append(current_chunk)

    # Gửi từng chunk
    for chunk_index, chunk in enumerate(chunks):
        webhook = DiscordWebhook(
            url=WEBHOOK_URL,
            username="Airflow"
        )

        embed = DiscordEmbed(
            description=chunk
        )

        if chunk_index == 0:
            embed.set_footer(
                text="Data Engineer Airflow"
            )

        webhook.add_embed(embed)

        response = webhook.execute()

        if response.status_code >= 300:
            raise RuntimeError(
                f"Discord error: "
                f"{response.status_code} "
                f"{response.text}"
            )

    print(
        f"Đã gửi {len(jobs)} Data Engineer jobs "
        f"vào Discord."
    )

def main():


    print(
        f"Đang lấy Data Engineer jobs "
        f"ngày {processing_date}..."
    )

    jobs = get_jobs(processing_date)

    print(
        f"Tìm thấy {len(jobs)} jobs."
    )

    send_to_discord(
        jobs,
        processing_date
    )


if __name__ == "__main__":
    main()