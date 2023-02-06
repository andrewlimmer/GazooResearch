import os
import psycopg2
from psycopg2 import Error
from pathlib import Path

class db:
    def __init__(self):
        try:
            # Connect to an existing database
            self.connection = psycopg2.connect(user=os.environ.get('POSTGRES_USER'),
                                                password=os.environ.get('POSTGRES_PASSWORD'),
                                                host="clinical_db",
                                                port="5432",
                                                database="clinical",
                                                # Schemas
                                                options="-c search_path=clinical_document,rad_onc,public")

            # Print PostgreSQL details
            #print("PostgreSQL server information")
            #print(connection.get_dsn_parameters(), "\n")
            self.cursor = self.connection.cursor()
        except (Exception, Error) as error:
            print("Error while connecting to PostgreSQL", error)
        
    def sql(self, sql):
        """
        SQL Request
        """
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        return data
    
    def __del__(self):
        self.cursor.close()
        self.connection.close()
        return
    