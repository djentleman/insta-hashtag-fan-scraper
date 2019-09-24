# Insta Hashtag Fan Scraper
scrapes locations of fans of an instagram hashtag (no API key required)

## Usage

To scrape metadata and location data associated with fans of a hashtag, just run the `scrape_fan_locations.py` script with the hastag as the first positional argument. 
The data is output to a csv file called `<hashtag>_output.csv`. 
for instance:

```
scrape_fan_locations.py italy
```

would produce a csv file called `italy_output.csv` containing data about the posts of the users who posted using the #italy hashtag.

The current dimensions that are exported are as follows:

 - _hashtag_ (Search level): The hashtag used in the search, in the above example this would be `italy`.
 - _user\_id_ (User level): The user id of the instagram user who posted the picture
 - _username_ (User level): The username of the instagram user who posted the picture
 - _followers_ (User level): The number of followers the user has
 - _full\_name_ (User level): The full name of the user
 - _profile\_pic\_url_ (User level): The profile picture url of the user
 - _address_ (Picture level): The address of the picture - this is used to forward geocode the lat/lng
 - _lat_ (Picture level): The Latitude of the picture
 - _lng_ (Picture Level): The Longitude of the picture
 - _post\_id_ (Picture level): the id of the picture
 - _post\_text_ (Picture level): the text associated with the picture
 - _post\_img\_url_ (Picture level): the url of the image
 - _post\_timestamp_ (Picture level): the timestamp of the post
 - _post\_likes_ (Picture level): the number of likes the image has
 - _post\_comments_ (Picture level): the number of comments the image has
 - _post\_views_ (Picture level): the number of views the post has (if its a video, else null)

There are 3 different 'levels', the hashtag being search, the accounts (users) associated with that hashtag, and the posts those users made

## Method

This script is an instagram scraper aimed at producing a location dataset based on a specfic hashag.
It first scrapes the explore page for a hashtag, and builds a list of all users who posted something with that hashtag in the description. It then scrapes the account pages of all of these users, finding all of their geocoded pictures and getting any relevant information. 

It mainly exploits the `__a=1` get parameter, which returns the contents of any instagram page as a GraphQL Database. This doesn't work when scraping the account pages of instagram users (technically it does return data, it just doesn't pageinate properly), so for that part of the scrape the graphql endpoint is used.

