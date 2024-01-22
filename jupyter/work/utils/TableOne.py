from datetime import datetime, timedelta
import numpy as np

def age_distribution(database, mrns, reference_tag, reference_occurance=0):
    '''
    Gathers age distribution for a set of mrns
    parameters
    database: <Database>; Database instance
    mrns: list<string>; list of mrns to loop through
    reference_tag: str; name of icd10 and tag (eg. 'c61:external-radiation')
    reference_occurance: int; 
    returns
    ages: list<float>; list of ages in years
    
    '''
    ages = []
    for mrn in mrns:
        #print(f"{mrn=}")
        age = None
        p = database.Patient(mrn = mrn)
        
        # Does dob exist
        if reference_tag in p.icd10_tags:
            #print(f"{reference_tag=}")
            
            # Get Reference Date
            reference_date = p[reference_tag]
            # timepoint or timespan
            #print(f"{reference_date=}")
            try:
                reference_date = reference_date.date[reference_occurance]
            except AttributeError:
                reference_date = reference_date.start_date[reference_occurance]
            reference_date = datetime.strptime(reference_date, '%Y-%m-%d')
    
            # Does dob exist
            if 'dob' in p.icd10_tags and p['dob'].date[0]:
                date_of_birth = p['dob'].date[0]
                date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d')
                age = (reference_date-date_of_birth).days/365.
        ages.append(age)
        del p
    return ages

def tag_distribution_by_occurance(database, mrns, icd10_tag, attribute, occurance=0):
    '''
    Gathers tag distribution for a set of mrns
    parameters
    database: <Database>; Database instance
    mrns: list<string>; list of mrns to loop through
    icd10_tag: str; name of icd10 and tag (eg. 'c61:external-radiation')
    attribute_name: str; name of attribute
    occurance: int; 
    returns
    ages: list<float>; list of ages in years
    '''
    values = []
    for mrn in mrns:
        value = None
        p = database.Patient(mrn = mrn)
        
        # Does dob exist
        if icd10_tag in p.icd10_tags:
            # Get Value
            try:
                value = p[icd10_tag][attribute][occurance]
            except KeyError:
                value = None
        values.append(value)
        del p
    return values

def tag_distribution_by_association(database, mrns, icd10_tag, attribute, reference_icd10_tag, reference_occurance=0):
    '''
    Gathers tag distribution for a set of mrns, the tag chosen is time closest to the reference tag
    parameters
    database: <Database>; Database instance
    mrns: list<string>; list of mrns to loop through
    icd10_tag: str; name of icd10 and tag (eg. 'c61:external-radiation')
    reference_icd10_tag: str; name of icd10 and tag (eg. 'c61:external-radiation')
    reference_occurance: int; 
    returns
    ages: list<float>; list of ages in years
    
    '''
    values = []
    for mrn in mrns:
        p = database.Patient(mrn = mrn)
        # Does reference tag exist        
        if reference_icd10_tag in p.icd10_tags:
            # Get Reference Date
            reference = p[reference_icd10_tag]
            # timepoint or timespan
            try:
                reference_date = reference.date[0]
            except AttributeError:
                reference_date = reference.start_date[reference_occurance]
            reference_date = datetime.strptime(reference_date, '%Y-%m-%d')
        else:
            #print(f"mrn:{mrn}; reference_icd10_tag{reference_icd10_tag}")
            values.append(None)
            continue
        
        # Does dob exist
        if icd10_tag in p.icd10_tags:
            # timepoint or timespan
            try:
                date_list = p[icd10_tag].date.to_list()
            except AttributeError:
                date_list = p[icd10_tag].start_date.to_list()
            # Get Index of closest
            # Convert to datetime
            date_list = [datetime.strptime(tag_date, '%Y-%m-%d') for tag_date in date_list]
            date_list = np.abs([(tag_date-reference_date).days for tag_date in date_list])
            closest_index = np.argsort(date_list)[0]
            value = p[icd10_tag][attribute][closest_index]
            values.append(value)
        else:
            values.append(None)

        del p
    return values
