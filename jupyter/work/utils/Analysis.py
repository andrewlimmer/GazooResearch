import getpass
import psycopg2
from psycopg2 import Error
from pathlib import Path
import numpy as np
from datetime import datetime


class Analysis:
    def __init__(self):
        '''Connect To Database'''
        print("Connect To Database")
        try:            
            # Connect to an existing database
            self.connection = psycopg2.connect(user='postgres',
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
                WHERE mrn = '{mrn}' \
                AND icd10='{icd10}' \
                AND tag='{tag}' \
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
    def get_event_date(self, mrn, icd10, tag, start_date):
        # Connect to DB
        cursor = self.connection.cursor()

        # Get Positive Event Date
        sql = f"SELECT DISTINCT obj->>'value' as date \
                FROM clinical_document.q_document, jsonb_array_elements(attribute) obj \
                WHERE mrn = '{mrn}' \
                AND icd10='{icd10}' \
                AND tag='{tag}' \
                AND (obj->>'name' = 'start_date' OR obj->>'name' = 'date') \
                AND obj->>'value' >= '{start_date}'\
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
                    WHERE mrn = '{mrn}' \
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
    
    def kaplan_meier(self, mrns, icd10, start_tag, event_tag):
        """
        Generate Kaplan Meier Curves
        mrns: <list>
        start_tag: <string>
        event_tag: <string>: 
        """
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
            event_date, event_ = self.get_event_date(mrn, icd10, event_tag, start_date)
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