from django.db import connection

table_names = [
    "mocktest_mocktest",
    "mocktest_testquestion",
    "mocktest_testattempt",
    "mocktest_testresponse",
    "mocktest_testanswer",
]

with connection.cursor() as cursor:
    for table in table_names:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")
            print(f"Dropped table: {table}")
        except Exception as e:
            print(f"Could not drop {table}: {e}")