import os
import pymysql
import logging
from faker import Faker
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch environment variables for database connection
host = os.getenv('HOST')
port = 3306
user = os.getenv('USER')
password = os.getenv('PASSWORD')
database = os.getenv('DATABASE')

# Number of rows to insert for each column
num_rows = 10  # Change this number to insert more rows

try:
    # Connect to the database
    connection = pymysql.connect(host=host, port=port, user=user, password=password, database=database)
    logger.info("Connection to the database successful")

    # Create a cursor object to run the first SELECT statement
    with connection.cursor() as cursor:
        # Execute a SQL query to count rows before insertion
        cursor.execute("SELECT count(*) FROM assay_status")

        # Fetch the result
        result_before = cursor.fetchone()
        logger.info(f"Number of rows in assay_status before insertion: {result_before[0]}")

    # Generate Faker instance
    fake = Faker()

    # Generate UUIDs for each column
    state_ids = [str(fake.random_number(digits=10)) for _ in range(num_rows)]
    device_ids = [fake.uuid4() for _ in range(num_rows)]
    accession_ids = [fake.uuid4() for _ in range(num_rows)]
    assay_names = [fake.uuid4() for _ in range(num_rows)]
    state_names = [fake.uuid4() for _ in range(num_rows)]
    substates = [fake.uuid4() for _ in range(num_rows)]
    current_inds = [fake.random_int(min=0, max=1) for _ in range(num_rows)]
    notify_alternates = [fake.random_int(min=0, max=1) for _ in range(num_rows)]
    accession_create_dt_tm = [time.time() for _ in range(num_rows)]
    update_dt_tm = [time.time() for _ in range(num_rows)]

    # Generate SQL insert statements
    sql_insert_statements = []
    for i in range(num_rows):
        sql_insert = f"REPLACE INTO {database}.assay_status (STATE_ID, DEVICE_ID, ACCESSION_ID, ASSAY_NAME, STATE_NAME, SUBSTATE, CURRENT_IND, NOTIFY_ALTERNATES, ACCESSION_CREATE_DT_TM, UPDATE_DT_TM) VALUES ({state_ids[i]}, '{device_ids[i]}', '{accession_ids[i]}', '{assay_names[i]}', '{state_names[i]}', '{substates[i]}', {current_inds[i]}, {notify_alternates[i]}, {accession_create_dt_tm[i]}, {update_dt_tm[i]});"
        sql_insert_statements.append(sql_insert)

    # Create a cursor object to insert data and commit changes
    with connection.cursor() as cursor:
        for sql_insert in sql_insert_statements:
            cursor.execute(sql_insert)
        connection.commit()
        logger.info("Changes committed successfully")

    # Create a cursor object to run the second SELECT statement
    with connection.cursor() as cursor:
        # Execute a SQL query to count rows after insertion
        cursor.execute("SELECT count(*) FROM assay_status")

        # Fetch the result
        result_after = cursor.fetchone()
        logger.info(f"Number of rows in assay_status after insertion: {result_after[0]}")

finally:
    try:
        # Close the connection
        connection.close()
        logger.info("Connection closed successfully")
    except NameError:
        logger.warning("Connection object not found, unable to close")
