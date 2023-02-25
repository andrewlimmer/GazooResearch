import getpass
import pandas as pd

import psycopg2
from psycopg2 import Error
from pathlib import Path

class Database:
    def __init__(self):
        '''Connect To Database'''
        print("Connect To Database")
        try:            
            # Connect to an existing database
            self.connection = psycopg2.connect(user=getpass.getpass(prompt='username:'),
                                                password=getpass.getpass(prompt='encryption key:'),
                                                host="clinical_db",
                                                port="5432",
                                                database="clinical",
                                                sslmode='require',
                                                # Schemas
                                                options="-c search_path=clinical_document,rad_onc,public")

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
    
    def fetch_mrns(self):
        '''Returns a list of all the mrns found in the database'''
        cursor = self.connection.cursor()
        sql = "SELECT DISTINCT mrn FROM clinical_document.q_document"
        cursor.execute(sql)
        data = cursor.fetchall()
        cursor.close()
        data = sorted(list(map(lambda a : a[0], data)))
        
        return data
    
    def search_name(self, first_name = None,last_name = None):
        cursor = self.connection.cursor()
        sql = "SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = 'first_name'"
        cursor.execute(sql)
        fname = cursor.fetchall()
        fname_df = pd.DataFrame(list(map(lambda a : [a[0], *a[1].values()], fname)))
        if fname_df.empty:
            fname_df = pd.DataFrame([[None,None]])
        fname_df.columns = "mrn","fname"

        sql = "SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = 'last_name'"
        cursor.execute(sql)
        lname = cursor.fetchall()
        cursor.close()
        lname_df = pd.DataFrame(list(map(lambda a : [a[0], *a[1].values()], lname)))
        if lname_df.empty:
            lname_df = pd.DataFrame([[None,None]])
        lname_df.columns = "mrn", "lname"

        name_df = fname_df.set_index("mrn").join(lname_df.set_index("mrn"))
        if not first_name and not last_name:
            return name_df
        elif first_name and not last_name:
            return name_df[name_df["fname"].str.contains(first_name, case = False)]
        elif not first_name and last_name:
            return name_df[name_df["lname"].str.contains(last_name, case = False)]
        else:
            return name_df[(name_df["fname"].str.contains(first_name, case = False)) & (name_df["lname"].str.contains(last_name, case = False))]
       
    def search(self, tag):
        cursor = self.connection.cursor()
        sql = f"SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = '{tag}'"
        cursor.execute(sql)
        data = cursor.fetchall()
        cursor.close()
        index = list(map(lambda a : a[0], data))
        data_df = pd.DataFrame(list(map(lambda a : a[1], data)), index = index)
        data_df = data_df.sort_index()
        return data_df