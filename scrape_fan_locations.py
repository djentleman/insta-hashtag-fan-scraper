import requests
import sys
import json
import geocoder
import pandas
import time

def make_request(url):
    for i in range(5):
        try:
            resp = requests.get(url)
            return resp
        except requests.exceptions.ConnectionError as e:
            print('Connection Error...')
            time.sleep(1)
    return None


hashtag = sys.argv[1]

users = []
# loop over all posts for hashtag
hashtag_page_lim = 10
user_page_lim = 5
end_cursor = ''
for i in range(hashtag_page_lim):
    print(f'scraping page {i} of {hashtag}')
    base_url = f'https://www.instagram.com/explore/tags/{hashtag}/?__a=1&max_id={end_cursor}'
    resp = make_request(base_url).json()
    hashtag_posts = resp['graphql']['hashtag']['edge_hashtag_to_media']['edges']
    for post in hashtag_posts:
        # get the shortcode
        post_shortcode = post['node']['shortcode']
        # using the shortcode get the uploader
        try:
            post_uploader = make_request(f'https://www.instagram.com/p/{post_shortcode}/?__a=1').json()['graphql']['shortcode_media']['owner']
            users.append((post_uploader['id'], post_uploader['username']))
        except json.decoder.JSONDecodeError as e:
            continue
    page_info = resp['graphql']['hashtag']['edge_hashtag_to_media']['page_info']
    if not page_info['has_next_page']:
        break
    if page_info['end_cursor'] == None:
        break
    # cursor for next page
    end_cursor = page_info['end_cursor']

# deduplicate users
users = list(set(users))
locations = []
try:
    for user_id, user in users:
        print(user)
        end_cursor = ''
        for i in range(user_page_lim):
            print(f'Scrape Page {i} of {user}')
            user_url = f'https://www.instagram.com/graphql/query/?query_id=17888483320059182&id={user_id}&first=12&after={end_cursor}'
            print(user_url)
            try:
                user_resp = make_request(user_url).json()
                if user_resp['data']['user'] == None:
                    continue
                user_post_data = user_resp['data']['user']['edge_owner_to_timeline_media']['edges']
            except json.decoder.JSONDecodeError as e:
                continue
            for post in user_post_data:
                shortcode = post['node']['shortcode']
                try:
                    resp = make_request(f'https://www.instagram.com/p/{shortcode}/?__a=1').json()['graphql']['shortcode_media']
                except json.decoder.JSONDecodeError as e:
                    continue
                # check if location is valid
                if resp.get('location') == None or resp.get('location').get('address_json') == None:
                    continue
                resp = json.loads(resp['location']['address_json'])
                address = ', '.join([resp['street_address'], resp['city_name'], resp['zip_code'], resp['country_code']])
                loc = geocoder.arcgis(address)
                if loc.latlng == None:
                    continue
                print(address, loc.latlng)
                locations.append([hashtag, user, address, loc.latlng[0], loc.latlng[1]])
                time.sleep(0.2)
            page_info = user_resp['data']['user']['edge_owner_to_timeline_media']['page_info']
            if not page_info['has_next_page']:
                break
            if page_info['end_cursor'] == None:
                break
            # cursor for next page
            end_cursor = page_info['end_cursor']

except KeyboardInterrupt as e:
    pass

if len(locations) == 0:
    print('cant find location data')
else:
    df = pandas.DataFrame(locations)
    df.columns = ['hashtag', 'username', 'address', 'lat', 'lng']
    df.to_csv(f'{hashtag}_output.csv')
