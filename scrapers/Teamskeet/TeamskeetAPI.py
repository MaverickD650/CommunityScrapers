import json
import os
import pathlib
import re
import sys
from datetime import datetime

# to import from a parent directory we need to add that directory to the system path
csd = os.path.dirname(
    os.path.realpath(__file__))  # get current script directory
parent = os.path.dirname(csd)  #  parent directory (should be the scrapers one)
sys.path.append(
    parent
)  # add parent dir to sys path so that we can import py_common from there

try:
    import py_common.log as log
except ModuleNotFoundError:
    print("You need to download the folder 'py_common' from the community repo! (CommunityScrapers/tree/master/scrapers/py_common)", file=sys.stderr)
    sys.exit()

try:
    import cloudscraper
except ModuleNotFoundError:
    print("You need to install the cloudscraper module. (https://pypi.org/project/cloudscraper/)", file=sys.stderr)
    print("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install cloudscraper", file=sys.stderr)
    sys.exit()

def save_json(api_json, url):
    try:
        if sys.argv[1] == "logJSON":
            try:
                os.makedirs(DIR_JSON)
            except FileExistsError:
                pass  # Dir already exist
            api_json['url'] = url
            filename = os.path.join(DIR_JSON, str(api_json['id'])+".json")
            with open(filename, 'w', encoding='utf-8') as file:
                json.dump(api_json, file, ensure_ascii=False, indent=4)
    except IndexError:
        pass


USERFOLDER_PATH = str(pathlib.Path(__file__).parent.parent.absolute())
DIR_JSON = os.path.join(USERFOLDER_PATH, "scraperJSON","Teamskeet")


# Not necessary but why not ?
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0'


fragment = json.loads(sys.stdin.read())
if fragment["url"]:
    scene_url = fragment["url"]
else:
    log.error('You need to set the URL (e.g. teamskeet.com/movies/*****)')
    sys.exit(1)

if "teamskeet.com/movies/" not in scene_url:
    log.error('The URL is not from a Teamskeet URL (e.g. teamskeet.com/movies/*****)')
    sys.exit(1)

scene_id = re.sub('.+/', '', scene_url)
if not scene_id:
    log.error("Error with the ID ({})\nAre you sure that the end of your URL is correct ?".format(scene_id))
    sys.exit(1)
use_local = 0
json_file = os.path.join(DIR_JSON, scene_id+".json")
if os.path.isfile(json_file):
    log.debug("Using local JSON...")
    use_local = 1
    with open(json_file, encoding="utf-8") as json_file:
        scene_api_json = json.load(json_file)
else:
    log.debug("Asking the API...")
    api_url = f"https://store2.psmcdn.net/ts-elastic-d5cat0jl5o-videoscontent/_doc/{scene_id}"
    headers = {
        'User-Agent': USER_AGENT,
        'Origin': 'https://www.teamskeet.com',
        'Referer': 'https://www.teamskeet.com/'
    }
    scraper = cloudscraper.create_scraper()
    # Send to the API
    r = ""
    try:
        r = scraper.get(api_url, headers=headers, timeout=(3, 5))
    except:
        log.error("An error has occurred with the page request")
        log.error(f"Request status: `{r.status_code}`")
        log.error("Check your TeamskeetAPI.log for more details")
        with open("TeamskeetAPI.log", 'w', encoding='utf-8') as f:
            f.write(f"Scene ID: {scene_id}\n")
            f.write(f"Request:\n{r.text}")
        sys.exit(1)
    try:
        scene_api_json_check = r.json().get('found')
        if scene_api_json_check:
            scene_api_json = r.json()['_source']
        else:
            log.error('Scene not found (Wrong ID?)')
            sys.exit(1)

    except:
        if "Please Wait... | Cloudflare" in r.text:
            log.error("Protected by Cloudflare. Retry later...")
        else:
            log.error("Invalid page content")
        sys.exit(1)

# Time to scrape all data
scrape = {}
scrape['title'] = scene_api_json.get('title')
dt = scene_api_json.get('publishedDate')
if dt:
    dt = re.sub(r'T.+', '', dt)
    date = datetime.strptime(dt, '%Y-%m-%d')
    scrape['date'] = str(date.date())
scrape['details'] = scene_api_json.get('description')
scrape['studio'] = {}
scrape['studio']['name'] = scene_api_json['site'].get('name')
scrape['performers'] = [{"name": x.get('modelName')}
                        for x in scene_api_json.get('models')]
scrape['tags'] = [{"name": x} for x in scene_api_json.get('tags')]
scrape['image'] = scene_api_json.get('img')

if use_local == 0:
    save_json(scene_api_json, scene_url)
print(json.dumps(scrape))
