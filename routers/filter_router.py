import json

from fastapi import APIRouter
from sqlalchemy import create_engine, distinct
from sqlalchemy.orm import sessionmaker

from dependencies import DB_CONNECTION
from internal.models.db_models import APComponent, APPartnumber, APCategory, APParamlist

router = APIRouter(
    prefix="/filter",
    tags=["filter"]
)

engine = create_engine(DB_CONNECTION)
Session = sessionmaker(bind=engine)
session = Session()


def sort_param(data):
    """ Documentation for a method param_filter. Added: 02.10.2020 16:12 dmytro.medintsev


    :param :
    :type :

    :return:
    :rtype:
    """
    res = {}
    p_list = []
    for i in data:
        for j in i.params:
            p_list.append(i.params)
            if j not in res:
                res[j] = []
    for t in p_list:
        for p in res:
            if p in t:
                if t[p] not in res[p]:
                    res[p].append(t[p])
    return res


@router.get("/component/{filter_json}", tags=["filter"])
def components_filter(filter_json: str):
    c_filter = json.loads(filter_json)

    if len(c_filter) > 0:
        dd = session.query(APComponent.params).filter(APComponent.params.contains(c_filter)).all()
        session.close()
        ff = sort_param(dd)
        return {
            "components": [i[0] for i in dd],
            "filters": ff
        }
    else:
        tree = {}
        tree_query_res = session.query(distinct(APParamlist.category), APParamlist.family).all()
        for branch, leaf in tree_query_res:
            if branch not in tree:
                tree[branch] = []
            tree[branch].append(leaf)
        return tree


@router.get("/component/table_column_order/{family}", tags=["filter"])
def components_filter(family: str):
    return [i[0] for i in session.query(APParamlist.param_name).filter(APParamlist.family == family).
        filter(APParamlist.index >= 0).order_by(APParamlist.index.asc()).all()]


@router.get("/article/{filter_json}", tags=["filter"])
def components_filter(filter_json: str):
    a_filter = json.loads(filter_json)
    temp_list = []
    if 'Category' in a_filter:
        category_name = a_filter['Category']
        category = session.query(APCategory).filter(APCategory.name == category_name).first()
        temp_list = session.query(APPartnumber).filter(APPartnumber.name.startswith(f"11.{category.id}.")).all()
        if 'Family' in a_filter:
            family = a_filter['Family']
            family_id = category.family_list[family]
            temp_list = session.query(APPartnumber).filter(
                APPartnumber.name.startswith(f"11.{category.id :02d}.{family_id :02d}")).all()
        return temp_list
    else:
        return session.query(APPartnumber.name, APPartnumber.Description).all()

    pass
