import getpass
import pandas as pd
import numpy as np
import psycopg2
from psycopg2 import Error
from pathlib import Path
from collections.abc import Iterable
from datetime import datetime


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
  phase1 = f"\' OR obj->>'value' LIKE \'".join(values)
  sql = f"obj->>'value' LIKE \'{phase1}\'"
  return sql

class Database:
    def __init__(self):
        '''Connect To Database'''
        print("Connect To Database")
        self.project_uuid = '%'
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
    
    def Patient(self, mrn):
        '''Creates a patient object.  '''
        return Patient(mrn, self.project_uuid, self.connection)
        
    def __del__(self):
        '''Disconnect from Database'''
        if hasattr(self, 'connection'):
            self.connection.close()
        return
        
    def set_project_uuid(self, uuid=None):
        self.project_uuid = uuid
        print(f"project_uuid: {self.project_uuid}")
        return 
    
    def fetch_projects(self):
        '''Returns a list of all the mrns found in the database'''
        cursor = self.connection.cursor()
        sql = "SELECT DISTINCT name, description, uuid FROM administrative.project"
        cursor.execute(sql)
        data = cursor.fetchall()
        cursor.close()
        project_df = pd.DataFrame(data, columns=['name', 'description', 'uuid'])
        return project_df
        
    def fetch_mrns(self):
        '''Returns a list of all the mrns found in the database'''
        cursor = self.connection.cursor()
        sql = f"SELECT DISTINCT mrn FROM clinical_document.q_document WHERE project_uuid LIKE '{self.project_uuid}'"
        cursor.execute(sql)
        data = cursor.fetchall()
        cursor.close()
        data = sorted(list(map(lambda a : a[0], data)))
        
        return data
    
    def search_name(self, first_name = None, last_name = None):
        cursor = self.connection.cursor()
        # Search First Name
        sql = f"SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = 'first_name' AND project_uuid LIKE '{self.project_uuid}'"
        cursor.execute(sql)
        fname = cursor.fetchall()
        fname_df = pd.DataFrame([[x[0],x[1][0]['value']] for x in fname])
        if fname_df.empty:
            fname_df = pd.DataFrame([[None,None]])
        fname_df.columns = "mrn","first_name"
        #print(f"{fname_df=}")
        
        # Search Last Name
        sql = f"SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = 'last_name' AND project_uuid LIKE '{self.project_uuid}'"
        cursor.execute(sql)
        lname = cursor.fetchall()
        cursor.close()
        lname_df = pd.DataFrame([[x[0],x[1][0]['value']] for x in lname])
        if lname_df.empty:
            lname_df = pd.DataFrame([[None,None]])
        lname_df.columns = "mrn", "last_name"
        #print(f"{lname_df=}")
        # Join
        #name_df = pd.concat([fname_df.set_index("mrn"), lname_df.set_index("mrn")])
        name_df = pd.merge(fname_df, lname_df, how="outer")

        try:
            if not first_name and not last_name:
                return name_df
            elif first_name and not last_name:
                name_df.dropna(subset=['first_name'], inplace=True)
                return name_df[name_df["first_name"].str.contains(first_name, case = False)]
            elif not first_name and last_name:
                name_df.dropna(subset=['last_name'], inplace=True)
                return name_df[name_df["last_name"].str.contains(last_name, case = False)]
            else:
                name_df.dropna(subset=['last_name','first_name'], inplace=True)
                return name_df[(name_df["first_name"].str.contains(first_name, case = False)) & (name_df["last_name"].str.contains(last_name, case = False))]
        except KeyError:
            return None
       
    def search(self, tag=None, icd10=None):
        cursor = self.connection.cursor()
        if icd10 and tag:
            sql = f"SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE icd10='{icd10}' AND tag = '{tag}' AND project_uuid LIKE '{self.project_uuid}'"
        elif icd10 is None and tag:
            sql = f"SELECT DISTINCT mrn, attribute FROM clinical_document.q_document WHERE tag = '{tag}' AND project_uuid LIKE '{self.project_uuid}'"
        else:
            raise ValueError("Must include a 'tag' parameter")
        
        cursor.execute(sql)
        data = cursor.fetchall()
        if len(data) == 0:
            return pd.DataFrame([])
        cursor.close()
        # Get MRN index
        index = list(map(lambda a : a[0], data))
        
        # Get Attributes Values
        data_df = pd.DataFrame([[x['value'] for x in a[1]] for a in data], index = index)
        # Column Names
        data_df.columns = [[x['name'] for x in a[1]] for a in data][0]
        data_df.index.names = ['mrn']
        # Sort
        data_df = data_df.sort_index()
        return data_df

    def get_mrns_where_filters(self, filters):
        '''
        Get mrns that match a specific filters.
        
        parameters:
        filters: <list<json>>; structure of json is 
        eg. "{'icd10':'c61', 'tag': 'surgery'}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery'}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery', 'value': ['prostatectomy-lymphadenectomy']}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery', 'value': ['prostatectomy-lymphadenectomy', 'prostatectomy']}". 
        # You may use wildcard '%'
        eg. "{'icd10':'c61', 'tag': '%urgery', 'attribute': 'surgery', 'value': ['prostatectomy%']}". 
            
        return:
        mrns: <list>; list of mrns that match sequence
        '''
        # Connect to DB
        cursor = self.connection.cursor()
        sql = f"SELECT DISTINCT mrn FROM clinical_document.q_document WHERE project_uuid LIKE '{self.project_uuid}'"
        cursor.execute(sql)
        mrns = cursor.fetchall()
        # Close Cursor
        cursor.close()
        
        if mrns != None and len(mrns) > 0:
            mrns = np.asarray(mrns).flatten()
        else:
            return []
        
        # Loop through MRNs
        filter_exists = np.full_like(mrns, fill_value=False, dtype=bool)
        for idx, mrn in enumerate(mrns):
            if self.does_filter_exist(mrn, filters):
               filter_exists[idx] = True 
        
        return mrns[filter_exists].tolist()
    
    # Does filter apply to patient.
    def does_filter_exist(self, mrn, filters):
        """
        Determines if the full filter applies to patient 
        mrn: <string>; string of mrn
        filters: <list<json>>; structure of json is 
        eg. "{'icd10':'c61', 'tag': 'surgery'}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery'}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery', 'value': ['prostatectomy-lymphadenectomy']}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery', 'value': ['prostatectomy-lymphadenectomy', 'prostatectomy']}". 
        # You may use wildcard '%'
        eg. "{'icd10':'c61', 'tag': '%urgery', 'attribute': 'surgery', 'value': ['prostatectomy%']}". 
    
        return:
        <boolean>; True -> if the tags exists
        """
        assert isinstance(mrn, str), f"mrn should be strings. mrn={mrn} type(mrn)={type(mrn)}"
        assert isinstance(filters, list), f"filters should be a list. filters={filters} type(filters)={type(filters)}"
    
        # Connect to DB
        cursor = self.connection.cursor()
    
        sql = ''
        # Build SQL Logic
        # Loop through tags
        for idx, filter in enumerate(filters):
            #print(filter)
            
            # New Search Term
            if idx != 0: sql = sql + ' OR'
            
            # If icd10 exists
            if 'icd10' in filter.keys() and filter['icd10'] != None: 
                #print(f"icd10:{filter['icd10']}")
                sql = sql + f" (icd10 LIKE '{filter['icd10']}' "
            else:
                sql = sql + f" (icd10 IS NULL "
                
            
            # If icd10 exists
            if 'tag' in filter.keys(): 
                #print(f"tag:{filter['tag']}")
                sql = sql + f"AND tag LIKE '{filter['tag']}' "
    
            # If attribute exists
            if 'attribute' in filter.keys(): 
                #print(f"attribute:{filter['attribute']}")
                sql = sql + f"AND obj->>'name' LIKE '{filter['attribute']}' "
    
            # If attribute values exists
            if 'value' in filter.keys(): 
                #print(f"attribute values:{filter['value']}")
                sql = sql +'AND ('+ build_logical_OR_LIKE_sql_query(column="obj->>'value'", values=filter["value"]) +')'
    
            sql = sql + ')'
        # Built SQL Search Logic
        #print(sql)
        
        # Query
        sql_ = f"SELECT DISTINCT icd10, tag \
                FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                WHERE mrn='{mrn}' \
                AND ( \
                        {sql} \
                    ) \
                AND project_uuid LIKE '{self.project_uuid}'"
        #print(sql_)
        cursor.execute(sql_)
        output = cursor.fetchall()
        # Close Cursor
        cursor.close()
        if output == None or len(output) == 0 or len(output) < len(filters):
            return False
        else: 
            return True

    def does_target_filter_exist(self, mrn, target_id, filters):
        # Build SQL Logic
        for idx, filter in enumerate(filters):
            #print(filter)
            logic = ''
            
            # If icd10 exists
            if 'icd10' in filter.keys() and filter['icd10'] != None: 
                #print(f"icd10:{filter['icd10']}")
                logic = logic + f" (icd10 LIKE '{filter['icd10']}' "
            else:
                logic = logic + f" (icd10 IS NULL "
                
            
            # If icd10 exists
            if 'tag' in filter.keys(): 
                #print(f"tag:{filter['tag']}")
                logic = logic + f"AND tag LIKE '{filter['tag']}' "
        
            # If attribute exists
            if 'attribute' in filter.keys(): 
                #print(f"attribute:{filter['attribute']}")
                logic = logic + f"AND obj->>'name' LIKE '{filter['attribute']}' "
        
            # If attribute values exists
            if 'value' in filter.keys(): 
                #print(f"attribute values:{filter['value']}")
                logic = logic +'AND ('+ build_logical_OR_LIKE_sql_query(column="obj->>'value'", values=filter["value"]) +')'
            logic = logic + ')'

            # Does mrn-target meet criteria
            cursor = self.connection.cursor()
            sql = f"SELECT target.attribute \
                    FROM \
                        (SELECT q.icd10, q.tag, q.attribute \
                        FROM clinical_document.q_document as q, jsonb_array_elements(q.attribute) as attr \
                        WHERE q.mrn='{mrn}' AND attr->>'name'='target-id' AND attr->>'value'='{target_id}') target, \
                        jsonb_array_elements(target.attribute) as obj \
                    WHERE {logic} "
            #print(f"{sql=}")
            cursor.execute(sql)
            count = cursor.fetchone()
            cursor.close()
            if count == None: return False
        return True

    def get_mrn_targets_where_filter(self, filters):
        cursor = self.connection.cursor()
        
        # Get All MRNs & Targets
        sql = f"SELECT DISTINCT q.mrn as mrn, attr->>'value' as target \
                FROM clinical_document.q_document as q, jsonb_array_elements(q.attribute) as attr \
                WHERE attr->>'name'='target-id' AND q.project_uuid='{self.project_uuid}'"
        cursor.execute(sql)
        mrn_targets = np.asarray(cursor.fetchall())
        #print(mrn_targets)
        valids = np.full(shape=len(mrn_targets), fill_value=False)

        cursor.close()

        # Loop through MRNs
        filter_exists = np.full(len(mrn_targets), fill_value=False, dtype=bool)
        for idx, (mrn, target_id) in enumerate(mrn_targets):
            if self.does_target_filter_exist(mrn, target_id, filters):
                filter_exists[idx] = True 
        
        return mrn_targets[filter_exists].tolist()

    def get_mrns_where_sequence(self, filters, max_time_deltas):
        '''
        Get mrns that match a specific sequence.
        
        parameters:
        filters: <list<json>>; structure of json is 
        eg. "{'icd10':'c61', 'tag': 'surgery'}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery'}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery', 'value': ['prostatectomy-lymphadenectomy']}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery', 'value': ['prostatectomy-lymphadenectomy', 'prostatectomy']}". 
        # You may use wildcard '%'
        eg. "{'icd10':'c61', 'tag': '%urgery', 'attribute': 'surgery', 'value': ['prostatectomy%']}". 

        max_time_deltas: <list<int>>; numbers represent days. length must be one less than filters
        
        eg. sequence: surgery --> less than 60 days --> external-radiation 
        filters: [{'icd10':'c61', 'tag': 'surgery'}, {'icd10':'c61', 'tag': 'external-radiation'}]
        max_time_deltas: [60]
        
        return:
        mrns: <list>; list of mrns that match sequence
        '''
        # Connect to DB
        cursor = self.connection.cursor()
        sql = f"SELECT DISTINCT mrn FROM clinical_document.q_document WHERE project_uuid LIKE '{self.project_uuid}'"
        cursor.execute(sql)
        mrns = cursor.fetchall()
        # Close Cursor
        cursor.close()
        
        if mrns != None and len(mrns) > 0:
            mrns = np.asarray(mrns).flatten()
        else:
            return []
        
        # Loop through MRNs
        sequence_exists = np.full_like(mrns, fill_value=False, dtype=bool)
        for idx, mrn in enumerate(mrns):
            if self.does_sequence_exist(mrn, filters, max_time_deltas):
               sequence_exists[idx] = True 
        
        return mrns[sequence_exists].tolist()

    # Does sequence exist eg. sugery --> Time -->RT
    def does_sequence_exist(self, mrn, filters, max_time_deltas):
        """
        Determines if the full time sequence exists. each tag is present within 
        mrn: <string>; string of mrn
        filters: <list<json>>; structure of json is 
        eg. "{'icd10':'c61', 'tag': 'surgery'}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery'}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery', 'value': ['prostatectomy-lymphadenectomy']}". 
        eg. "{'icd10':'c61', 'tag': 'surgery', 'attribute': 'surgery', 'value': ['prostatectomy-lymphadenectomy', 'prostatectomy']}". 
        # You may use wildcard '%'
        eg. "{'icd10':'c61', 'tag': '%urgery', 'attribute': 'surgery', 'value': ['prostatectomy%']}". 
    
        max_time_deltas: <list<int>>; numbers represent days. length must be one less than filters
        
        eg. sequence: surgery --> less than 60 days --> external-radiation 
        filters: [{'icd10':'c61', 'tag': 'surgery'}, {'icd10':'c61', 'tag': 'external-radiation'}]
        max_time_deltas: [60]
        return:
        <boolean>; True -> if the time sequence exists
        """
        assert isinstance(mrn, str), f"mrn should be strings. mrn={mrn} type(mrn)={type(mrn)}"
        assert isinstance(filters, list), f"filters should be a list. filters={filters} type(filters)={type(filters)}"
        assert isinstance(max_time_deltas, list), f"max_time_deltas should be a list. max_time_deltas={max_time_deltas} type(max_time_deltas)={type(max_time_deltas)}"
        assert len(max_time_deltas) == len(filters)-1, f"max_time_deltas length should equal len(filters)-1"
    
        # Connect to DB
        cursor = self.connection.cursor()
    
        sql = ''
        # Build SQL Logic
        # Loop through tags
        for idx, filter in enumerate(filters):
            #print(filter)
            
            # New Search Term
            if idx != 0: sql = sql + ' OR'
            
            # If icd10 exists
            if 'icd10' in filter.keys() and filter['icd10'] != None: 
                #print(f"icd10:{filter['icd10']}")
                sql = sql + f" (icd10 LIKE '{filter['icd10']}' "
            else:
                sql = sql + f" (icd10 IS NULL "
            
            # If icd10 exists
            if 'tag' in filter.keys(): 
                #print(f"tag:{filter['tag']}")
                sql = sql + f"AND tag LIKE '{filter['tag']}' "
    
            # If attribute exists
            if 'attribute' in filter.keys(): 
                #print(f"attribute:{filter['attribute']}")
                sql = sql + f"AND obj->>'name' LIKE '{filter['attribute']}' "
    
            # If attribute values exists
            if 'value' in filter.keys(): 
                #print(f"attribute values:{filter['value']}")
                sql = sql +'AND ('+ build_logical_OR_LIKE_sql_query(column="obj->>'value'", values=filter["value"]) +')'
    
            sql = sql + ')'
        # Built SQL Search Logic
        #print(sql)
        
        # Query
        sql_ = f"SELECT DISTINCT select_tags.icd10 || ':' || select_tags.tag as icd10_tag, obj->>'value' as date \
                FROM \
                	(SELECT DISTINCT icd10, tag, obj->>'name' as attr, obj->>'value' as value, attribute \
                	FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                	WHERE mrn='{mrn}' \
                	AND ( \
                			{sql} \
                		) \
                	AND project_uuid LIKE '{self.project_uuid}') select_tags, \
                	jsonb_array_elements(select_tags.attribute) obj \
                WHERE (obj->>'name'='date' or obj->>'name'='start_date' or obj->>'name'='end_date') \
                ORDER BY date"
        #print(sql_)
        cursor.execute(sql_)
        output = cursor.fetchall()
        # Close Cursor
        cursor.close()
    
        if output != None and len(output) > 0:
            tickets = np.asarray(output)
        else:
            return None
        
        #print(tickets)
        # Loop through search terms
        icd10_tags = [f"{filter['icd10']}:{filter['tag']}" for idx, filter in enumerate(filters)]
        bool = np.full(len(filters)-1, fill_value=False)
        for idx, icd10_tag in enumerate(icd10_tags):
    
            # ith search term
            arr_index = np.where(tickets[:,0] == icd10_tag)
            index_icd10_tag_dates_0 = tickets[arr_index][:,1]
            index_icd10_tag_dates_0 = [datetime.strptime(date, '%Y-%m-%d').date() for date in index_icd10_tag_dates_0 if date != '']
    
            # Stop Comparison if last search term
            if idx >= len(icd10_tags)-1:
                continue
            
            # i+1th Search Term
            arr_index = np.where(tickets[:,0] == icd10_tags[idx+1])
            index_icd10_tag_dates_1 = tickets[arr_index][:,1]
            index_icd10_tag_dates_1 = [datetime.strptime(date, '%Y-%m-%d').date() for date in index_icd10_tag_dates_1 if date != '']
    
            # Compare Dates to Meet max_time_delta criteria
            #print(index_icd10_tag_dates_0)
            #print(index_icd10_tag_dates_1)
    
            diff = []
            for date0 in index_icd10_tag_dates_0:
                for date1 in index_icd10_tag_dates_1:
                    diff.append((date1-date0).days)
                    #print((date1-date0).days)
                    # Calculate Date Diff
                    if abs(date1-date0).days < max_time_deltas[idx] or ((date1-date0).days>0 and max_time_deltas[idx]==-1):
                        bool[idx] = True
            diff = np.asarray(diff)
            # Within 
            #print(diff)
            #print(np.unique(np.where(diff>=0,True,False)))
            if len(np.unique(np.where(diff>=0,True,False)))==2: bool[idx] = True
        return np.all(bool)


    
    # Get Start Date
    def get_start_date(self, mrn, icd10, tag, occurance = 0):
        """
        Gets the start date of a tag. If there are multiple occurance of the tag it will by default find the earliest occurance
        parameters:
        mrn: <string>, Medical record number
        icd10: <string>, icd10 number. eg. c61 or c53.9
        tag: <sting>, tag
        occurance: <int>, If multiple occurance of the tag.  0 -> First occurance; 1 -> second occurance; -1  -> Last Occurance
        """
        # Connect to DB
        cursor = self.connection.cursor()

        sql_ = f"SELECT DISTINCT obj->>'value' as date \
                FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                WHERE project_uuid LIKE '{self.project_uuid}' \
                AND mrn = '{mrn}' \
                AND icd10 LIKE '{icd10}' \
                AND tag LIKE'{tag}' \
                AND (obj->>'name' = 'start_date' OR obj->>'name' = 'date') \
                ORDER BY obj->>'value'"
        cursor.execute(sql_)
        dates = np.array(cursor.fetchall()).flatten()
        # Remove None and covert to datetime
        dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates if date is not None]
        dates.sort()
        

        # Start Date Does Not Exist
        if len(dates) == 0:
            date =  None
        else:
            date = dates[occurance]

        # Close Cursor
        cursor.close()
        return date

    # Get Event Date
    def get_event_date(self, mrn, icd10, tags, start_date):
        # Connect to DB
        cursor = self.connection.cursor()

        # Get Positive Event Date
        sql = f"SELECT DISTINCT obj->>'value' as date \
                FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                WHERE project_uuid LIKE '{self.project_uuid}' \
                AND mrn = '{mrn}' \
                AND icd10 LIKE '{icd10}' \
                AND ({build_logical_OR_LIKE_sql_query('tag', tags)}) \
                AND (obj->>'name' = 'start_date' OR obj->>'name' = 'date') \
                AND obj->>'value' >= '{start_date}'\
                ORDER BY obj->>'value'"
        #print(f"{sql=}")
        cursor.execute(sql)
        dates = np.array(cursor.fetchall()).flatten()
        # Remove None and covert to datetime
        dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates if date is not None]
        dates.sort()

        # Date Exists
        if len(dates) > 0:
            date = dates[0]
            # Event True tag
            event = True
        else:
            # If No positive Get Last Event
            sql = f"SELECT DISTINCT obj->>'value' as date \
                    FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                    WHERE project_uuid LIKE '{self.project_uuid}' \
                    AND mrn = '{mrn}' \
                    AND (obj->>'name' = 'end_date' OR obj->>'name' = 'date') \
                    AND obj->>'value' IS NOT NULL \
                    ORDER BY obj->>'value' DESC \
                    LIMIT 1;"
            #print(sql)
            cursor.execute(sql)
            dates = np.array(cursor.fetchall()).flatten()

            # Remove None and convert to datetime
            dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates if date is not None]
            #print(f"{mrn=}")
            #print(f"{dates=}")

            # Remove patient is no dates exist
            if len(dates) != 0:
                # Get last Occurance
                dates.sort()
                date = dates[-1]
            else:
                date = None
        
            # Event is False
            event=False

        # Close Cursor
        cursor.close()
        return date, event
    
    def kaplan_meier(self, mrns, icd10, start_tag, event_tags):
        """
        Generate Kaplan Meier Curves for a patient level event
        mrns: list<string>
        start_tag: <string>
        event_tag: list<string>: 
        """
        assert isinstance(mrns, list), f"mrns should be a list of strings. mrns={mrns} type(mrns)={type(mrns)}"
        assert isinstance(icd10, str), f"icd10 should be a strings. icd10={icd10} type(icd10)={type(icd10)}"
        assert isinstance(start_tag, str), f"start_tag should be a strings. start_tag={start_tag} type(start_tag)={type(start_tag)}"
        assert isinstance(event_tags, list), f"event_tags should be a list of strings. event_tags={event_tags} type(mrns)={type(event_tags)}"
        
        # Get MRNs
        durations = []
        events = []
        remove_idx = []
        for idx, mrn in enumerate(mrns):
            #print(f"{mrn=}", flush=True)
            start_date = self.get_start_date(mrn, icd10, start_tag, occurance = 0)
            #print(f"{start_date=}", flush=True)
            # Check if start date exists
            if start_date == None:
                remove_idx.append(idx)
                continue

            #print(f"{event=}", flush=True)
            event_date, event_ = self.get_event_date(mrn, icd10, event_tags, start_date)
            #print(f"{event_date=}", flush=True)
            # Check if event date exists
            if event_date == None:
                remove_idx.append(idx)
                continue

            durations.append((event_date - start_date).days)
            events.append(event_)
            #print(f"{mrn=}", f"{start_date=}", f"{event_date=}", f"{event=}", flush=True)

        # Remove MRNs without start event
        mrns = np.delete(mrns, remove_idx).tolist()
        #print(f"{durations=}", flush=True)
        #print(f"{events=}", flush=True)

        output = {'mrns':mrns, 'durations':durations, 'events':np.asarray(events).astype(int).tolist()}

        return output
    
    # Get Start Date
    def get_target_start_date(self, mrn, target_id, icd10, tag, occurance = 0):
        """
        Gets the start date of a tag. If there are multiple occurance of the tag it will by default find the earliest occurance
        parameters:
        mrn: <string>, Medical record number
        icd10: <string>, icd10 number. eg. c61 or c53.9
        tag: <sting>, tag
        occurance: <int>, If multiple occurance of the tag.  0 -> First occurance; 1 -> second occurance; -1  -> Last Occurance
        """
        # Connect to DB
        cursor = self.connection.cursor()
    
        sql_ = f"SELECT DISTINCT obj->>'value' as date \
                FROM  \
                	(SELECT icd10, tag, obj->>'value' as target_id, attribute \
                	FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                	WHERE project_uuid LIKE '{self.project_uuid}' \
                    AND mrn = '{mrn}' \
                	AND icd10 LIKE '{icd10}' \
                	AND tag LIKE '{tag}' \
                	AND (obj->>'name' = 'target-id' AND obj->>'value'='{target_id}')) target, \
                	jsonb_array_elements(target.attribute) obj \
                WHERE \
                (obj->>'name' = 'start_date' OR obj->>'name' = 'date') \
                ORDER BY obj->>'value'"
        cursor.execute(sql_)
        dates = np.array(cursor.fetchall()).flatten()
        #print(dates)
        # Remove None and covert to datetime
        dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates if date is not None]
        dates.sort()
        
    
        # Start Date Does Not Exist
        if len(dates) == 0:
            date =  None
        else:
            date = dates[occurance]
    
        # Close Cursor
        cursor.close()
        return date
        
    # Get Event Date
    def get_target_event_date(self, mrn, target_id, icd10, event_tags, start_date):
        # Connect to DB
        cursor = self.connection.cursor()
    
        # Get Positive Event Date
        sql = f"SELECT DISTINCT obj->>'value' as date \
                FROM  \
                	(SELECT icd10, tag, obj->>'value' as target_id, attribute \
                	FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                	WHERE project_uuid LIKE '{self.project_uuid}' \
                    AND mrn = '{mrn}' \
                	AND icd10 LIKE '{icd10}' \
                	AND ({build_logical_OR_LIKE_sql_query('tag', event_tags)}) \
                	AND (obj->>'name' = 'target-id' AND obj->>'value'='{target_id}')) target, \
                	jsonb_array_elements(target.attribute) obj \
                WHERE \
                (obj->>'name' = 'start_date' OR obj->>'name' = 'date') \
                ORDER BY obj->>'value'"
        cursor.execute(sql)
        dates = np.array(cursor.fetchall()).flatten()
        # Remove None and covert to datetime
        dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates if date is not None]
        dates.sort()
    
        # Date Exists
        if len(dates) > 0:
            date = dates[0]
            # Event True tag
            event = True
        else:
            # If No positive Get Last Event
            sql = f"SELECT DISTINCT obj->>'value' as date \
                    FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                    WHERE project_uuid LIKE '{self.project_uuid}' \
                    AND mrn = '{mrn}' \
                    AND (obj->>'name' = 'end_date' OR obj->>'name' = 'date') \
                    AND obj->>'value' IS NOT NULL \
                    ORDER BY obj->>'value' DESC \
                    LIMIT 1;"
            #print(sql)
            cursor.execute(sql)
            dates = np.array(cursor.fetchall()).flatten()
    
            # Remove None and convert to datetime
            dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates if date is not None]
            #print(f"{mrn=}")
            #print(f"{dates=}")
    
            # Remove patient is no dates exist
            if len(dates) != 0:
                # Get last Occurance
                dates.sort()
                date = dates[-1]
            else:
                date = None
        
            # Event is False
            event=False
    
        # Close Cursor
        cursor.close()
        return date, event
            
    def target_kaplan_meier(self, mrn_targets, icd10, start_tag, event_tags):
        """
        Obtains Kaplan Meier for targets
        parameters:
        
        returns:
        
        """
        assert isinstance(mrn_targets, list), f"mrn_targets should be a 2d list of strings. mrn_targets={mrn_targets} type(mrn_targets)={type(mrn_targets)}"
        assert np.asarray(mrn_targets).shape[1] == 2, f"mrn_targets should be of shape (,2) list of strings. mrn_targets.shape={np.asarray(mrn_targets).shape}"
        assert isinstance(icd10, str), f"icd10 should be a strings. icd10={icd10} type(icd10)={type(icd10)}"
        assert isinstance(start_tag, str), f"start_tag should be a strings. start_tag={start_tag} type(start_tag)={type(start_tag)}"
        assert isinstance(event_tags, list), f"event_tags should be a list of strings. event_tags={event_tags} type(mrns)={type(event_tags)}"
        
        durations = []
        events = []
        remove_idx = []
        # Loop through targets
        for idx, (mrn, target_id) in enumerate(mrn_targets):
            #print(mrn, target_id)
            start_date = self.get_target_start_date(mrn, target_id, icd10, tag=start_tag)
            #print(f"{start_date=}")
            # Check if start date exists
            if start_date == None:
                remove_idx.append(idx)
                continue
                    
            if start_date==None: continue
            event_date, event = self.get_target_event_date(mrn, target_id, icd10, event_tags, start_date)
            #print(f"{event_date=} event:{event}")
            # Check if event date exists
            if event_date == None:
                remove_idx.append(idx)
                continue
            
            durations.append((event_date - start_date).days)
            events.append(event)
            #print(f"{mrn=}", f"{target_id=}", f"{start_date=}", f"{event_date=}", f"{event=}", flush=True)
            
        mrn_targets = np.delete(mrn_targets, remove_idx, axis=0).tolist()
        #print(f"{durations=}", flush=True)
        #print(f"{events=}", flush=True)
    
        output = {'mrn_targets':mrn_targets, 'durations':durations, 'events':np.asarray(events).astype(int).tolist()}
        
        return output
        
class Patient:
    '''A class to provide interface with the database by formatting the data.'''
    def __init__(self, mrn, project_uuid, connection):
        '''Connect To Database'''
        self.connection = connection
        self.cursor = self.connection.cursor()
        self.project_uuid = project_uuid
        
        if not hasattr(self, "cursor"):
            return
        
        self.mrn = str(mrn)
        #First check if mrn exists
        sql = f"SELECT exists (SELECT 1 FROM clinical_document.q_document WHERE mrn = '{mrn}' AND project_uuid LIKE '{self.project_uuid}' LIMIT 1)"
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        mrn_exists = data[0][0]
        if not mrn_exists:
            raise ValueError("MRN number not found in the database")
        
        #Gets all the tags from postgres database.
        #sql = f"SELECT DISTINCT tag FROM clinical_document.q_document WHERE mrn = '{mrn}'"
        sql = f"(SELECT DISTINCT tag as tag FROM clinical_document.q_document WHERE mrn = '{mrn}' and icd10 IS NULL AND project_uuid LIKE '{self.project_uuid}') \
                UNION ALL \
                (SELECT DISTINCT icd10 ||':'|| tag as tag FROM clinical_document.q_document WHERE mrn = '{mrn}' and icd10 IS NOT NULL AND project_uuid LIKE '{self.project_uuid}')"
        self.cursor.execute(sql)
        data = self.cursor.fetchall()

        #psycopg2 returns the data each packed into tuples.  Eg. [(first_name),(last_name)] So that needs to be unpacked.
        self.icd10_tags = list(map(lambda a : a[0], data)) 
        if "mrn" in self.icd10_tags:
            self.icd10_tags.remove("mrn")
        
        #Will iterate through all tags found in the database, and collect data from each of them.
        for tag in self.icd10_tags:
            rawdata = self.rawdata(tag)
            try:
                formatted_data = self.__formatdata(rawdata)
                setattr(self, tag, formatted_data)
            except:
                setattr(self, tag, None)
                print(f"Error in inputting {tag}.  Likely due to this datapoint being empty.  Try p.rawdata(attribute) if you think this was a bug.")
        
        self.icd10_tags.append("mrn")
            
        return
    
                    
    def rawdata(self, icd10_tag):
        '''Input: icd10_tag -> Output: data for that attribute in a list of dictionaries. 
        The data returned is exactly how it is stored in the SQL database.
        For example: [{'name': 'date', 'type': 'date', 'value': '2022-11-28'}, {'name': 'psa', 'type': 'number', 'value': 0.16}, {'name': 'unit', 'type': 'list', 'value': 'ng/mL'}]
        The rationale for the existence of this method is twofold.
        1. There is a bug in setting an attribute due to a weird data entry or something else.
        2. It is hard to access a single cell of data in a DataFrame.  A dictionary is a lot easier. 
        '''
        cursor = self.connection.cursor()

        # separate icd and tag (eg. 'c61:psa')
        
        if len(icd10_tag.split(':')) >= 2:
            icd10 = icd10_tag.split(':')[0]
            tag = icd10_tag.split(':')[1]
        else:
            icd10 = None
            tag = icd10_tag

        if icd10 is None:
            sql = f" SELECT attribute FROM clinical_document.q_document WHERE mrn = '{self.mrn}' AND icd10 IS NULL AND tag = '{tag}' AND project_uuid LIKE '{self.project_uuid}'" #Gets all rows of data for each attribute
        else:
            sql = f" SELECT attribute FROM clinical_document.q_document WHERE mrn = '{self.mrn}' AND icd10 = '{icd10}' AND tag = '{tag}' AND project_uuid LIKE '{self.project_uuid}'" #Gets all rows of data for each attribute
        
        cursor.execute(sql)
        unformatted_data = cursor.fetchall()
        cursor.close()
        try:
            # Get Data
            unformatted_data = [[{'name':attribute['name'], 'type':attribute['type'], 'value':attribute['value']} for attribute in tag[0]] for tag in unformatted_data]

        except: 
             pass        
        
        return unformatted_data
    
    def __formatdata(self, rawdata): 
        '''Converts the data retrieved from the sql database into a dataframe.'''
        
        # Get Heading
        headings = list([[y['name'] for y in heading] for heading in rawdata][0])
        # Get Data
        data = [[y['value'] for y in x] for x in rawdata]
        return pd.DataFrame(data, columns=headings)

    def __repr__(self):
        '''When printed, this object should display all of its data. So that's what it is going to do.'''
        result = ""
        result += f"MRN: {self.mrn}\n\n"
        #iterate through attributes and print data from each
        for tag in self.icd10_tags:
            result +=f"{tag}:\n"
            result += self.__getitem__(tag).__str__() + "\n\n"
        return result
    

    def __getitem__(self, tag):
        '''Supports p["first_name", "last_name"]'''
        if isinstance(tag, str):
            return getattr(self,tag)
        elif isinstance(tag, Iterable):
            l = []
            for attr in tag:
                l.append(getattr(self,attr))
            return l
        else:
            raise ValueError("Index should be the name of an attribute or a list of such.  For example, p['first_name'] or p['first_name','last_name']")