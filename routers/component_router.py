import sqlalchemy
from fastapi import APIRouter
from fastapi.exceptions import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dependencies import DB_CONNECTION
from internal.digikey_api import get_category_list, log_message
from internal.models.db_models import APComponent, APPartnumber, APParamlist, APCategory

router = APIRouter(
    prefix="/components",
    tags=["components"]
)

engine = create_engine(DB_CONNECTION)
Session = sessionmaker(bind=engine)
session = Session()


def __check_for_new_params(params):
    new_params = []
    qqq = session.query(APParamlist.family).filter(APParamlist.family == params['Family']).all()
    if len(qqq) == 0:
        category = session.query(APCategory).filter(APCategory.name == params['Category']).first()
        category.family_list[params['Family']] = len(category.family_list)

    params_in_db = [i[0] for i in
                    session.query(APParamlist.param_name).filter(APParamlist.category == params['Category']). \
                        filter(APParamlist.family == params['Family']).all()]
    for p in params:
        if p not in params_in_db:
            new_params.append(APParamlist(category=params['Category'],
                                          family=params['Family'],
                                          param_name=p,
                                          index=0))
            session.add_all(new_params)
            session.commit()


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
                session.add(APCategory(name=element['Category']))
                session.commit()
                categories = get_category_list()
                log_message('ACTION',
                            'DevToolsDB',
                            'Category "{}" was created because, '
                            'DevTools DB has no record in "Category" table with this value'.format(element['Category']))
            additional_query = """('{}', {}, '{}')""".format(element['ManufacturerPartNumber'],
                                                             categories[element['Category']],
                                                             str(element).replace(u"\u0027", u"\u0022"))
            temp_list.append(additional_query)
            __check_for_new_params(element)
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
    update_query = f"INSERT INTO {table} (mpn, category_id, params) values {query}"
    sql_query = sqlalchemy.text(update_query)
    session.execute(sql_query)
    session.commit()
    session.close()


@router.post("/", tags=["components"])
def post_component(data: dict):
    try:
        component_list = data['data']
        add_element_to_db(component_list)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="Error with adding component to DB")


@router.get("/{component_mpn}", tags=["components"])
def get_component(component_mpn: str):
    component, name = session.query(APComponent, APPartnumber.name).join(APPartnumber).filter(
        APComponent.mpn == component_mpn).first()
    qq = component.params['Category']
    ww = component.params['Family']
    tmp_order = session.query(APParamlist.param_name). \
        filter(APParamlist.category == component.params['Category']). \
        filter(APParamlist.family == component.params['Family']).all()
    order = [i[0] for i in tmp_order]
    new_params = {}
    for param_name in order:
        if param_name in component.params:
            new_params[param_name] = component.params[param_name]
    component_as_dict = component.__dict__
    component_as_dict['params'] = new_params
    component_as_dict['partnumber'] = name
    del component_as_dict['id']
    del component_as_dict['category_id']
    return component_as_dict


@router.put("/{component_mpn}", tags=["components"])
def update_component(component_mpn: str, component: dict):
    """
    in process
    :param component:
    :return:
    """
    field_list = [
        "priority",
        "provider",
        "delivery_time",
        "validation",
        "price",
        "factory",
        "mpn",
        "partnumber",
        "params"]
    for prm in field_list:
        if prm not in component:
            raise HTTPException(status_code=400, detail="Bad component description")
    if not component['params']['ManufacturerPartNumber'] == component_mpn:
        raise HTTPException(status_code=400, detail="Component name error")
    updated_component = session.query(APComponent).filter(APComponent.mpn == component_mpn).first()
    dict_component = updated_component.__dict__
    dict_new = {}
    for key in dict_component:
        if key == "_sa_instance_state":
            continue
        dict_new[key] = component[key]
    __check_for_new_params(component['params'])
    dict_new['partnumber'] = \
        session.query(APPartnumber.id).filter(APPartnumber.name == component['partnumber']).first()[0]
    session.query(APComponent).filter(APComponent.mpn == component_mpn).update(dict_new)
    session.commit()
    return True
    pass


@router.delete("/{component_mpn}", tags=["components"])
def delete_component(component_mpn: str):
    """
    in process
    :param component_mpn:
    :return:
    """
    session.query(APComponent).filter(APComponent.mpn == component_mpn).delete()
    session.commit()
    return True


@router.get("/blacklist_and_order/{family}", tags=["components"])
def get_blacklist_and_order(family: str):
    return session.query(APParamlist.index, APParamlist.param_name).filter(APParamlist.family == family).\
        order_by(APParamlist.index.asc()).all()


@router.put("/blacklist_and_order/{family}", tags=["components"])
def update_blacklist_and_order(family: str, blacklist_and_order: list):
    def _to_dict(list_list):
        res = {}
        for i in list_list:
            res[i[1]] = i[0]
        return res

    new_list = _to_dict(blacklist_and_order)
    all_params = session.query(APParamlist).filter(APParamlist.family == family).order_by(APParamlist.index.asc()).all()
    for i in all_params:
        i.index = new_list[i.param_name]
    session.commit()



