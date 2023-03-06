import getpass
import pandas as pd
import numpy as np
import psycopg2
from psycopg2 import Error
from pathlib import Path


# build OR sql query
def build_logical_or_sql_query(column, values):
  phase1 = f'\' OR {column}=\''.join(values)
  sql = f"{column}=\'{phase1}\'"
  return sql

# build OR sql query
def build_logical_OR_LIKE_sql_query(column, values):
  phase1 = f'\' OR {column} LIKE \''.join(values)
  sql = f"{column} LIKE \'{phase1}\'"
  return sql

# build AND sql query
def build_logical_AND_sql_query(column, values):
  phase1 = f'\' AND {column}=\''.join(values)
  sql = f"{column}=\'{phase1}\'"
  return sql
# build AND sql query
def build_logical_AND_LIKE_sql_query(column, values):
  phase1 = f'\' AND {column}=\''.join(values)
  sql = f"{column}=\'{phase1}\'"
  return sql

# build OR sql jsonb query
def build_logical_OR_LIKE_sql_json_query(attribute, values):
  phase1 = f'\' OR attribute->>\'{attribute}\' LIKE \''.join(values)
  sql = f"attribute->>\'{attribute}\' LIKE \'{phase1}\'"
  return sql


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
    
    def get_mrns_where_tag_value(self, data_options):
        # Connect to DB
        cursor = self.connection.cursor()

        tags = np.asarray([json['tag'] for json in data_options if 'tag' in json ])
        tags = np.unique(tags)

        # Get MRNS when only tags are specified, and no attributes
        mrns_no_attributes = None
        tags_no_attributes = [json['tag'] for json in data_options if ('tag' in json and 'attribute' not in json)]
        # Data without attributes
        if len(tags_no_attributes) > 0:
            sql = ''
            for idx, tag in enumerate(tags_no_attributes):
                if idx != 0: sql = sql + " INTERSECT "
                sql = sql + f" SELECT mrn FROM clinical_document.q_document WHERE tag LIKE '{tag}' "

            #print(f"{sql=}")
            cursor.execute(sql)
            mrns_ = np.unique(np.asarray(cursor.fetchall()).flatten())
            if mrns_no_attributes is None:  mrns_no_attributes = mrns_
            else: mrns_no_attributes = np.append(mrns_no_attributes, mrns_)


        # Loop through tags
        mrns_attributes = None
        for idx, tag in enumerate(tags):
            attributes = [json['attribute'] for json in data_options if ('tag' in json and 'attribute' in json and json['tag'] == tag)]

            # Data with attributes
            sql = 'SELECT DISTINCT mrn FROM clinical_document.q_document WHERE '
            for idy, attribute in enumerate(attributes):
                # sub_tags = np.asarray([json['sub_tag'] for json in data_options if json['tag'] == tag])
                values = np.asarray([json['value'] for json in data_options if ('tag' in json and 'attribute' in json and 'value' in json and json['tag'] == tag and json['attribute'] == attribute)]).flatten()
                if len(values) == 0: values=['%']
                #print(f"{values=}")


                if idy == 0: sql += f" tag LIKE '{tag}' "
                else: sql += f" AND tag LIKE '{tag}' "

                sql += f"AND ({build_logical_OR_LIKE_sql_json_query(attribute, values)})"
                #print(f"{sql=}")
                cursor.execute(sql)
                mrns_ = np.unique(np.asarray(cursor.fetchall()).flatten())

                if mrns_attributes is None: mrns_attributes = mrns_
                else: mrns_attributes = np.intersect1d(mrns_attributes, mrns_)

        # Close Cursor
        cursor.close()

        # Intersection
        mrns = None
        if mrns_no_attributes is not None:
            mrns = mrns_no_attributes
            if mrns_attributes is not None:
                mrns = np.intersect1d(mrns, mrns_attributes)
        else:
            if mrns_attributes is not None:
                mrns = mrns_attributes

        #print(f"end:{mrns}", flush=True)
        return np.unique(mrns)