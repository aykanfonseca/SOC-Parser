from bs4 import BeautifulSoup 
import requests
import re
import time

def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, s[0])]

def main():
    start = time.time()

    podcast_url = "https://podcast.ucsd.edu"

    post = requests.get(podcast_url)
    soup = BeautifulSoup(post.content, 'lxml')

    # A list of lists where each list is contains: title of course, professor, authentication, and podcast link.
    podcasts = []

    table = soup.find('div', {'class': 'quarter'}).findAll('tr')

    for item in table:
        sub = []

        # # Append the Class name & Professor.
        sub.append(item.findAll('td')[0].text.strip().partition('-')[0].strip())
        sub.append(item.findAll('td')[1].text.strip())

        # True / False value if log in authentication is required. Assume false. 
        authentication = False

        if (item.findAll('td')[0].div != None):
            authentication = True
        
        # Append the authentication.
        sub.append(authentication)

        # Podcast link.
        sub.append(item.findAll('td')[2].findAll('a')[0]['href'][:-4])

        podcasts.append(sub)

    # Natural sort the classes based on first item in list for each list in list of lists. 
    podcasts.sort(key=natural_sort_key)

    # Print data.
    for i in podcasts:
        print i[0]
        print i[1]
        print i[2]
        print i[3]
        print "\n"

    end = time.time()

    print("\nTime taken: " + str(end - start))

if __name__ == '__main__':
    main()