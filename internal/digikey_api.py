# -*- coding: utf-8 -*-
#
# The state and configuration is kept in a file ~/.digi-key_api_state.json
# The file is expected to be in a valid JSON format and contain the following minimal contents on first execution
#
# Expected format:
#
# 	{
# 	"API_CLIENT_ID": "<MAGIC STRING>",
# 	"API_SECRET": "<SUPER SECRET MAGIC STRING>",
# 	"API_REDIRECT_URI": "https://localhost",
# 	"LOGIN_PASSWORD" : "<SUPER SECRET PASSWORD>",
# 	"LOGIN_NAME" : "<LESS SECRET LOGIN NAME>",
# 	"CONTEXT": { }
# 	}
import json
import os.path
import sys

import requests
from HTMLParser import HTMLParser
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from dependencies import DB_CONNECTION
from internal.models.db_models import APCategory


class MyHTMLParser(HTMLParser):
    """
	We use this to dig out the 'FORM' element out of the login form that we need to get past in order to get initial magic tokens.
	"""

    def __init__(self):
        HTMLParser.__init__(self)
        self.form_action = None
        return

    def handle_starttag(self, tag, attrs):
        if tag.upper() != "FORM":
            return
        for a in attrs:
            if a[0] == 'action':
                self.form_action = a[1]


"""
The file we keep our application state, configuration parameters, and super secret magic strings in.
"""
STATE_FILE = ".digi-key_api_state.json"

"""
The file we're going to be caching parametric information in.
"""
PARAMETRICS_FILE = ".digi-key_api_parametrics.json"

"""
The Digi-Key search API endpoint
"""
#
# This is the old, deprecated API
# API_PART_SEARCH_URI = "https://api.digikey.com/services/basicsearch/v1/search"

API_PART_SEARCH_URI = "https://api.digikey.com/services/partsearch/v2/keywordsearch"

"""
The host that we shuffle magic strings through in order to get access to the API
"""
SSO_HOST = "https://sso.digikey.com"

"""
Application state/context
"""
GLOBAL_CONTEXT = {}

PARAMETRICS_CACHE = {}

"""
If set by config file or command line parameters we output humorous debug information
"""
DEBUG_FLAG = False

CK_API_CLIENT_ID = "API_CLIENT_ID"
CK_API_SECRET = "API_SECRET"
CK_API_REDIRECT = "API_REDIRECT_URI"
CK_LOGIN_PASSWORD = "LOGIN_PASSWORD"
CK_LOGIN_NAME = "LOGIN_NAME"
CK_VERSION = "VERSION"
CK_DEBUG = "DEBUG"
CK_CONTEXT = "CONTEXT"
CK_CONTEXT_REF_TOK = "REFRESH_TOKEN"
CK_CONTEXT_ACC_TOK = "ACCESS_TOKEN"
CK_CONTEXT_EXP = "EXPIRES"
CK_CONTEXT_TS = "GEN_TIMESTAMP"

PC_ID = "Id"

DBG_IN_FILE = ""

CMD_ARGS = None


def get_context_file_name():
    """
        Returns the complete path to the program state and configuration file/
        @return: Full path to the state and configuration file
    """

    return os.path.join(os.path.expanduser("~"), STATE_FILE)


def load_global_context():
    """
        Loads the global program state and configuration from a JSON file.
        The function also performs basic sanity checking and will throw an exception if something is thought to be hinky.
        @raise ValueError: Raises a ValueError if a required bit is missing in the file.  Should only be of concern during the first invocation.
        @raise Exception: Passes along any exceptions from the 'open' call.
        @return: Nothing
    """

    global GLOBAL_CONTEXT
    global CONFIG_VERSION
    global DEBUG_FLAG

    try:
        with open(get_context_file_name(), "rt") as ctx_file:
            GLOBAL_CONTEXT = json.load(ctx_file)
    except Exception as e:
        print(sys.stderr, "Failed to parse state/cofig file: " + str(e))
        raise e

    if CK_API_CLIENT_ID not in GLOBAL_CONTEXT:
        raise ValueError(
            "State/config file is missing the API_CLIENT_ID key.  "
            "This is part of the API configuration on the Digi-Key API portal.")

    if CK_API_SECRET not in GLOBAL_CONTEXT:
        raise ValueError(
            "State/config file is missing the API_SECRET key. "
            " This is part of the API configuration on the Digi-Key API portal.")

    if CK_API_REDIRECT not in GLOBAL_CONTEXT:
        raise ValueError(
            "State/config file is missing the API_REDIRECT_URI key. "
            " This is part of the API configuration on the Digi-Key API portal.")

    if CK_LOGIN_NAME not in GLOBAL_CONTEXT:
        raise ValueError(
            "State/config file is missing the LOGIN_NAME key.  "
            "This is the login name of your Digi-Key account that you use to buy parts.")

    if CK_LOGIN_PASSWORD not in GLOBAL_CONTEXT:
        raise ValueError(
            "State/config file is missing the LOGIN_PASSWORD key.  "
            "This is the password of your Digi-Key account that you use to buy parts.")

    if CK_CONTEXT not in GLOBAL_CONTEXT:
        raise ValueError(
            "State/config file is missing the CONTEXT.  "
            "This means that your file is corrupt/incomplete.  "
            "Please read documentation in this source file.")

    if CK_DEBUG not in GLOBAL_CONTEXT:
        GLOBAL_CONTEXT[CK_DEBUG] = "FALSE"

    if GLOBAL_CONTEXT[CK_DEBUG] == "TRUE":
        DEBUG_FLAG = True
    else:
        DEBUG_FLAG = False

    if DEBUG_FLAG:
        print("Successfully loaded application state/config.")
    return


def dump_response_headers(r, _target=sys.stdout):
    """
        Dumps the response headers in a relatively useful fasion
        @param r: Response object
        @param _target: Where to dump the information.  Should be a file descriptor type object.
    """

    print("\n" + ("*" * 10) + " RESPONSE HEADERS START " + ("*" * 10))

    for h in r.headers.keys():
        print(_target, h + ": " + r.headers[h])
    print(("*" * 10) + " RESPONSE HEADERS END " + ("*" * 10) + "\n")

    return


def create_auth_magic_url_one():
    """
        Cobbles together a URL for the first step of the authentication magic
        @see: https://api-portal.digikey.com/node/188
        @return: A URL with the magic bits specified in the application configuration
    """

    dd = SSO_HOST + "/as/authorization.oauth2?response_type=code&client_id=" + GLOBAL_CONTEXT[
        CK_API_CLIENT_ID] + "&redirect_uri=" + GLOBAL_CONTEXT[CK_API_REDIRECT]
    return dd


def invoke_auth_magic_one():
    """
        Performs the first step of the authentication magic.
        @see: https://api-portal.digikey.com/node/188
        @return: Magic code to be used in step two of the authentication.
    """

    if DEBUG_FLAG:
        print("Trying to perform first stage of magic: invoking a redirect so user has chance to approve us.")

    https_session = requests.Session()
    magic_string = create_auth_magic_url_one()
    r = https_session.post(magic_string)

    if r.status_code != 200:
        print >> sys.stderr, ("*" * 10) + " ERROR OUTPUT START " + ("*" * 10)
        print >> sys.stderr, "Failed in the first sub-step of the authentication magic step one."
        print >> sys.stderr, "Response code: " + r.status_code
        dump_response_headers(r, sys.stderr)
        print >> sys.stderr, r.text
        print >> sys.stderr, ("*" * 10) + " ERROR OUTPUT END " + ("*" * 10)
        raise RuntimeError(
            "Failed to get new tokens in authentication magic step one.  See program output for details.")

    html_parser = MyHTMLParser()
    html_parser.feed(r.text)

    if DEBUG_FLAG:
        print("Trying to perform second stage of magic: fudging login via form.")

    https_session.headers.update({"Referer": magic_string, "Content-Type": "application/x-www-form-urlencoded"})

    r = https_session.post(SSO_HOST + html_parser.form_action, data={"pf.username": GLOBAL_CONTEXT[CK_LOGIN_NAME],
                                                                     "pf.pass": GLOBAL_CONTEXT[CK_LOGIN_PASSWORD],
                                                                     "pf.ok": "clicked"}, allow_redirects=False)

    #
    # XXX I guess here there could be another response.  If the session is expired there might be another clickthrough dialog.
    #
    if r.status_code != 302:
        print(("*" * 10) + " ERROR OUTPUT START " + ("*" * 10))
        print("Failed in the second sub-step of the authentication magic step one.")
        print("Response code: " + str(r.status_code))
        dump_response_headers(r, sys.stderr)
        print(r.text)
        print(("*" * 10) + " ERROR OUTPUT END " + ("*" * 10))
        raise RuntimeError(
            "Failed to get new tokens in authentication magic step one.  See program output for details.")

    magic_code = None

    try:
        #
        # What do you mean "robust"?
        #
        # On success the redirect header will look something like this:
        # Location: https://localhost?code=<MAGIC BEANS>
        #
        # We extract the code parameter because that's really all we care about
        #

        magic_code = r.headers["Location"].split("?")[1].split("=")[1]
    except Exception as e:
        print >> sys.stderr, "Failed to extract code from the 'Location' response header: " + str(e)
        dump_response_headers(r, sys.stderr)
        raise RuntimeError(
            "Failed to get new tokens in authentication magic step one.  See program output for details.")

    if magic_code is None:
        raise RuntimeError(
            "Failed to get new tokens in authentication magic step one.  Magic code seems to be None even though everything went well.")

    if DEBUG_FLAG:
        print("If we got this far we probably have a new code.")
        print("Code: " + str(magic_code))

    return magic_code


def create_auth_magic_url_two(_code):
    """
        Cobbles together a URL for the second step of the authentication magic.
        @see: https://api-portal.digikey.com/node/188
        @return: A URL with the magic bits specified in the application configuration combined with magic bits produced by authentication magic step one.
    """

    # For V1
    # V2 expects everything to be moved out of the request and into the body
    # return SSO_HOST + "/as/token.oauth2?grant_type=authorization_code&code=" + _code + "&
    # client_id=" + GLOBAL_CONTEXT[CK_API_CLIENT_ID] + "&client_secret=" + GLOBAL_CONTEXT[CK_API_SECRET] +
    # "&redirect_uri=" + GLOBAL_CONTEXT[CK_API_REDIRECT]

    return SSO_HOST + "/as/token.oauth2"


def invoke_auth_magic_two(_code):
    """
        Performs the second step of the authentication magic.  Here we get the real-real authentication token and a refresh token.
        @param _code: Magic code from step one of the authentication process.
        @see: https://api-portal.digikey.com/node/188
    """

    if DEBUG_FLAG:
        print("Trying to collect more magic beans.")

    global GLOBAL_CONTEXT

    magic_string = create_auth_magic_url_two(_code)

    if DEBUG_FLAG:
        print("Magic URL: " + magic_string)

    post_data = {}

    post_data["code"] = _code
    post_data["client_id"] = GLOBAL_CONTEXT[CK_API_CLIENT_ID]
    post_data["client_secret"] = GLOBAL_CONTEXT[CK_API_SECRET]
    post_data["redirect_uri"] = GLOBAL_CONTEXT[CK_API_REDIRECT]
    post_data["grant_type"] = "authorization_code"

    r = requests.post(magic_string, data=post_data)

    if r.status_code < 200 or r.status_code >= 300:
        print >> sys.stderr, "Failed to get new tokens in authentication magic step two"
        print >> sys.stderr, "Response code: " + str(r.status_code)
        dump_response_headers(r, sys.stderr)
        print >> sys.stderr, "Response text: "
        print >> sys.stderr, r.text

        raise RuntimeError(
            "Failed to get new tokens in authentication magic step two.  See program output for details.")

    d = json.loads(r.text)

    GLOBAL_CONTEXT[CK_CONTEXT][CK_CONTEXT_ACC_TOK] = d["access_token"]
    GLOBAL_CONTEXT[CK_CONTEXT][CK_CONTEXT_REF_TOK] = d["refresh_token"]

    if DEBUG_FLAG:
        print("We should have enough magic beans to grow the bean stalk so that we can climb INTO THE CLOUD.")

    return


def create_api_call_headers(_client_id, _auth_token):
    """
        Creates the necessary headers to invoke an API call.
        @param _client_id: Client ID magic string.
        @param _auth_token: Authentication token magic string.  This is usually stored in the application state/configuration.
        @return: A map of headers.
    """
    pass
    ret = {}
    ret["accept"] = "application/json"
    # ret["x-digikey-locale-language"] = "en"
    # ret["x-digikey-locale-currency"] = "usd"
    ret["authorization"] = str(_auth_token)
    ret["content-type"] = "application/json"
    ret["x-ibm-client-id"] = str(_client_id)

    return ret


def create_api_part_search(_id, _qty):
    """
        Creates the map containing the pertinent part search parameters.
        @param _id: Digi-Key part ID.
        @param _qty: Part quantity.  Should probably be more than zero.
        @return: A map of the parameters.
    """
    ret = {}
    ret["Keywords"] = _id
    ret["RecordCount"] = _qty
    return ret


def dump_request_headers(r, _target=sys.stdout):
    """
        Dumps the response headers in a relatively useful fasion
        @param r: Response object
        @param _target: Where to dump the information.  Should be a file descriptor type object.
	"""

    print >> _target, "\n" + ("*" * 10) + " REQUEST HEADERS START " + ("*" * 10)

    for h in r.request.headers.keys():
        print >> _target, h + ": " + r.request.headers[h]
    print >> _target, ("*" * 10) + " REQUEST HEADERS END " + ("*" * 10) + "\n"

    return


def get_part_data(_id, _qty):
    """
        @raise RuntimeError: Raises a RuntimeError if the response code is not 2xx.  The search can fail for any number of reasons including an invalid part number.  A malformed request, auth error, an invalid search, they all return code 4xx.
        @return: Search results in a fully formed Python object.
	"""

    head = create_api_call_headers(GLOBAL_CONTEXT[CK_API_CLIENT_ID], GLOBAL_CONTEXT[CK_CONTEXT][CK_CONTEXT_ACC_TOK])

    payload = json.dumps(create_api_part_search(_id.strip(), int(_qty)))

    r = requests.post(API_PART_SEARCH_URI, data=payload, headers=head)

    if DEBUG_FLAG:
        dump_response_headers(r)
        dump_request_headers(r)

    if r.status_code < 200 or r.status_code >= 300:
        raise RuntimeError("Remote call to search for parts failed for some reason.  Don't know why. Code: " + str(
            r.status_code) + ", Body: " + r.text)

    body = json.loads(r.text)

    if DEBUG_FLAG:
        print("\n" + ("*" * 10) + " RESULT START " + ("*" * 10))
        print(json.dumps(body, indent=4))
        print(("*" * 10) + " RESULT END " + ("*" * 10) + "\n")

    return body


def search_for_part(_part, _count, _compact):
    d = None

    ind = 2
    seps = (', ', ': ')

    if _compact:
        ind = None
        seps = (',', ':')

    try:
        d = get_part_data(_part, _count)
    except RuntimeError as e:
        #
        # This could be thrown by anything and everything.  We'll assume that just means that no results were found.
        #
        print("Failed to search for part: " + str(e))
        sys.exit(-1)

    global PARAMETRICS_CACHE
    try:
        for i in d["Parts"][0]["Parameters"]:
            parm_text = i["Parameter"]
            parm_id = str(i["ParameterId"])

            if parm_id not in PARAMETRICS_CACHE.keys():
                PARAMETRICS_CACHE[parm_id] = parm_text

        if len(d["Parts"]) == 1:
            d = d["Parts"][0]

        # if CMD_ARGS.rmMl:
        #     d.pop("MediaLinks", None)
        # if CMD_ARGS.rmPp:
        #     d.pop("PrimaryPhoto", None)
        # if CMD_ARGS.rmPd:
        #     d.pop("PrimaryDatasheet", None)

        return json.dumps(d, indent=ind, ensure_ascii=True, separators=seps)
    except:
        print('[ERROR]: No element with mpn:\'{}\' in DigiKey database'.format(_part))
        return None


# ======================================================================================================================


engine = create_engine(DB_CONNECTION)
Session = sessionmaker(bind=engine)
session = Session()


def get_category_list():
    main_dict = {}

    temp_dict = session.query(APCategory.id, APCategory.name).filter(APCategory.name != "Draft").all()
    for dk in temp_dict:
        main_dict[dk[1]] = dk[0]
    return main_dict


def add_element_to_db(elements_list, table='component'):
    temp_list = []
    categories = get_category_list()
    for x_item in elements_list:
        for key in x_item.keys():
            if u"\u0022" in x_item[key]:
                print(x_item[key])
                val = x_item[key].replace(u"\u0022", u"\u201D")
                x_item[key] = val
                print(x_item[key])
    for element in elements_list:
        try:
            if element['Category'] not in categories.keys():
                # log_message('ERROR',
                #             'DevToolsDB',
                #             'DevTools DB has no record in "Category" table with value: "{}".[COMPONENT]: {}'
                #             .format(element['Category'], element.__str__().replace(u"\u0027", u"\u0022")))
                create_category(element['Category'])
                categories = get_category_list()
                log_message('ACTION',
                            'DevToolsDB',
                            'Category "{}" was created because, '
                            'DevTools DB has no record in "Category" table with this value'.format(element['Category']))
            additional_query = """('{}', {}, '{}')""".format(element['ManufacturerPartNumber'],
                                                             categories[element['Category']],
                                                             str(element).replace(u"\u0027", u"\u0022"))
            temp_list.append(additional_query)
            add_params_to_template(element)
        except:
            log_message('ERROR',
                        'DevToolsDB',
                        'Problem with [COMPONENT]: {}'
                        .format(element.__str__().replace(u"\u0027", u"\u0022")))
            # return 'ERROR'
    query = ''
    for value in temp_list:
        query += value + ','
    query = query[:-1]
    update_query = text("""INSERT INTO {} (mpn, category_id, params) values {}""".format(table, query))
    session.execute(update_query)


def log_message(action_type, action_source, message):
    session.execute('insert into log (action_type, action_source, message) values(\'{}\', \'{}\', \'{}\')'
                 .format(action_type, action_source, message))


if __name__ == '__main__':
    # try:
    #     load_global_context()
    #     code = invoke_auth_magic_one()
    #     invoke_auth_magic_two(code)
    #     res = search_for_part('RC0402FR-070RL', 1, None)
    #     ff = json.loads(res)
    #     qq = ff['Parameters']
    #     params = {}
    #     for item in qq:
    #         params[item['Parameter']] = item['Value']
    #     params["Manufacturer"] = ff['ManufacturerName']['Text']
    #     params['Datasheet'] = ff['PrimaryDatasheet']
    #     params['Family'] = ff['Family']['Text']
    #     params['Category'] = ff['Category']['Text']
    #     params['MountingType'] = '-'
    #     print(params)
    #     if params['Family'] == 'Chip Resistor - Surface Mount':
    #         add_resistor_to_db('resistors_chip', params)
    #
    # except ValueError as e:
    #     print >> sys.stderr, "Failed to load state/config file: " + str(e)
    # hhh = '[{"Packaging":"Tape & Reel (TR)","Part Status":"Active","Resistance":"0 Ohms","Tolerance":"Jumper","Power (Watts)":"0.063W, 1/16W","Composition":"Thick Film","Features":"Moisture Resistant","Temperature Coefficient":"-","Operating Temperature":"-55°C ~ 155°C","Package / Case":"0402 (1005 Metric)","Supplier Device Package":"0402","Size / Dimension":"0.039\" L x 0.020\" W (1.00mm x 0.50mm)","Height - Seated (Max)":"0.016\" (0.40mm)","Number of Terminations":"2","Failure Rate":"-","Manufacturer":"Yageo","Datasheet":"http://www.yageo.com/documents/recent/PYu-RC_Group_51_RoHS_L_10.pdf","Family":"Chip Resistor - Surface Mount","Category":"Resistors","MountingType":"-","ManufacturerPartNumber":"RC0402FR-070RL"}]'
    # n = json.dumps(hhh)
    # o = json.loads(n)
    fff = get_category_list()
    pass
