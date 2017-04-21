'''Python program to scrape UC San Diego's Schedule of Classes.'''

# Builtins.
import re
import itertools
import time
from datetime import datetime

# Pip install packages.
import requests
from bs4 import BeautifulSoup
from cachecontrol import CacheControl

# Starts the timer.
start = time.time()

# Current year (cYear) and next year (nYear) but only the last two digits.
year = datetime.now().year
cY = repr(year % 100)
nY = repr(year + 1 % 100)

# URL to the entire list of classes.
soc_url = 'https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudentResult.htm?page='

# URL to get the 3 - 4 letter department codes.
subjects_url = 'http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html'

# Input data besides classes.
post_data = {
    'loggedIn': 'false',
    'instructorType': 'begin',
    'titleType': 'contain',
    'schDay': ['M', 'T', 'W', 'R', 'F', 'S'],
    'schedOption1': 'true',
    'schedOption2': 'true',
    'schStartTime': '12:00',
    'schStartAmPm': '0',
    'schEndTime': '12:00',
    'schEndAmPm': '0',
    'tabNum': 'tabs-sub',
    'schedOption1Dept': 'true',
    'schedOption2Dept': 'true',
    'schDayDept': ['M', 'T', 'W', 'R', 'F', 'S'],
    'schStartTimeDept': '12:00',
    'schStartAmPmDept': '0',
    'schEndTimeDept': '12:00',
    'schEndAmPmDept': '0'
}


def get_quarters(URL, current=None):
    '''Gets all the quarters listed in drop down menu.'''

    quarters = requests.get(URL)
    qSoup = BeautifulSoup(quarters.content, 'lxml')

    # Gets the rest of the quarters for the year.
    quarters = []
    for option in qSoup.findAll('option'):
        # Value will take the form 'FA16' or 'SP15' for example.
        value = option['value']
        if value[2:] in (cY, nY):
            # Current quarter by optional parameter.
            if current:
                return value
            else:
                quarters.append(value)

    return quarters


def get_subjects():
    '''Gets all the subjects listed in select menu.'''

    # Makes the post request for the Subject Codes.
    subjectPost = requests.post(subjects_url, stream=True)
    subjectSoup = BeautifulSoup(subjectPost.content, 'lxml')

    # Gets all the subject Codes for post request.
    subjects = {}
    for x in subjectSoup.findAll('td'):
        if (len(x.text) <= 4):
            if str(x.text).isupper():
                subjects.setdefault('selectedSubjects', []).append(str(x.text))

    return subjects


def update_term():
    '''Updates post request using current quarter by calling get_quarter.'''

    quarter = get_quarters(soc_url, current='yes')
    term = {'selectedTerm': quarter}
    # term = {'selectedTerm': "SP17"}
    # term = {'selectedTerm': "WI17"}
    post_data.update(term)
    return quarter


def update_subjects():
    '''Updates the post request and subjects selected by parsing URL2.'''

    post_data.update(get_subjects())
    # post_data.update({'selectedSubjects' : 'CSE'})
    # post_data.update({'selectedSubjects' : 'BENG'})


def update_post():
    '''Calls updateSubjects & update_term to add to post data.'''

    update_subjects()
    quarter = update_term()
    return quarter


def get_data(url, page):
    '''Parses the data of one page.'''

    pstart = time.time()

    # Occasionally, the first call will fail.
    try:
        post = s.get(url, stream=True)
    except requests.exceptions.HTTPError:
        post = s.get(url, stream=True)

    # Parse the response into HTML and look only for tr tags.
    soup = BeautifulSoup(post.content, 'lxml')
    tr_elements = soup.findAll('tr')

    # This will contain all the classes for a single page.
    SOC = []

    # Used to switch departments.
    for item in tr_elements:
        try:
            parsedText = str(" ".join(item.text.split()).encode('utf-8'))
        except UnicodeEncodeError:
            return "error"

        # Changes department if tr_element looks like a department header.
        try:
            if item.td:
                # We have a 3-4 department code in our tag.
                if (" )" in item.td.h2.text):
                    currentDept = str(item.td.h2.text.partition("(")[2].partition(" ")[0])

        # Not on a department, so skip it, and use previous currentDept.
        except AttributeError:
            pass

        # The header of each class: units, department, course number, etc..
        if ('Units' in parsedText):
            SOC.append(' NXC')
            add = parsedText.partition(' Prereq')[0]
            SOC.append((currentDept + " " + add))

        # Exam Information, Section information, and Email.
        else:
            # # Assume there isn't an item class.
            itemClass = ''

            # Check if there is an item  class.
            try:
                itemClass = str(item['class'][0])
            except KeyError:
                pass

            if (itemClass == 'nonenrtxt'):
                if (('FI' or 'MI') in parsedText):
                    SOC.append((parsedText))

            elif (itemClass == 'sectxt'):
                if 'Cancelled' not in parsedText:
                    # Assume there is no email.
                    email = 'No Email'

                    # Check if there is an email.
                    try:
                        email = str(item.find('a')['href'])[7:]
                    except TypeError:
                        pass

                    SOC.append(('....' + parsedText))
                    SOC.append((email))
            else:
                pass

    pend = time.time()
    print ("Completed Page {} of {}").format(page, numberPages)
    times.append(pend - pstart)
    return SOC


def parse_list(ls):
    '''Parses the list elements into their readable values to store.'''

    # Components of a class.
    Header, Email, Final, Midterm, Section = [], [], [], [], []

    number_regex = re.compile(r'\d+')
    days_regex = re.compile(r'[A-Z][^A-Z]*')

    for item in ls:
        # Find class information.
        if 'Units' in item:
            # Department.
            C_department = item.partition(' ')[0]
            Header.append(C_department)
            num_loc = number_regex.search(item).start()

            # Course Number.
            C_number = item[num_loc:].partition(' ')[0]

            Header.append(C_number)

            # Temporary variable to make lines shorter and save time.
            temp = item.partition('( ')

            # Name.
            Header.append(temp[0][len(C_number) + 1 + num_loc: -1])

            # Units.
            Header.append(temp[2].partition(')')[0])

            # Restrictions.
            if num_loc != len(C_department) + 1:

                Header.append(item[len(C_department) + 1: num_loc - 1])
            else:
                Header.append('No Restrictions')

        # TODO: What happens with two emails? Need to modify getData as well.

        # Find Email Info.
        if (('No Email' in item) or ('.edu' in item)) and (item.strip() not in Email):
            if (len(Email) == 0) or ('No Email' not in item):
                Email.append(item.strip())

        # Finds Section Info.
        if ('....' in item):
            num_loc = number_regex.search(item).start()
            S = item.split(' ')

            # ID.
            if (num_loc == 4):
                Section.append(item[4:10].strip())
                S = S[1:]
            else:
                Section.append('Blank')
                S[0] = S[0][4:]

            # Meeting type and Section.
            Section.extend(S[0:2])

            # Readjust the list.
            S = S[2:]

            # Days: so MWF would have separate entries, M, W, F.
            if S[0] != 'TBA':
                temp = days_regex.findall(S[0])
                # Day 1, Day 2, and Day 3.
                if len(temp) == 3:
                    Section.extend(temp)
                if len(temp) == 2:
                    Section.extend(temp)
                    Section.append('Blank')
                if len(temp) == 1:
                    Section.append(temp[0])
                    Section.append('Blank')
                    Section.append('Blank')
                S = S[1:]
            else:
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')

            # The times.
            if S[0] != 'TBA':
                Section.extend(S[0].partition('-')[::2])
                S = S[1:]
            else:
                Section.append('Blank')
                Section.append('Blank')

            # Adjust list in the case that the time was given, but not the building or room.
            if (len(S) > 1) and (S[0] == S[1] == 'TBA'):
                S = S[1:]

            # The Building.
            if S[0] != 'TBA':
                Section.append(S[0])
                S = S[1:]
            else:
                Section.append('Blank')

            # The Room.
            if S[0] != 'TBA':
                Section.append(S[0])
            else:
                Section.append('Blank')

            # Readjust the list.
            S = ' '.join(S[1:])

            # Find position of first number in string.
            try:
                num_loc = number_regex.search(S).start()
            except AttributeError:
                num_loc = 0

            # Handles Teacher, Seats Taken, and Seats Offered.
            if 'FULL' in S:
                temp = S.find('FULL')
                if (temp == 0):
                    Section.append('Blank')
                    Section.append('Blank')
                    Section.append('Blank')
                else:
                    if 'Staff' in S:
                        Section.append('Staff')
                        Section.append('Blank')
                        Section.append('Blank')
                    else:
                        name = S[:temp].strip()

                        # First name.
                        Section.append(name.partition(',')[0])
                        # Last name.
                        Section.append(name.partition(',')[2].strip().split(' ')[0])

                        # Middle name.
                        try:
                            Section.append(name.partition(',')[2].strip().split(' ')[1])
                        except:
                            Section.append('Blank')

                # Adjust String.
                S = S[temp:]

                # Seats Taken.
                Section.append(S[:(S.find(')')+1)])

                # Seats Available.
                Section.append(S[(S.find(')')+2):])

            elif 'Unlim' in S:
                if 'Staff ' in S:
                    # First, Last, middle names.
                    Section.append('Staff')
                    Section.append('Blank')
                    Section.append('Blank')
                    # Seat Information.
                    Section.append('Unlim')
                    Section.append('Unlim')
                else:
                    name = S[:S.find('Unlim')-1]

                    # First name.
                    Section.append(name.partition(',')[0])
                    # Last name.
                    Section.append(name.partition(',')[2].strip().split(' ')[0])

                    # Middle name.
                    try:
                        Section.append(name.partition(',')[2].strip().split(' ')[1])
                    except IndexError:
                        Section.append('Blank')

                    # Seat information.
                    Section.append('Unlim')
                    Section.append('Unlim')

            # Name and seat information.
            elif num_loc != 0:
                name = S[:num_loc].strip()

                # First name.
                if (name.partition(',')[0] != ''):
                    Section.append(name.partition(',')[0])
                else:
                    Section.append('Blank')

                # Last name.
                if (name.partition(',')[2].strip().split(' ')[0] != ''):
                    Section.append(name.partition(',')[2].strip().split(' ')[0])
                else:
                    Section.append('Blank')

                # Middle name.
                try:
                    Section.append(name.partition(',')[2].strip().split(' ')[1])
                except:
                    Section.append('Blank')

                temp = S[num_loc:].strip().split(' ')
                Section.append(temp[0])
                Section.append(temp[1])

            # Just staff and no seat information.
            elif (S.strip() == 'Staff'):
                Section.append('Staff')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')

            # Name and no seat information.
            elif (num_loc == 0):
                name = S.strip()

                # First name.
                if (name.partition(',')[0] != ''):
                    Section.append(name.partition(',')[0])
                else:
                    Section.append('Blank')

                # Last name.
                if (name.partition(',')[2].strip().split(' ')[0] != ''):
                    Section.append(name.partition(',')[2].strip().split(' ')[0])
                else:
                    Section.append('Blank')

                # Middle name.
                try:
                    Section.append(name.partition(',')[2].strip().split(' ')[1])
                except:
                    Section.append('Blank')

                # Blanks for both the seat information.
                Section.append('Blank')
                Section.append('Blank')

            # No name and no seat information
            else:
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')

        # Finds Final / Midterm Info.
        if ('FI' or 'MI') in item:
            Exam = item.split(' ')

            temp = []

            temp.extend(Exam[1:3])

            # The start and end times.
            if Exam[3] != 'TBA':
                temp.extend(Exam[3].partition('-')[::2])
            else:
                temp.append('TBA')
                temp.append('TBA')

            temp.extend(Exam[4:])

            if ('FI' in item):
                Final = temp
            else:
                Midterm = temp

    return [Header, Section, Email, Midterm, Final]


def format_list(ls):
    '''Formats the result list into the one we want.'''

    # Flattens list of lists into list.
    parsedSOC = (item for sublist in ls for item in sublist)

    # Groups list into lists of lists based on a delimiter word.
    parsedSOC = (list(y) for x, y in itertools.groupby(parsedSOC, lambda z: z == ' NXC') if not x)

    # Sorts list based on sorting criteria.
    return (x for x in parsedSOC if (len(x) > 2 and 'Cancelled' not in x))


def write_data(ls):
    '''Writes the data to a file.'''

    with open("dataset2.txt", "w") as openFile:
        for item in ls:
            for i in item:
                openFile.write(str(i))

            openFile.write("\n")
            openFile.write("\n")


def main():
    '''The main function.'''

    global s, numberPages
    global times
    times = []

    # XXX: 0
    check0 = time.time()

    # Update postData and request session for previously parsed classes.
    quarter = update_post()

    # XXX: A
    check1 = time.time()

    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0'
    s = CacheControl(s)

    # TODO : BOTTLE NECK
    post = s.post(soc_url, data=post_data, stream=True)
    soup = BeautifulSoup(post.content, 'lxml')

    # XXX: B
    check2 = time.time()

    # The total number of pages to parse and the current page starting at 1.
    numberPages = int(soup.text[re.search(r"Page", soup.text).start()+12:].partition(')')[0])

    # Prints which quarter we are fetching data from and how many pages.
    print("--Fetching data for {} from {} pages--\n").format(quarter, numberPages)

    # XXX: C
    check3 = time.time()

    pages = [x for x in xrange(1, numberPages + 1)]
    urls = (soc_url + str(x) for x in pages)

    # Gets the data using urls.
    results = (get_data(x, y) for (x, y) in itertools.izip(urls, pages))

    # XXX: D
    check4 = time.time()

    # Format list into proper format
    results = (format_list(results))

    # XXX: E
    check5 = time.time()

    # Parses items in list into usable portions.
    final = [parse_list(item) for item in results]

    # XXX: F
    check6 = time.time()

    # Does the printing of the timing statements.
    print('This is the break down of code timing:\n')
    print('\t' + '0 --  ' + str(check0 - start))
    print('\t' + 'A --  ' + str(check1 - start))
    print('\t' + 'B --  ' + str(check2 - start))
    print('\t' + 'C --  ' + str(check3 - start))
    print('\t' + 'D --  ' + str(check4 - start))
    print('\t' + 'E --  ' + str(check5 - start))
    print('\t' + 'F --  ' + str(check6 - start) + '\n')

    print float(sum(times)) / max(len(times), 1)

    return final


if __name__ == '__main__':
    Final = main()

    # Ends the timer.
    end = time.time()

    # Writes the data to a file.
    write_data(Final)

    # Prints how long it took for program to run with checkpoints.
    print('\n' + str(end - start))
