import pandas as pd
from mysql import connector
from mysql.connector import Error
from datetime import datetime
import os

AIRFLOW_HOME=os.environ.get("AIRFLOW_HOME")

from utils import (
    processing_address_columns,
    processing_salary_columns
)
df = pd.read_csv(
    os.path.join(
        AIRFLOW_HOME,
        "..",
        "data/data.csv"
    )
)

df = processing_address_columns(df)
df = processing_salary_columns(df)

job_detail_records = [
    (
        item.get("created_date"),
        item.get("job_title"),
        item.get("company"),
        item.get("salary"),
        item.get("address"),
        item.get("link_description"),
        item.get("city"),
        item.get("district"),
        item.get("min_salary"),
        item.get("max_salary"),
        item.get("salary_unit"),
        item.get("tag"),
        item.get("job_description"),
        item.get("time_published")
    )
    for item in df.to_dict(orient="records")
]

conn = connector.connect(
    host="mysql",
    port=3306,
    user="mysql",
    password="mysql",
    database="jobs_db"
)


try:
    if conn.is_connected():
        cursor = conn.cursor()

        cursor.execute(
            operation=(
                f"""
                DELETE FROM jobs
                WHERE created_date = '{datetime.today().date().strftime(f"%Y-%m-%d")}'
                """
            )
        )
        cursor.executemany(
            operation=(
                """
                INSERT INTO jobs(
                    created_date,  
                    job_title, 
                    company, 
                    salary, 
                    address,
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
            ),
            seq_params=job_detail_records
        )

        conn.commit()

        cursor.close()
        conn.close()
except Error as e:
    if conn:
        conn.rollback()

    print(f"Error while interacting with MySQL: {e}")