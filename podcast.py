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

    table = soup.findAll('tr')

    # A list of lists where each list is contains: title of course, professor, authentication, and podcast link.
    podcasts = []

    for item in table:
        sub = []

        parsed = str(item.text.strip()).partition('\n')

        # Append the Class name & Professor.
        sub.append(parsed[0])
        sub.append(parsed[2])

        # True / False value if log in authentication is required. Assume false. 
        authentication = False

        try:
            if (str(item['class'][0]) == authentication):
                authentication = True
        except KeyError:
            pass
        
        # Append the authentication.
        sub.append(authentication)

        # Podcast link.
        try:
            if (str(item.find('a')['class'][0]) == "PodcastLink"):
                sub.append(podcast_url + str(item.find('a')['href']))
                podcasts.append(sub)
        except:
            # If there's no podcast link, skip adding it to the podcasts list.
            continue

    # Natural sort the classes based on first item in list for each list in list of lists. 
    podcasts.sort(key=natural_sort_key)

    # Print data.
    for i in podcasts:
        print i

    end = time.time()

    print("\nTime taken: " + str(end - start))

if __name__ == '__main__':
    main()