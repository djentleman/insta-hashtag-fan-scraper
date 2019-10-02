from datetime import datetime
import requests
import sys
import json
import geocoder
import pandas
import time

hashtag_page_lim = 10 # number of pages of the 'explore' page to scrape
user_page_lim = 5 # number of pages of each account to scrape

request_headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8,ja;q=0.7',
    'cache-control': 'max-age=0',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
}

def make_request(url):
    for i in range(5):
        try:
            resp = requests.get(url, headers=request_headers)
            return resp.json()
        except requests.exceptions.ConnectionError as e:
            print('Connection Error...')
            time.sleep(1)
        except json.decoder.JSONDecodeError as e:
            print('JSON Decode Error...')
            pass
    return None


def get_users(hashtag):
    users = []
    # loop over all posts for hashtag
    end_cursor = ''
    for i in range(hashtag_page_lim):
        print(f'scraping page {i} of {hashtag}')
        base_url = f'https://www.instagram.com/explore/tags/{hashtag}/?__a=1&max_id={end_cursor}'
        resp = make_request(base_url)
        if resp == None:
            continue
        hashtag_posts = resp['graphql']['hashtag']['edge_hashtag_to_media']['edges']
        for post in hashtag_posts:
            # get the shortcode
            post_shortcode = post['node']['shortcode']
            # using the shortcode get the uploader
            post_uploader = make_request(f'https://www.instagram.com/p/{post_shortcode}/?__a=1')
            if post_uploader == None:
                continue
            post_uploader = post_uploader['graphql']['shortcode_media']['owner']
            users.append((post_uploader['id'], post_uploader['username']))
        page_info = resp['graphql']['hashtag']['edge_hashtag_to_media']['page_info']
        if not page_info['has_next_page']:
            break
        if page_info['end_cursor'] == None:
            break
        # cursor for next page
        end_cursor = page_info['end_cursor']

    # deduplicate users
    users = list(set(users))
    return users

def get_user_metadata(user):
    print(f'Scraping {user} metadata...')
    user_url = f'https://www.instagram.com/web/search/topsearch/?query={user}'
    print(user_url)
    user_resp = make_request(user_url)
    if user_resp == None or len(user_resp['users']) == 0:
        return (
            None,
            None,
            None
        )
    #followers = user_resp['users'][0]['user']['follower_count']
    full_name = user_resp['users'][0]['user']['full_name']
    profile_pic = user_resp['users'][0]['user']['profile_pic_url']
    return (
        #followers,
        full_name,
        profile_pic
    )

def get_post_metadata(post):
    post_id = post['node']['id']
    post_text = post['node']['edge_media_to_caption']['edges'][0]['node']['text'] if len(post['node']['edge_media_to_caption']['edges']) > 0 else ''
    post_text = post_text.replace('\n', '  ')
    post_img_url = post['node']['display_url']
    post_timestamp = str(datetime.fromtimestamp(post['node']['taken_at_timestamp']))
    post_likes = post['node']['edge_media_preview_like']['count']
    post_comments = post['node']['edge_media_to_comment']['count']
    post_views = post['node']['video_view_count'] if post['node']['is_video'] else None
    return (
        post_id,
        post_text,
        post_img_url,
        post_timestamp,
        post_likes,
        post_comments,
        post_views
    )

def get_data_from_users(users, hashtag):
    scraped_data = []
    try:
        for user_id, user in users:
            print(user)
            user_metadata = get_user_metadata(user)
            end_cursor = ''
            for i in range(user_page_lim):
                print(f'Scrape Page {i} of {user}')
                user_url = f'https://www.instagram.com/graphql/query/?query_id=17888483320059182&id={user_id}&first=12&after={end_cursor}'
                print(user_url)
                user_resp = make_request(user_url)
                if user_resp == None or user_resp['data']['user'] == None:
                    continue
                user_post_data = user_resp['data']['user']['edge_owner_to_timeline_media']['edges']
                for post in user_post_data:
                    shortcode = post['node']['shortcode']
                    post_metadata = get_post_metadata(post)
                    resp = make_request(f'https://www.instagram.com/p/{shortcode}/?__a=1')['graphql']['shortcode_media']
                    # check if location is valid
                    if resp == None or resp.get('location') == None or resp.get('location').get('address_json') == None:
                        continue
                    resp = json.loads(resp['location']['address_json'])
                    address = ', '.join([resp['street_address'], resp['city_name'], resp['zip_code'], resp['country_code']])
                    loc = geocoder.arcgis(address)
                    if loc.latlng == None:
                        continue
                    print(address, loc.latlng)
                    scraped_data.append(
                        [
                            hashtag,
                            user_id,
                            user,
                            *user_metadata,
                            address,
                            loc.latlng[0],
                            loc.latlng[1],
                            *post_metadata
                        ]
                    )
                    time.sleep(0.2)
                page_info = user_resp['data']['user']['edge_owner_to_timeline_media']['page_info']
                if not page_info['has_next_page']:
                    break
                if page_info['end_cursor'] == None:
                    break
                # cursor for next page
                end_cursor = page_info['end_cursor']
    except KeyboardInterrupt as e:
        print("Keyboard interrupt detected, halting...")
        pass
    return scraped_data


def write_output(scraped_data, hashtag):
    if len(scraped_data) == 0:
        print('cant find location data')
    else:
        df = pandas.DataFrame(scraped_data)
        df.columns = [
            'hashtag',
            'user_id',
            'username',
            #'followers',
            'full_name',
            'profile_pic_url',
            'address',
            'lat',
            'lng',
            'post_id',
            'post_text',
            'post_img_url',
            'post_timestamp',
            'post_likes',
            'post_comments',
            'post_views'
        ]
        df.to_csv(f'{hashtag}_output.csv')

def main():
    hashtag = sys.argv[1]
    users = get_users(hashtag)
    scraped_data = get_data_from_users(users, hashtag)
    write_output(scraped_data, hashtag)


if __name__ == "__main__":
    main()
