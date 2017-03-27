from bs4 import BeautifulSoup
from datetime import datetime
import time
import requests, itertools, re

# Starts the timer.
start = time.time()

# Relevant Year Data for current year (cYear) and next year (nYear) but only the last two digits.
year = datetime.now().year
cY = repr(year % 100)
nY = repr(year + 1 % 100)

# This is the URL to the entire list of classes.
SOC = 'https://act.ucsd.edu/scheduleOfClasses/scheduleOfClassesStudentResult.htm?page='
Subjects = 'http://blink.ucsd.edu/instructors/courses/schedule-of-classes/subject-codes.html'

# Input data besides classes.
post_data = {
    'loggedIn': 'false', 'instructorType': 'begin', 'titleType': 'contain',
    'schDay': ['M', 'T', 'W', 'R', 'F', 'S'], 'schedOption1': 'true',
    'schedOption2': 'true', 'schStartTime': '12:00', 'schStartAmPm': '0',
    'schEndTime': '12:00', 'schEndAmPm': '0', 'tabNum': 'tabs-sub',
    'schedOption1Dept': 'true', 'schedOption2Dept': 'true',
    'schDayDept': ['M', 'T', 'W', 'R', 'F', 'S'], 'schStartTimeDept': '12:00',
    'schStartAmPmDept': '0', 'schEndTimeDept': '12:00', 'schEndAmPmDept': '0'}

# Gets all the quarters listed in drop down menu.
def get_quarters(URL, current=None):
    quarters = requests.post(URL)
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

# Gets all the subjects listed in select menu.
def get_subjects():
    # Makes the post request for the Subject Codes.
    subjectPost = requests.post(Subjects)
    subjectSoup = BeautifulSoup(subjectPost.content, 'lxml')

    # Gets all the subject Codes for post request.
    subjects = {}
    for x in subjectSoup.findAll('td'):
        if (len(x.text) <= 4):
            if str(x.text).isupper():
                subjects.setdefault('selectedSubjects', []).append(str(x.text))

    return subjects

# Updates term and post request using the current quarter by calling get_current_quarter.
def update_term():
    quarter = get_quarters(SOC, current='yes')
    term = {'selectedTerm': quarter}
    post_data.update(term)
    return quarter

# Updates the post request and subjects selected by parsing URL2.
def update_subjects():
    # postData.update(getSubjects())
    post_data.update({'selectedSubjects' : 'CSE'})

# Calls updateSubjects & update_term to add to post data.
def update_post():
    update_subjects()
    quarter = update_term()
    return quarter

# Parses the data of one page.
def get_data(url, page):
    # Occasionally, the first call will fail.
    try:
        post = s.get(url)
    except:
        post = s.get(url)

    soup = BeautifulSoup(post.content, 'lxml')
    tr_elements = soup.findAll('tr')
    span_elements = soup.findAll('span', {'class': 'centeralign'})

    # Gets the list of departments in the current page.
    departments = (str(x.text.partition("(")[2].partition(" ")[0]) for x in span_elements if ' )' in x.text)

    SOC = []

    # Used to switch departments.
    for item in tr_elements:
        parsedText = str(" ".join(item.text.split()))

        # Next one if you find selected text b/c new subject is shown.
        if all(x in parsedText for x in ['Course Number', 'ID']):
            currentDept = next(departments)

        # The header of each class: units, department, course number, etc..
        if ('Units' in parsedText):
            add = parsedText.partition(' Prereq')[0]
            SOC.extend((' NXC', currentDept + ' ' + add))

        # Final / Midterm Information, Section information (Discussion and Labs), and Email.
        else:
            # Assume there isn't an item class.
            itemClass = ''

            # Check if there is an item  class.
            try:
                itemClass = str(item['class'][0])
            except KeyError:
                pass

            if (itemClass == 'nonenrtxt'):
                if (('FI' or 'MI') in parsedText):
                    SOC.append((parsedText))

            if (itemClass == 'sectxt'):
                if 'Cancelled' not in parsedText:
                    # Assume there is no email.
                    email = 'No Email'

                    # Check if there is an email.
                    try:
                        email = str(item.find('a')['href'])[7:]
                    except TypeError:
                        pass

                    # SOC.append(email)
                    SOC.extend(('....' + parsedText, email))

    print ("Completed Page {} of {}").format(page, numberPages)
    return SOC

# Parses the list elements into their readable values to store.
def parse_list(ls):
    # Components of a class.
    Header, Email, Final, Midterm, Section = [], [], [], [], []

    for item in ls:
        # Find class information.
        if 'Units' in item:
            # Department.
            C_department = item.partition(' ')[0].strip()
            Header.append(C_department)
            num_loc = re.search(r'\d+', item).start()

            # Course Number.
            C_number = item[num_loc:].partition(' ')[0].strip()
            Header.append(C_number)

            # Name.
            Header.append(item.partition('( ')[0][len(C_number) + 1 + num_loc:].strip())

            # Units.
            Header.append(item.partition('( ')[2].partition('s)')[0]+'s')

            # Restrictions.
            if num_loc != len(C_department) + 1:
                Header.append(item[len(C_department) + 1:num_loc].strip())
            else:
                Header.append('No Restrictions')
        pass

        # TODO : What happens if there are two emails? Need to modify getData as well.

        # Find Email Info.
        if (('No Email' in item) or ('.edu' in item)) and (item.strip() not in Email):
            if (len(Email) == 0) or ('No Email' not in item):
                Email.append(item.strip())
        pass

        # Finds Section Info.
        if ('....' in item):
            num_loc = re.search(r'\d+', item).start()
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
                temp = re.findall('[A-Z][^A-Z]*', S[0])
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
                num_loc = re.search(r'\d+', S).start()
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
                    except:
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
            elif S.strip() == 'Staff':
                Section.append('Staff')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')
                Section.append('Blank')

            # Name and no seat information.
            elif num_loc == 0:
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
        pass

        # Finds Final Info.
        if 'FI' in item:
            F = item.split(' ')

            # Date and Day.
            Final.extend(F[1:3])

            # The start and end times.
            if F[3] != 'TBA':
                Final.extend(F[3].partition('-')[::2])
            else:
                Final.append('TBA')
                Final.append('TBA')

            # Building and Room.
            Final.extend(F[4:])
        pass

        # Finds Midterm Info.
        if 'MI' in item:
            M = item.split(' ')

            # Date and Day.
            Midterm.extend(M[1:3])

            # The start and end times.
            if M[3] != 'TBA':
                Midterm.extend(M[3].partition('-')[::2])
            else:
                Midterm.append('TBA')
                Midterm.append('TBA')

            # Building and Room.
            Midterm.extend(M[4:])
        pass

    return [Header, Section, Email, Midterm, Final]

# Formats the result list into the one we want
def format_list(ls):
    # # Flattens list of lists into list.
    parsedSOC = [item for sublist in ls for item in sublist]

    # Spliting a list into lists of lists based on a delimiter word.
    parsedSOC = [list(y) for x, y in itertools.groupby(parsedSOC, lambda z: z == ' NXC') if not x]

    # Sorts list based on sorting criteria.
    return [x for x in parsedSOC if len(x) > 2 and not 'Cancelled' in x]

# The main function.
def main():
    global s, numberPages

    # Update postData and request session for previously parsed classes.
    update_post()

    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0'
    post = s.post(SOC, data=post_data)
    soup = BeautifulSoup(post.content, 'lxml')

    # The total number of pages to parse and the current page starting at 1.
    numberPages = int(soup.text[re.search(r"Page", soup.text).start()+12:].partition(')')[0])

    pages = [x for x in xrange(1, numberPages + 1)]
    urls = [SOC + str(x) for x in pages]

    # Gets the data using urls.
    results = [get_data(x,y) for (x,y) in itertools.izip(urls, pages)]

    # Format list into proper format
    results = format_list(results)

    # Parses items in list into usable portions.
    final = [parse_list(item) for item in results]

    # for item in final:
    #     print item
    #     print '\n'

    return final

# The main algorithm that employes functions to get the data.
if __name__ == '__main__':
    Final = main()

    with open("dataset.txt", "w") as file:
        for item in Final:
            for i in item:
                file.write(str(i))

            file.write("\n")
            file.write("\n")

    # Ends the timer.
    end = time.time()

    # Prints how long it took for program to run.
    print('\n' + str(end - start) )
