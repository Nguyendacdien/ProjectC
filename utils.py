import json

def get_pages(count, limit):
    #Get Number of Pages to Paginate
    pages = count // limit
    if count % limit > 0:
        if count % limit <= limit:
            pages += 1
            return pages
        else:
            pages += 2
    else:
        return pages

def generate_pagination_links(offset, limit, pages, webpage, search, username):
    #Generates Pagination Links
    if webpage == 'search':
        url_list = ['/' + username + '/' + webpage + '/' + search  + '?limit=' + str(limit) + '&offset=0']
        for i in range(pages):
            url_list.append('/' + username + '/'  + webpage + '/' + search  + '?limit=' + str(limit) + '&offset=' + str(offset + limit))
            offset += limit
    else:
        url_list = ['/'+ username + '/'  + webpage + '?limit=' + str(limit) + '&offset=0']
        for x in range(pages):
            url_list.append('/'+ username + '/'  + webpage  + '?limit=' + str(limit) + '&offset=' + str(offset + limit))
            offset += limit
    return url_list
 
def get_countries():
    #Return a list of countries
    with open('data/countries.json') as j:
        loaded =json.load(j)
        country_list = []
        for i in loaded:
            country_list.append((i['name'], i['name']))
        return country_list

def increment_field(voteType, current):
    #Increment Field
    for x in current:
        if x.keys() == [voteType]:
            new_vote = x[voteType] + 1
            return int(new_vote)

def search_name(formName, names):
    for name in names:
        if name['name'].title() == formName.title():
            return True
    return False
        


    
