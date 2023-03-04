import getpass
import pandas as pd
from collections.abc import Iterable

import psycopg2
from psycopg2 import Error
from pathlib import Path


class Patient:
    '''A class to interface '''
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
    
    def load_mrn(self, mrn):
            self.mrn = str(mrn)
            cursor = self.connection.cursor()

            #First check if mrn exists
            sql = f"SELECT exists (SELECT 1 FROM clinical_document.q_document WHERE mrn = '{mrn}' LIMIT 1)"
            cursor.execute(sql)
            data = cursor.fetchall()
            mrn_exists = data[0][0]
            if not mrn_exists:
                raise ValueError("MRN number not found in the database")
            
            #Gets all the attributes from postgres database.
            sql = f"SELECT DISTINCT tag FROM clinical_document.q_document WHERE mrn = '{mrn}'"
            cursor.execute(sql)
            data = cursor.fetchall()
            
            cursor.close()

            #psycopg2 returns the data each packed into tuples.  Eg. [(first_name),(last_name)] So that needs to be unpacked.
            self.attributes = list(map(lambda a : a[0],data)) 
            if "mrn" in self.attributes:
                self.attributes.remove("mrn")
    
            #Will iterate through all tags found in the database, and collect data from each of them.
            for attribute in self.attributes:
                rawdata = self.rawdata(attribute)
                try:
                    formatted_data = self.__formatdata(rawdata)
                    setattr(self,attribute,formatted_data)
                except:
                    setattr(self,attribute, None)
                    print(f"Error in inputting {attribute}.  Likely due to this datapoint being empty.  Try p.rawdata(attribute) if you think this was a bug.")
            self.attributes.append("mrn")
                    
    def rawdata(self,attribute):
        '''Input: attribute -> Output: data for that attribute in a list of dictionaries. 
        The data returned is exactly how it is stored in the SQL database.
        For example: [{'date': '2023-01-04', 'color': 'blue'}, {'date': '2023-01-12', 'color': 'green'}]
        The rationale for the existence of this method is twofold.
        1. There is a bug in setting an attribute due to a weird data entry or something else.
        2. It is hard to access a single cell of data in a DataFrame.  A dictionary is a lot easier. 
        '''
        cursor = self.connection.cursor()

        sql = f" SELECT attribute FROM clinical_document.q_document WHERE mrn = '{self.mrn}' AND tag = '{attribute}'" #Gets all rows of data for each attribute
        cursor.execute(sql)
        unformatted_data = cursor.fetchall()
        cursor.close()

        try:
            unformatted_data = list(map(lambda a : a[0], unformatted_data))
        except: 
             pass           
        
        return unformatted_data
    
    def __formatdata(self, rawdata): 
        '''Converts the data retrieved from the sql database into a dataframe.'''
        #Get all possible columns in the values below.
        if (len(rawdata[0]) == 1 and len(rawdata) == 1):
            return list(rawdata[0].values())[0]
        else:
            return pd.DataFrame(rawdata)
            
    def __repr__(self):
        '''When printed, this object should display all of its data. So that's what it is going to do.'''
        result = ""
        result += f"MRN: {self.mrn}\n\n"
        #iterate through attributes and print data from each
        for attribute in self.attributes:
            result +=f"{attribute}:\n"
            result += self.__getitem__(attribute).__str__() + "\n\n"
        return result
    

    def __getitem__(self,attribute):
        '''Supports p["first_name", "last_name"]'''
        if isinstance(attribute, str):
            return getattr(self,attribute)
        elif isinstance(attribute, Iterable):
            l = []
            for attr in attribute:
                l.append(getattr(self,attr))
            return l
        else:
            raise ValueError("Index should be the name of an attribute or a list of such.  For example, p['first_name'] or p['first_name','last_name']")
    
    
    