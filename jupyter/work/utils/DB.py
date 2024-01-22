import getpass
import pandas as pd
import numpy as np
import psycopg2
from psycopg2 import Error
from pathlib import Path

class DB:
    def __init__(self):
        '''Connect To Database'''
        print("Connect To Database")
        try:            
            # Connect to an existing database
            self.connection = psycopg2.connect(user='postgres',#getpass.getpass(prompt='username:'),
                                                password=getpass.getpass(prompt='encryption key:'),
                                                host="clinical_db",
                                                port="5432",
                                                database="clinical",
                                                sslmode='require',
                                                # Schemas
                                                options="-c search_path=clinical_document,public")

            # Print PostgreSQL details
            print(f"Connected: {self.connection.get_dsn_parameters()}")
        except (Exception, Error) as error:
            print("Error while connecting to PostgreSQL: ", error)
        return
    
    def __del__(self):
        '''Disconnect from Database'''
        if hasattr(self, 'connection'):
            self.connection.close()
        return
    