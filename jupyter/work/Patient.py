from db_lib import db
from collections.abc import Iterable
import pandas as pd

class Patient:
    '''A class to interface '''
    def __init__(self, mrn):
            self.mrn = str(mrn)
            #Interface with the database
            cursor = db()

            #First check if mrn exists
            sql = f"SELECT exists (SELECT 1 FROM clinical_document.q_document WHERE mrn = '{mrn}' LIMIT 1)"
            mrn_exists = cursor.sql(sql)[0][0]
            if not mrn_exists:
                raise ValueError("MRN number not found in the database")
            
            #Gets all the attributes from postgres database.
            sql = f"SELECT DISTINCT tag FROM clinical_document.q_document WHERE mrn = '{mrn}'"
            
            #psycopg2 returns the data each packed into tuples.  Eg. [(first_name),(last_name)] So that needs to be unpacked.
            self.attributes = list(map(lambda a : a[0],cursor.sql(sql))) 
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
        cursor = db()
        sql = f" SELECT attribute FROM clinical_document.q_document WHERE mrn = '{self.mrn}' AND tag = '{attribute}'" #Gets all rows of data for each attribute
        unformatted_data = cursor.sql(sql)
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
    
    
    @staticmethod
    def fetch_mrns():
        '''Returns a list of all the mrns found in the database'''
        sql = "SELECT DISTINCT mrn FROM clinical_document.q_document"
        cursor = db()
        data = cursor.sql(sql)
        data = sorted(list(map(lambda a : a[0], data)))
        return data
    
    @staticmethod
    def search_name(first_name = None,last_name = None):
        cursor = db()
        sql = "SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = 'first_name'"
        fname = cursor.sql(sql)
        fname_df = pd.DataFrame(list(map(lambda a : [a[0], *a[1].values()], fname)))
        fname_df.columns = "mrn","fname"

        sql = "SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = 'last_name'"
        lname = cursor.sql(sql)
        lname_df = pd.DataFrame(list(map(lambda a : [a[0], *a[1].values()], lname)))
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
       
    @staticmethod
    def search(tag):
        cursor = db()
        sql = f"SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = '{tag}'"
        data = cursor.sql(sql)
        index = list(map(lambda a : a[0], data))
        data_df = pd.DataFrame(list(map(lambda a : a[1], data)), index = index)
        data_df = data_df.sort_index()
        return data_df