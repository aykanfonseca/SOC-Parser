'''Python program to scrape UC San Diego's Schedule of Classes. Created by Aykan Fonseca.'''

# Builtins
import sys
import time

# Pip install packages.
from bs4 import BeautifulSoup
from cachecontrol import CacheControl
from firebase import firebase
import requests

# Global Variables.
SESSION = CacheControl(requests.Session())

# A timestamp for the scrape in year-month-day-hour-minute.
TIMESTAMP = int(time.strftime("%Y%m%d%H%M"))

# Current year and next year but only the last two digits.
YEAR = int(time.strftime("%Y"))

# Example, if Year = 2018, then we would have: (18, 19, 17, 16, 15)
VALID_YEARS = (YEAR % 100, (YEAR + 1) % 100, (YEAR - 1) % 100, (YEAR - 2) % 100, (YEAR - 3) % 100)

# CAPE urls & User agent.
CAPE_URL = 'http://cape.ucsd.edu/responses/Results.aspx?'
BASE_URL = 'http://cape.ucsd.edu/responses/'
USER_AGENT = {'User-agent': 'Mozilla/5.0'}

# URL to the entire list of classes.
SOC_URL = 'https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudentResult.htm?page='

# FIREBASE_DB = "https://schedule-of-classes-8b222.firebaseio.com/"
FIREBASE_DB = "https://winter-2019-rd.firebaseio.com/"

def get_quarters():
    '''Gets all the quarters listed in drop down menu, and return the most recent one.'''

    print("Getting quarters.")

    quarters = SESSION.get(SOC_URL, stream=True)
    q_soup = BeautifulSoup(quarters.content, 'lxml').findAll('option')

    # Gets the rest of the quarters for the years specified in VALID_YEARS.
    return [x['value'] for x in q_soup if x['value'][2:] in str(VALID_YEARS)]


def get_data_from_db(quarter):
    """ Retrieves the teachers & course number data to firebase."""

    print("Getting information from database.")

    database = firebase.FirebaseApplication(FIREBASE_DB)

    path = "/quarter/" + quarter + "/"

    return database.get(path, None)


def get_teacher_and_classes(data):
    """ Gets a mapping of courses to the teachers that teach them."""

    print("Identifying teacher - course mappings.")

    keys_exclude = {'restrictions', 'code', 'description', 'title', 'prerequisites', 'units', 'dei', 'key', 'waitlist', 'podcast'}

    course_teacher_mapping = {}
    for i in data:
        # Example: CSE 100
        course = i

        # Example: A00, B00.
        sections = list(set(data[i].keys()) - keys_exclude)

        # Example: [Gary Gillespie, Rick Ord]
        teachers = {data[i][section]['section'][1]['name'] for section in sections}

        course_teacher_mapping[course] = teachers

    return course_teacher_mapping


def get_distributions_for_course(course, teachers, print_errors):
    """ Gets all the averages for a particular course on a per teacher basis."""

    course_data = {}
    for teacher in teachers:
        department, _, code = course.partition(' ')

        url = 'http://cape.ucsd.edu/responses/Results.aspx?courseNumber=' + department + '+' + code + '&name=' + teacher.replace(' ', '%20')
        
        post = SESSION.get(url, headers=USER_AGENT, stream=True)
        soup = BeautifulSoup(post.content, 'lxml')
        tr_elements = soup.findAll('tr')

        master = []
        # No CAPEs for this professor.
        if 'No CAPEs have been submitted that match your search criteria.' in soup.text:
            if (print_errors):
                print "No CAPES"
                print "\n"
        else:
            for row in tr_elements:
                # Some simple validation checks.
                try:
                    row_class = row['class'][0]

                    if row_class == 'even' or row_class == 'odd':
                        # We now have a valid row. This will include every table cell after and including the Term. Thus it specifically doesn't include the instructor or course.
                        formatted_row = ((list(row)[1:])[:-1])[2:]

                        year_of_term = int(formatted_row[0].text[-2:])

                        # Data is not too old.
                        if (year_of_term in VALID_YEARS):
                            # Contains the last three cells, specifically, the study hours, the average grade expected, and the average grade received. The next variable, text_data contains the text info.
                            relevant_data_in_row = formatted_row[5:]
                            text_data = [data.text.strip('\n') for data in relevant_data_in_row]

                            # We want full data. Ignore incomplete data.
                            if "N/A" not in text_data:
                                hours = text_data[0]
                                avg_grade_expected = text_data[1].partition('(')[2].partition(')')[0]
                                avg_grade_received = text_data[2].partition('(')[2].partition(')')[0]
                                master.append([hours, avg_grade_expected, avg_grade_received])
                            else:
                                if (print_errors):
                                    print "NOT WELLFORMED DATA. HAS N/A."
                    else:
                        if (print_errors):
                            print "ISN'T A VALID ROW."
                except:
                    continue

        hours = 0
        grade_expected = 0
        grade_received = 0
        count = 0

        for lst in master:
            hours += float(lst[0])
            grade_expected += float(lst[1])
            grade_received += float(lst[2])

            count += 1
    
        # Takes the averages if any and stores the data based on teacher into a dictionary.
        if count != 0:
            course_data[teacher] = [round(hours / count, 2), round(grade_expected / count, 2), round(grade_received / count, 2)]
        else:
            course_data[teacher] = []

    return course_data


def update_db(quarter, data):
    """ Updates nodes with grade distribution data."""

    print("Updating information in database.")

    keys_exclude = {'restrictions', 'code', 'description', 'title', 'prerequisites', 'units', 'dei', 'key', 'waitlist', 'podcast'}
    database = firebase.FirebaseApplication(FIREBASE_DB)

    for course in data:
        path = "/quarter/" + quarter + "/" + str(course) + "/"

        course_node = database.get(path, None)

        sections = list(set(course_node.keys()) - keys_exclude)

        for section in sections:
            section_path = "/quarter/" + quarter + "/" + str(course) + "/" + section + "/"

            # Example, A00 node or B00 node.
            section_info = database.get(section_path, None)

            # # Updates node when node exists. If not, don't add because we won't use.
            if (section_info != None): 
                name = section_info['section'][1]['name']

                relevant_data = (data[course])[name]

                if (relevant_data != []):
                    database.put(section_path, 'cape', {'study': relevant_data[0], 'expected': relevant_data[1], 'received': relevant_data[2]})
                else:
                    database.put(section_path, 'cape', "N/A")


def reset_db():
    """ Deletes data to firebase."""

    print("Wiping information in database.")

    database = firebase.FirebaseApplication(FIREBASE_DB)

    database.delete('/quarter', None)


def main():
    currentQuarterNeeded = True
    print_errors = False
    upload_data = True
    reset_db = False

    if (currentQuarterNeeded):
        # Quarter. Listed like SP18 or FA17.
        quarter = get_quarters()[0]
    else:
        # Harcode needed quarter.
        quarter = "SP18"

    data = get_data_from_db(quarter)

    course_teacher_mapping = get_teacher_and_classes(data)

    print("Parsing Data! Will take some time.")
    all_course_data = {}
    for course, teachers in course_teacher_mapping.items():
        all_course_data[course] = get_distributions_for_course(course, teachers, print_errors)

    if (reset_db):
        reset_db()

    if (upload_data):
        update_db(quarter, all_course_data)

if __name__ == '__main__':
    main()