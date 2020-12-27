import json

from fastapi import APIRouter, HTTPException


from internal.digikey_api import search_for_part, invoke_auth_magic_two, invoke_auth_magic_one, load_global_context, \
    log_message

router = APIRouter(
    prefix="/search",
    tags=["search"]
)


def get_search_api(search_engine: str):
    try:
        res = eval(search_engine)
    except Exception as e:
        print(e)
        raise TypeError("Invalid API name")
    return res


def digikey_partdetails(data_list: str):
    params = []
    global g_data
    load_global_context()
    code = invoke_auth_magic_one()
    invoke_auth_magic_two(code)
    mpn_list = data_list.split(',')
    for mpn in mpn_list:
        mpn = mpn.strip()
        res = search_for_part(mpn, 1, None)
        param = {}
        if res is not None:
            ff = json.loads(res)
            qq = ff['Parameters']
            for item in qq:
                param[item['Parameter']] = item['Value']
            param["Manufacturer"] = ff['ManufacturerName']['Text']
            param['Datasheet'] = ff['PrimaryDatasheet']
            param['Family'] = ff['Family']['Text']
            param['Category'] = ff['Category']['Text']
            param['MountingType'] = '-'
            param['ManufacturerPartNumber'] = mpn
            param['BuyUrl'] = ff['BuyUrl']
            params.append(param)
        else:
            param['ManufacturerPartNumber'] = mpn
            param['Description'] = 'No element with mpn:"{}" in DigiKey database'.format(mpn)
            params.append(param)
            log_message('WARNING', 'DigiKeyDB', param['Description'])
    g_data = params
    return params


@router.get("/search_api_list", tags=["search"])
def get_search_api_list():
    return [
        'digi-key'
    ]


@router.get('/', tags=["search"])
def search(where: str, what: str):
    if where == "digi-key":
        return digikey_partdetails(what)
    else:
        raise HTTPException(status_code=404, detail="Bad search source name")



