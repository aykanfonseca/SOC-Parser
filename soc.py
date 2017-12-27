'''Python program to scrape UC San Diego's Schedule of Classes. Created by Aykan Fonseca.'''

# Builtins
import itertools
import re
import sys
import time
from collections import defaultdict

# Pip install packages.
from bs4 import BeautifulSoup
from cachecontrol import CacheControl
from firebase import firebase
import requests

# Global Variables.
SESSION = CacheControl(requests.Session())
NUMBER_PAGES = 0

# A timestamp for the scrape in year-month-day-hour-minute.
TIMESTAMP = int(time.strftime("%Y%m%d%H%M"))

# Current year and next year but only the last two digits.
YEAR = int(time.strftime("%Y"))

VALID_YEARS = (YEAR % 100, YEAR + 1 % 100)

# URL to the entire list of classes.
SOC_URL = 'https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudentResult.htm?page='

# URL to get the 3 - 4 letter department codes.
SUBJECTS_URL = 'http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html'

CATALOG_URL = 'http://www.ucsd.edu/catalog/courses/'

# Input data besides classes.
POST_DATA = {'loggedIn': 'false', 'instructorType': 'begin', 'titleType': 'contain',
             'schDay': ['M', 'T', 'W', 'R', 'F', 'S'], 'schedOption1': 'true',
             'schedOption2': 'true'}


def get_quarters():
    '''Gets all the quarters listed in drop down menu.'''

    quarters = SESSION.get(SOC_URL, stream=True)
    q_soup = BeautifulSoup(quarters.content, 'lxml').findAll('option')

    # Gets the rest of the quarters for the years specified in VALID_YEARS.
    return [x['value'] for x in q_soup if x['value'][2:] in str(VALID_YEARS)]


def get_subjects():
    '''Gets all the subjects listed in select menu.'''

    subject_post = requests.post(SUBJECTS_URL)
    soup = BeautifulSoup(subject_post.content, 'lxml').findAll('td')

    return {'selectedSubjects': [i.text for i in soup if len(i.text) <= 4]}


def setup():
    '''Updates post request with quarter and subjects selected. Also gets NUMBER_PAGES.'''

    # Global Variable.
    global NUMBER_PAGES

    # The subjects to parse.
    # POST_DATA.update({'selectedTerm': get_quarters()[0]})
    POST_DATA.update({'selectedTerm': "FA17"})
    # POST_DATA.update({'selectedTerm': "SA17"})

    # The quarter to parse.
    POST_DATA.update(get_subjects())

    # print(len(get_subjects()['selectedSubjects']))
    POST_DATA.update({'selectedSubjects': ['BILD', 'CSE']})

    # The total number of pages to parse.
    post = str(SESSION.post(SOC_URL, data=POST_DATA, stream=True).content)
    NUMBER_PAGES = int(re.search(r"of&nbsp;([0-9]*)", post).group(1))

    return POST_DATA['selectedTerm']


def get_data(url_page_tuple):
    '''Parses the data of all pages.'''

    # Cache NUMBER_PAGES & SESSION to avoid calls to global vars.
    master = []
    total = NUMBER_PAGES
    s = SESSION

    for url, page in url_page_tuple:
        # Occasionally, the first call will fail.
        try:
            post = s.get(url, stream=True)
        except requests.exceptions.HTTPError:
            post = s.get(url, stream=True)

        # Parse the response into HTML and look only for tr tags.
        tr_elements = BeautifulSoup(post.content, 'lxml').findAll('tr')

        # This will contain all the classes for a single page.
        page_list = []

        for item in tr_elements:
            parsed_text = str(" ".join(item.text.split()).encode('utf_8'))

            # Changes department if tr_element looks like a department header.
            try:
                current_dept = str(
                    re.search(r'\((.*?)\)', item.td.h2.text).group(1))
            except AttributeError:
                pass

            # The header of each class: units, department, course number, etc..
            if 'Units' in parsed_text:
                page_list.append(' NXC')
                page_list.append(current_dept + " " + parsed_text.partition(' Prereq')[0])

            # Exam Information & Section information (and Email).
            else:
                try:
                    item_class = item['class'][0]

                    if 'nonenrtxt' == item_class and any(x in parsed_text for x in ('FI', 'MI')):
                        page_list.append('****' + parsed_text)

                    elif 'sectxt' == item_class and 'Cancelled' not in parsed_text:
                        page_list.append('....' + parsed_text)

                        # Check for an email.
                        try:
                            page_list.append(item.find('a')['href'][7:])
                        except TypeError:
                            page_list.append('No Email')

                except KeyError:
                    pass

        print("Completed Page {} of {}".format(page, total))
        master.append(page_list)

    return master


def format_list(lst):
    '''Formats the result list into the one we want.'''

    # Flattens list of lists into list.
    parsed = (item for sublist in lst for item in sublist)

    # Groups list into lists of lists based on a delimiter word.
    regrouped = (list(y) for x, y in itertools.groupby(
        parsed, lambda z: z == ' NXC') if not x)

    # Sorts list based on sorting criteria.
    non_canceled = (x for x in regrouped if len(x) > 2 and 'Cancelled' not in x)

    # Gets rid of classes without 6-digit identifications.
    return (x for x in non_canceled if re.findall(r"\D(\d{6})\D", str(x)))


def parse_list(results):
    '''Parses the list elements into their readable values to store.'''

    parsed = []
    teacher_class = {}

    for lst in results:
        # Components of a class.
        header = {}
        email = set()
        final = {}
        midterm = {}
        seats = {}
        all_sections = {}
        counter = 0

        number_regex = re.compile(r'\d+')

        for item in lst:
            # Find class information.
            if 'Units' in item:
                c_department = item.partition(' ')[0]
                num_loc = number_regex.search(item).start()
                c_number = item[num_loc:].partition(' ')[0]
                temp = item.partition('( ')

                # Department, Course Number, Name, and Units.
                header["department"] = c_department
                header["course number"] = c_number
                header["course name"] = temp[0][len(
                    c_number) + 1 + num_loc: -1]
                header["units"] = temp[2].partition(')')[0]

                # Restrictions.
                header["restrictions"] = "No Restrictions"

                if num_loc != len(c_department) + 1:
                    header["restrictions"] = item[len(
                        c_department) + 1: num_loc - 1]

            # TODO: What happens with two emails? Modify getData as well. Change Email to set().

            # Find Email Info.
            if ('No Email' in item) or ('.edu' in item):
                email.add(item.strip())

            # Finds Section Info.
            if '....' in item:
                section = {}

                counter += 1

                number_regex = re.compile(r'\d+')
                days_regex = re.compile(r'[A-Z][^A-Z]*')
                num_loc = number_regex.search(item).start()

                to_parse = item.split(' ')
                section_num = "section " + str(counter)

                # ID.
                if num_loc == 4:
                    section[section_num + " id"] = item[4:10].strip()
                    to_parse = to_parse[1:]
                else:
                    section[section_num + " id"] = 'Blank'
                    to_parse[0] = to_parse[0][4:]

                # Meeting type and Section.
                section[section_num + " meeting type"] = to_parse[0]
                section[section_num + " number"] = to_parse[1]

                # Readjust the list.
                to_parse = to_parse[2:]

                # Days: so MWF would have separate entries, M, W, F. Max = 5, assumed Blank.
                if to_parse[0] != 'TBA':
                    temp = days_regex.findall(to_parse[0])
                    section[section_num + " day 1"] = 'Blank'
                    section[section_num + " day 2"] = 'Blank'
                    section[section_num + " day 3"] = 'Blank'
                    section[section_num + " day 4"] = 'Blank'
                    section[section_num + " day 5"] = 'Blank'

                    # Changes whatever is available.
                    try:
                        section[section_num + " day 1"] = temp[0]
                        section[section_num + " day 2"] = temp[1]
                        section[section_num + " day 3"] = temp[2]
                        section[section_num + " day 4"] = temp[3]
                        section[section_num + " day 5"] = temp[4]
                    except IndexError:
                        pass

                    to_parse = to_parse[1:]
                else:
                    pass

                # The times. Assume TBA.
                section[section_num + " start time"] = "TBA"
                section[section_num + " end time"] = "TBA"
                section[section_num + " start time am"] = True
                section[section_num + " end time am"] = True

                if to_parse[0] != 'TBA':
                    time_tuples = to_parse[0].partition('-')[::2]

                    section[section_num + " start time"] = time_tuples[0][:-1]
                    section[section_num + " end time"] = time_tuples[1][:-1]

                    section[section_num +
                            " start time am"] = False if time_tuples[0][-1] != "a" else True
                    section[section_num +
                            " end time am"] = False if time_tuples[1][-1] != "a" else True

                    to_parse = to_parse[1:]

                # Adjust list because time was given, but not building or room.
                if (len(to_parse) > 1) and (to_parse[0] == to_parse[1] == 'TBA'):
                    to_parse = to_parse[1:]

                # The Building. Assume Blank.
                section[section_num + " building"] = 'Blank'

                if to_parse[0] != 'TBA':
                    section[section_num + " building"] = to_parse[0]
                    to_parse = to_parse[1:]

                # The Room.
                section[section_num +
                        " room"] = to_parse[0] if to_parse[0] != 'TBA' else 'Blank'

                # Readjust the list.
                to_parse = ' '.join(to_parse[1:])

                # Find position of first number in string.
                try:
                    num_loc = number_regex.search(to_parse).start()
                except AttributeError:
                    num_loc = 0

                # Assume Blank.
                section[section_num + " name"] = 'Blank'
                section[section_num + " seats taken"] = 'Blank'
                section[section_num + " seats available"] = 'Blank'

                # Note for seat enrollments:
                # A. WAITLIST FULL, the seats taken is the amount over plus the seats available.
                # B. UNLIMITED seats, the seats taken is max integer.
                # C. None of those, the seats taken is a positive interger.

                # Handles Teacher, Seats Taken, and Seats Offered.
                if 'FULL' in to_parse:
                    temp = to_parse.find('FULL')

                    if temp != 0:
                        if 'Staff' in to_parse:
                            section[section_num + " name"] = 'Staff'
                        else:
                            section[section_num + " name"] = to_parse[:temp - 1]

                    # Adjust String.
                    to_parse = to_parse[temp:]

                    taken = int(to_parse[to_parse.find(
                        '(') + 1:to_parse.find(')')])
                    taken += int(to_parse[(to_parse.find(')') + 2):])

                    # Seat Information: Amount of seats taken (WAITLIST Full).
                    seat_tracking = (taken, int(to_parse[(to_parse.find(')') + 2):]))
                    section[section_num + " seats taken"] = taken
                    section[section_num +
                            " seats available"] = int(to_parse[(to_parse.find(')') + 2):])

                elif 'Unlim' in to_parse:
                    if 'Staff ' in to_parse:
                        section[section_num + " name"] = 'Staff'
                    else:
                        section[section_num + " name"] = to_parse[:to_parse.find('Unlim') - 1]

                    # Seat information. -1 indicates unlimited seats.
                    seat_tracking = (sys.maxint, sys.maxint)
                    section[section_num + " seats taken"] = sys.maxint
                    section[section_num + " seats available"] = sys.maxint

                # Name and seat information.
                elif num_loc != 0:
                    section[section_num + " name"] = to_parse[:num_loc].strip()

                    temp = to_parse[num_loc:].strip().split(' ')

                    # Amount of seats taken (has seats left over.
                    seat_tracking = (int(temp[0]), int(temp[1]))
                    section[section_num + " seats taken"] = int(temp[0])
                    section[section_num + " seats available"] = int(temp[1])

                # Just staff and no seat information.
                elif to_parse.strip() == 'Staff':
                    section[section_num + " name"] = 'Staff'

                # Name and no seat information. Blanks for both the seat information.
                elif num_loc == 0 and ',' in to_parse:
                    section[section_num + " name"] = to_parse.strip()

                # No name but seat info - think discussion sections without teacher name.
                elif num_loc == 0 and to_parse:
                    try:
                        temp = to_parse.split(' ')

                        seat_tracking = (int(temp[0]), int(temp[1]))
                        section[section_num + " seats taken"] = int(temp[0])
                        section[section_num + " seats available"] = int(temp[1])

                    except IndexError:
                        print("ERROR")
                        sys.exit()

                # Add section to all_section dictionary.
                all_sections[counter] = section

            # Finds Final / Midterm Info.
            if '****' in item:
                exam = item.split(' ')
                exam_info = {}

                exam_info["date"] = exam[1]
                exam_info["day"] = exam[2]

                # Assume they are problematic and then change them if not.
                exam_info["start time"] = "TBA"
                exam_info["end time"] = "TBA"
                exam_info["start time am"] = True
                exam_info["end time am"] = True

                # The start and end times.
                if exam[3] != 'TBA':
                    time_tuples = exam[3].partition('-')[::2]

                    exam_info["start time"] = time_tuples[0][:-1]
                    exam_info["end time"] = time_tuples[1][:-1]

                    if time_tuples[0][-1] != "a":
                        exam_info["start time am"] = False
                    if time_tuples[1][-1] != "a":
                        exam_info["end time am"] = False

                if 'FI' in item:
                    final = exam_info
                else:
                    midterm = exam_info

        # Uses first 6-digit id as key.
        key = int(re.findall(r"\D(\d{6})\D", str(lst))[0])
        seats = {TIMESTAMP: seat_tracking}

        temp = {"section": all_sections, "midterm": midterm}
        temp["final"] = final
        temp["seats"] = seats
        temp["key"] = key
        temp.update(header)

        parsed.append(temp)

    return parsed


def check_collision(lst):
    '''Compares all keys and makes sure they are unique.'''

    seen = set()
    differences = []

    for item in lst:
        if item["key"] in seen:
            differences.append(item["key"])
        else:
            seen.add(item["key"])

    # This will print the sizes. If collision, they will be different.
    print("")
    print("---Diagonistic Information---")
    print("  - # of keys: " + str(len(seen) + len(differences)))
    print("  - # of unique keys: " + str(len(seen)))
    print("  - Note: We want them to be the same.")
    print("")

    # This code will print the keys that collided in a list.
    if differences:
        print(differences)
        return True

    return False


def group_list(lst):
    ''' Groups same classes together in a dictionary with the key as the class dept + name
        and the value being a list of the various sections of this class. I.e: A00, B00, etc.'''

    composite = {}

    for i in lst:
        key =  i["department"] + " " + i["course number"]

        if key not in composite:
            composite[key] = {}

        composite[key][i["section"][1]["section 1 number"]] = i

    return composite


def department_group(dict):
    ''' Groups the various classes by department.'''

    departments = {}

    for i in dict:
        dept = i.partition(" ")[0]

        if dept not in departments:
            departments[dept] = {}

        departments[dept][i] = dict[i]

    return departments


def prepare_for_db(dict):
    """ Groups teachers and classes they teach as well as makes some data 
        (course name, department, etc) first level in our db schema for easy access."""

    grouped_by_teachers = defaultdict(list)

    for i in dict:
        first_section = dict[i][dict[i].iterkeys().next()]
        code = first_section['department'] + " " + first_section['course number']
        title = first_section['course name']
        key = first_section['key']
        units = first_section['units']
        waitlist = 'true'
        for j in dict[i].keys():
            for k in dict[i][j]['section'].keys():
                name = dict[i][j]['section'][k]['section ' + str(k) + ' name']

                if name not in ("", "Staff", "Blank"):
                    grouped_by_teachers[name.replace('.', "")].append(i)

            first, second = dict[i][j]['seats'][dict[i][j]['seats'].keys()[0]]

            if first < second:
                waitlist = 'false'

            del dict[i][j]['department']
            del dict[i][j]['course number']
            del dict[i][j]['units']
            del dict[i][j]['course name']
            del dict[i][j]['key']

        dict[i]['waitlist'] = waitlist
        dict[i]['code'] = code
        dict[i]['title'] = title
        dict[i]['key'] = key
        dict[i]['units'] = units

    return dict, grouped_by_teachers


def write_to_db(dictionary, quarter):
    """ Adds data to firebase."""

    database = firebase.FirebaseApplication("https://schedule-of-classes-8b222.firebaseio.com/")

    path = "/quarter/" + quarter + "/"

    for key in dictionary:
        database.put(path, key, dictionary[key])


def write_teachers_to_db(dictionary, quarter):
    """ Adds data to firebase."""

    database = firebase.FirebaseApplication("https://schedule-of-classes-8b222.firebaseio.com/")

    path = "/quarter/" + quarter + " teachers" + "/"

    for key in dictionary:
        database.put(path, key, dictionary[key])


def main():
    '''The main function.'''
    print(sys.version)

    # Update POST_DATA and sets NUMBER_PAGES to parse.
    quarter = setup()

    # Prints which quarter we are fetching data from and how many pages.
    print("Fetching data for {} from {} pages\n".format(quarter, NUMBER_PAGES))

    # Gets the data using urls. Input is url, page number pairings.
    raw_data = get_data(((SOC_URL + str(x), x) for x in range(1, NUMBER_PAGES + 1)))

    # Format list into proper format.
    formatted_data = format_list(raw_data)

    # Parses items in list into usable portions.
    finished = parse_list(formatted_data)

    # If our unique ID keys aren't for some reason unique, we want to stop.
    if check_collision(finished):
        print("ERROR: Hashing algorithm encountered a collision!")
        sys.exit()

    # Groups by class.
    grouped = group_list(finished)
 
    # Groups by department.
    # grouped_by_department = department_group(grouped)

    # Groups teachers and classes and prepares the grouped dictionary for upload by modifiying it.
    grouped, grouped_by_teachers = prepare_for_db(grouped)

    # Writes the data to the db.
    write_to_db(grouped, quarter)

    # Writes the teacher data to the db.
    write_teachers_to_db(grouped_by_teachers, quarter)


if __name__ == '__main__':
    main()
