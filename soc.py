'''Python program to scrape UC San Diego'SESSION Schedule of Classes. Created by Aykan Fonseca.'''

# Builtins
import itertools
import re
import sys
import time

# Pip install packages.
from bs4 import BeautifulSoup
from cachecontrol import CacheControl
from firebase import firebase
import requests

print(sys.version)

# Global Variable.
SESSION = CacheControl(requests.Session())
NUMBER_PAGES = 0

# Create a timestamp for the start of scrape in year-month-day-hour-minute.
TIMESTAMP = int(time.strftime("%Y%m%d%H%M"))

# Current year and next year but only the last two digits.
YEAR = int(time.strftime("%Y"))
VALID_YEARS = (repr(YEAR % 100), repr(YEAR + 1 % 100))

# URL to the entire list of classes.
SOC_URL = 'https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudentResult.htm?page='

# URL to get the 3 - 4 letter department codes.
SUBJECTS_URL = 'http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html'

# Input data besides classes.
POST_DATA = {'loggedIn': 'false', 'instructorType': 'begin', 'titleType': 'contain',
             'schDay': ['M', 'T', 'W', 'R', 'F', 'S'], 'schedOption1': 'true',
             'schedOption2': 'true'}


def get_quarters(url, current=None):
    '''Gets all the quarters listed in drop down menu.'''

    quarters = SESSION.get(url, stream=True)
    q_soup = BeautifulSoup(quarters.content, 'lxml').findAll('option')

    # Gets the rest of the quarters for the year. For example, 'FA16' or 'SP15'.
    quarters = []
    for option in q_soup:
        if option['value'][2:] in VALID_YEARS:
            if current:
                return option['value']

            quarters.append(option['value'])

    return quarters


def get_subjects():
    '''Gets all the subjects listed in select menu.'''

    subject_post = requests.post(SUBJECTS_URL)
    soup = BeautifulSoup(subject_post.content, 'lxml').findAll('td')

    return {'selectedSubjects' : [i.text for i in soup if len(i.text) <= 4]}


def update_data():
    '''Updates post request with quarter and subjects selected.'''

    quarter = get_quarters(SOC_URL, current='yes')
    term = {'selectedTerm': quarter}
    POST_DATA.update(term)

    # POST_DATA.update(get_subjects())
    POST_DATA.update({'selectedSubjects': 'CSE'})

    return quarter


def get_data(tied):
    '''Parses the data of one page.'''

    master = []

    for url, page in tied:
        # Occasionally, the first call will fail.
        try:
            post = SESSION.get(url, stream=True)
        except requests.exceptions.HTTPError:
            post = SESSION.get(url, stream=True)

        # Parse the response into HTML and look only for tr tags.
        tr_elements = BeautifulSoup(post.content, 'lxml').findAll('tr')

        # This will contain all the classes for a single page.
        page_list = []

        for item in tr_elements:
            parsed_text = str(" ".join(item.text.split()).encode('utf_8'))

            # Changes department if tr_element looks like a department header.
            try:
                current_dept = str(re.search(r'\((.*?)\)', item.td.h2.text).group(1))
            except AttributeError:
                pass

            # The header of each class: units, department, course number, etc..
            if 'Units' in parsed_text:
                page_list.append((' NXC'))
                page_list.append(str(current_dept + " " + parsed_text.partition(' Prereq')[0]))

            # Exam Information, Section information, and Email.
            else:
                try:
                    item_class = str(item['class'][0])

                    if 'nonenrtxt' in item_class and ('FI' or 'MI') in parsed_text:
                        page_list.append(str(parsed_text))

                    elif 'sectxt' in item_class and 'Cancelled' not in parsed_text:
                        page_list.append(str('....' + parsed_text))

                        # Check if there is an email.
                        try:
                            page_list.append(str(item.find('a')['href'])[7:])
                        except TypeError:
                            page_list.append('No Email')

                except KeyError:
                    pass

        print ("Completed Page {} of {}".format(page, NUMBER_PAGES))
        master.append(page_list)

    return master


def parse_list_sections(section, tracker, item, counter):
    '''Parses the section information for parse_list.'''

    number_regex = re.compile(r'\d+')
    days_regex = re.compile(r'[A-Z][^A-Z]*')
    num_loc = number_regex.search(item).start()

    to_parse = item.split(' ')
    section_num = "section " + str(counter)

    # ID.
    if num_loc == 4:
        section[section_num + " ID"] = item[4:10].strip()
        to_parse = to_parse[1:]
    else:
        section[section_num + " ID"] = 'Blank'
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
        section[section_num + " start time am"] = False if time_tuples[0][-1] != "a" else True
        section[section_num + " end time am"] = False if time_tuples[1][-1] != "a" else True

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
    section[section_num + " room"] = to_parse[0] if to_parse[0] != 'TBA' else 'Blank'

    # Readjust the list.
    to_parse = ' '.join(to_parse[1:])

    # Find position of first number in string.
    try:
        num_loc = number_regex.search(to_parse).start()
    except AttributeError:
        num_loc = 0

    # Assume Blank.
    section[section_num + " firstname"] = 'Blank'
    section[section_num + " lastname"] = 'Blank'
    section[section_num + " middlename"] = 'Blank'
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
                section[section_num + " firstname"] = 'Staff'
            else:
                name = to_parse[:temp - 1].partition(',')

                # First name & last name.
                section[section_num + " firstname"] = name[0]
                section[section_num + " lastname"] = name[2][1:].split(' ')[0]

                # Middle name.
                try:
                    section[section_num + " middlename"] = name[2][1:].split(' ')[1]
                except IndexError:
                    pass

        # Adjust String.
        to_parse = to_parse[temp:]

        taken = int(to_parse[to_parse.find('(')+1:to_parse.find(')')])
        taken += int(to_parse[(to_parse.find(')')+2):])

        # Seat Information: Amount of seats taken (WAITLIST Full).
        tracker[TIMESTAMP] = taken
        section[section_num + " seats taken"] = taken
        section[section_num + " seats available"] = int(to_parse[(to_parse.find(')')+2):])

    elif 'Unlim' in to_parse:
        if 'Staff ' in to_parse:
            # First, Last, and middle names.
            section[section_num + " firstname"] = 'Staff'
        else:
            name = to_parse[:to_parse.find('Unlim')-1].partition(',')

            # First name & last name.
            section[section_num + " firstname"] = name[0]
            section[section_num + " lastname"] = name[2].strip().split(' ')[0]

            # Middle name.
            try:
                section[section_num + " middlename"] = name[2].strip().split(' ')[1]
            except IndexError:
                pass

        # Seat information. -1 indicates unlimited seats.
        tracker[TIMESTAMP] = sys.maxint
        section[section_num + " seats taken"] = sys.maxint
        section[section_num + " seats available"] = sys.maxint

    # Name and seat information.
    elif num_loc != 0:
        name = to_parse[:num_loc].strip().partition(',')

        # First name.
        if name[0] != '':
            section[section_num + " firstname"] = name[0]
        else:
            pass

        # Last name.
        if name[2].strip().split(' ')[0] != '':
            section[section_num + " lastname"] = name[2].strip().split(' ')[0]
        else:
            pass

        # Middle name.
        try:
            section[section_num + " middlename"] = name[2].strip().split(' ')[1]
        except IndexError:
            pass

        temp = to_parse[num_loc:].strip().split(' ')

        # Amount of seats taken (has seats left over.
        tracker[TIMESTAMP] = int(temp[0])
        section[section_num + " seats taken"] = int(temp[0])
        section[section_num + " seats available"] = int(temp[1])

    # Just staff and no seat information.
    elif to_parse.strip() == 'Staff':
        section[section_num + " firstname"] = 'Staff'

    # Name and no seat information. Blanks for both the seat information.
    elif num_loc == 0 and ',' in to_parse:
        name = to_parse.strip().partition(',')

        # First name.
        if name[0] != '':
            section[section_num + " firstname"] = name[0]
        else:
            pass

        # Last name.
        if name[2].strip().split(' ')[0] != '':
            section[section_num + " lastname"] = name[2].strip().split(' ')[0]
        else:
            pass

        # Middle name.
        try:
            section[section_num + " middlename"] = name[2].strip().split(' ')[1]
        except IndexError:
            pass

    # No name but seat info - think discussion sections without teacher name.
    elif num_loc == 0 and to_parse:
        try:
            temp = to_parse.split(' ')

            tracker[TIMESTAMP] = int(temp[0])
            section[section_num + " seats taken"] = int(temp[0])
            section[section_num + " seats available"] = int(temp[1])

        except IndexError:
            print("ERROR")
            sys.exit()

    # TODO: Add tracker information.


def check_collision_key(lst):
    '''Compares all keys and makes sure they are unique.'''

    seen = set()
    differences = []

    for item in lst:
        for i in item:
            if isinstance(i, int):
                if i in seen:
                    differences.append(i)
                else:
                    seen.add(i)

    # This will print the sizes. If collision, they will be different.
    print("---Diagonistic Information---")
    print("  - # of keys: " + str(len(seen) + len(differences)))
    print("  - # of unique keys: " + str(len(seen)))
    print("  - Note: We want them to be the same.")
    print("")

    # This code will print the keys that collided in a list.
    if differences:
        print(differences)
        return False

    return True


def generate_key(header, section, final):
    '''Gives a unique ID to use. If a disc. id, use it, else use lecture id.'''

    hashed = set(frozenset(header.items()) | frozenset(final.items()))
    hashed.add(section['section 1 number'])

    return hash(frozenset(hashed))


def parse_list(results):
    '''Parses the list elements into their readable values to store.'''

    parsed = []

    for lst in results:
        # Components of a class.
        header = {}
        email = []
        final = {}
        midterm = {}
        tracker = {}
        section = {}
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
                header["course name"] = temp[0][len(c_number) + 1 + num_loc: -1]
                header["units"] = temp[2].partition(')')[0]

                # Restrictions.
                header["restrictions"] = "No Restrictions"

                if num_loc != len(c_department) + 1:
                    header["restrictions"] = item[len(c_department) + 1: num_loc - 1]

            # TODO: What happens with two emails? Modify getData as well. Change Email to set().

            # Find Email Info.
            if (('No Email' in item) or ('.edu' in item)) and (item.strip() not in email):
                if (not email) or ('No Email' not in item):
                    email.append(item.strip())

            # Finds Section Info.
            if '....' in item:
                counter += 1
                parse_list_sections(section, tracker, item, counter)

            # Finds Final / Midterm Info.
            if ('FI' or 'MI') in item:
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

        key = generate_key(header, section, final)
        key_tracker = {key: [tracker]}

        # If you have a list of collision keys, put one here to determine the problematic classes.
        # if (key == -5895194357248003337):
        #     print(header, section, tracker)

        parsed.append([header, section, email, midterm, final, key_tracker, key])

    return parsed


def format_list(lst):
    '''Formats the result list into the one we want.'''

    # Flattens list of lists into list.
    parsed = (item for sublist in lst for item in sublist)

    # Groups list into lists of lists based on a delimiter word.
    parsed = (list(y) for x, y in itertools.groupby(parsed, lambda z: z == ' NXC') if not x)

    # Sorts list based on sorting criteria.
    return (x for x in parsed if len(x) > 2 and 'Cancelled' not in x)


def write_data(lst):
    '''Writes the data to a file.'''

    with open("tracking.txt", "w") as open_file2:
        with open("dataset3.txt", "w") as open_file:
            for item in lst:
                for i in item:
                    if isinstance(i, dict):
                        open_file2.write(str(i))
                        open_file2.write("\n")
                        open_file2.write("\n")
                    elif isinstance(i, int):
                        pass
                    else:
                        open_file.write(str(i))

                open_file.write("\n")
                open_file.write("\n")


def write_to_db(lst):
    """ Adds data to firebase."""

    database = firebase.FirebaseApplication("https://schedule-of-classes.firebaseio.com")

    path = "/Classes/quarter/SUMMER 2017/"

    for i in lst:
        key = i[-1]
        result = database.post(path + str(key), i[:-2])


def main():
    '''The main function.'''

    # Global Variable.
    global NUMBER_PAGES

    # Update postData and request session for previously parsed classes.
    quarter = update_data()

    post = SESSION.post(SOC_URL, data=POST_DATA, stream=True)

    # The total number of pages to parse.
    NUMBER_PAGES = int(re.search(r"of&nbsp;([0-9]*)", str(post.content)).group(1))

    # Prints which quarter we are fetching data from and how many pages.
    print("Fetching data for {} from {} pages\n".format(quarter, NUMBER_PAGES))

    # Gets the data using urls. Input is url, page number pairings.
    results = get_data(((SOC_URL + str(x), x) for x in range(1, NUMBER_PAGES + 1)))

    # Format list into proper format
    semi = format_list(results)

    # Parses items in list into usable portions.
    finished = parse_list(semi)

    # If our unique ID keys aren't for some reason unique, we want to stop.
    if check_collision_key(finished) is False:
        print("ERROR: Hashing algorithm encountered a collision!")
        sys.exit()

    # Writes the data to a file.
    # write_to_db(DONE)

    return finished

if __name__ == '__main__':
    main()
