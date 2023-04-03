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
            self.connection = psycopg2.connect(user='admin',#getpass.getpass(prompt='username:'),
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
    
    # Get Start Date
    def get_start_date(self, mrn, tag):
        # Connect to DB
        cursor = self.connection.cursor()

        sql_ = f"SELECT attribute->>'date' as date, attribute->>'start_date' as start_date, attribute->>'end_date' as end_date \
                  FROM clinical_document.q_document \
                  WHERE  \
                  mrn = '{mrn}' \
                  AND tag='{tag}' \
                  LIMIT 1;"
        cursor.execute(sql_)
        dates = np.array(cursor.fetchone()).flatten()
        # Remove None and covert to datetime
        dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates if date is not None]
        dates.sort()

        # Start Date Does Not Exist
        if len(dates) == 0:
            date =  None
        else:
            date = dates[0]

        # Close Cursor
        cursor.close()
        return date

      # Get Event Date
    
    def get_event_date(self, mrn, tag):
        # Connect to DB
        cursor = self.connection.cursor()

        # Get Positive Event Date
        sql_ = f"SELECT attribute->>'date' as date \
                  FROM clinical_document.q_document \
                  WHERE tag = '{tag}' AND mrn='{mrn}' \
                  ORDER BY attribute->>'date' ASC \
                  LIMIT 1;"
        cursor.execute(sql_)
        date = np.array(cursor.fetchone()).flatten()[0]

        if date != None:
            # Convert to datetime
            date = datetime.strptime(date, '%Y-%m-%d').date()
            # Event True tag
            event=True

        else:
            # If No positive Get Last Event
            sql_ = f"SELECT attribute->>'date' as date, attribute->>'start_date' as start_date, attribute->>'end_date' as end_date \
                  FROM clinical_document.q_document \
                  WHERE mrn = '{mrn}' \
                    AND (attribute->>'date' IS NOT NULL \
                    OR attribute->>'start_date' IS NOT NULL \
                    OR attribute->>'end_date' IS NOT NULL) \
                  ORDER BY attribute->>'date' DESC;"
            cursor.execute(sql_)
            dates = np.array(cursor.fetchall()).flatten()
            # Remove None and convert to datetime
            dates = [datetime.strptime(date, '%Y-%m-%d').date() for date in dates if date is not None and date != '']

            # Get last Occurance
            dates.sort()
            date = dates[-1]

            # Event is False
            event=False

        # Close Cursor
        cursor.close()
        return date, event
    
    def kaplan_meier(self, mrns, start_tag, event_tag):
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
            start_date = self.get_start_date(mrn, start_tag)
            #print(f"{start_date=}", flush=True)
            # Check if start date exists
            if start_date == None:
                remove_idx.append(idx)
                continue

            #print(f"{event=}", flush=True)
            event_date, event_ = self.get_event_date(mrn, event_tag)
            #print(f"{event_date=}", flush=True)

            durations.append((event_date - start_date).days)
            events.append(event_)
            #print(f"{mrn=}", f"{start_date=}", f"{event_date=}", f"{event=}", flush=True)

        # Remove MRNs without start event
        mrns = np.delete(mrns, remove_idx).tolist()
        #print(f"{durations=}", flush=True)
        #print(f"{events=}", flush=True)

        output = {'mrns':mrns, 'durations':durations, 'events':np.asarray(events).astype(int).tolist()}

        return output